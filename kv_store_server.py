#!/usr/bin/env python3
"""
Key-Value Store Database Server with Clustering and Replication
"""

from typing import Any, Optional
from dataclasses import dataclass
from enum import Enum
import json
import threading
import time
import socket
import signal
import sys
import argparse
import random


class NodeRole(Enum):
    """Node role in the cluster"""
    PRIMARY = "primary"
    SECONDARY = "secondary"


@dataclass
class NodeInfo:
    """Information about a cluster node"""
    node_id: str
    host: str
    port: int
    role: NodeRole = NodeRole.SECONDARY
    last_heartbeat: float = 0.0


@dataclass
class ReplicationLog:
    """Entry in the replication log"""
    timestamp: float
    operation: str  # SET, DELETE
    key: str
    value: Optional[Any] = None


class KeyValueStore:
    """Thread-safe in-memory key-value store with replication log"""
    
    def __init__(self):
        self.store: dict[str, Any] = {}
        self.lock = threading.Lock()
        self.replication_log: list[ReplicationLog] = []
    
    def set(self, key: str, value: Any) -> dict:
        """Set a key-value pair"""
        with self.lock:
            self.store[key] = value
            # Add to replication log
            self.replication_log.append(
                ReplicationLog(
                    timestamp=time.time(),
                    operation="SET",
                    key=key,
                    value=value
                )
            )
            return {"status": "OK"}
    
    def get(self, key: str) -> Optional[Any]:
        """Get value for a key"""
        with self.lock:
            return self.store.get(key)
    
    def delete(self, key: str) -> dict:
        """Delete a key"""
        with self.lock:
            if key in self.store:
                del self.store[key]
                # Add to replication log
                self.replication_log.append(
                    ReplicationLog(
                        timestamp=time.time(),
                        operation="DELETE",
                        key=key
                    )
                )
                return {"status": "OK"}
            else:
                return {"status": "ERROR"}
    
    def get_all(self) -> dict:
        """Get all key-value pairs"""
        with self.lock:
            return dict(self.store)
    
    def apply_replication_log(self, entries: list[dict]):
        """Apply replication log entries"""
        with self.lock:
            for entry in entries:
                if entry["operation"] == "SET":
                    self.store[entry["key"]] = entry["value"]
                elif entry["operation"] == "DELETE":
                    if entry["key"] in self.store:
                        del self.store[entry["key"]]


class TCPServer:
    """TCP server with cluster support"""
    
    def __init__(self, kv_store: KeyValueStore, node_id: str, host: str = '0.0.0.0', 
                 port: int = 6379, role: NodeRole = NodeRole.SECONDARY):
        self.kv_store = kv_store
        self.node_id = node_id
        self.host = host
        self.port = port
        self.role = role
        self.socket = None
        self.running = True
        
        # Cluster configuration
        self.primary_node: Optional[NodeInfo] = None
        self.secondary_nodes: dict[str, NodeInfo] = {}
        self.election_term = 0
        self.voted_for: Optional[str] = None
        
        # Known nodes in cluster
        self.all_nodes = [
            {"node_id": "node1", "host": "127.0.0.1", "port": 6379},
            {"node_id": "node2", "host": "127.0.0.1", "port": 6380},
            {"node_id": "node3", "host": "127.0.0.1", "port": 6381},
        ]
    
    def is_primary(self) -> bool:
        """Check if this node is the primary"""
        return self.role == NodeRole.PRIMARY
    
    def start(self):
        """Start the TCP server"""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((self.host, self.port))
        self.socket.listen(5)
        print(f"[{self.node_id}] TCP Server listening on {self.host}:{self.port} (Role: {self.role.value})")
        
        # Register with other nodes
        if self.is_primary():
            self._register_with_secondaries()
        else:
            self._register_with_primary()
        
        try:
            while self.running:
                try:
                    self.socket.settimeout(1.0)
                    client_socket, addr = self.socket.accept()
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, addr),
                        daemon=True
                    )
                    client_thread.start()
                except socket.timeout:
                    continue
        except KeyboardInterrupt:
            self.stop()
    
    def stop(self):
        """Stop the server"""
        self.running = False
        if self.socket:
            self.socket.close()
        print(f"[{self.node_id}] Server stopped")
    
    def _register_with_secondaries(self):
        """Primary registers secondary nodes"""
        for node in self.all_nodes:
            if node["node_id"] != self.node_id:
                self.secondary_nodes[node["node_id"]] = NodeInfo(
                    node_id=node["node_id"],
                    host=node["host"],
                    port=node["port"],
                    role=NodeRole.SECONDARY,
                    last_heartbeat=time.time()
                )
    
    def _register_with_primary(self):
        """Secondary registers primary node"""
        for node in self.all_nodes:
            if node["node_id"] != self.node_id:
                # Assume first node is primary initially
                if node["node_id"] == "node1":
                    self.primary_node = NodeInfo(
                        node_id=node["node_id"],
                        host=node["host"],
                        port=node["port"],
                        role=NodeRole.PRIMARY,
                        last_heartbeat=time.time()
                    )
                    break
    
    def handle_client(self, client_socket: socket.socket, addr):
        """Handle a client connection"""
        try:
            while self.running:
                data = client_socket.recv(4096)
                if not data:
                    break
                
                command_str = data.decode('utf-8').strip()
                response = self.process_command(command_str)
                client_socket.send(response.encode('utf-8') + b'\n')
        except Exception as e:
            pass
        finally:
            client_socket.close()
    
    def process_command(self, command_str: str) -> str:
        """Process a command and return response"""
        try:
            # Try to parse as JSON first (internal cluster commands)
            try:
                command = json.loads(command_str)
                if isinstance(command, dict) and "type" in command:
                    return self._handle_internal_command(command)
            except json.JSONDecodeError:
                pass
            
            # Parse as regular command
            parts = command_str.split(None, 2)
            if not parts:
                return json.dumps({"status": "ERROR", "message": "Empty command"})
            
            cmd = parts[0].upper()
            
            if cmd == "SET" and len(parts) == 3:
                if not self.is_primary():
                    return json.dumps({
                        "status": "ERROR",
                        "message": "This node is not primary. Writes not allowed."
                    })
                
                key, value = parts[1], parts[2]
                try:
                    value = json.loads(value)
                except:
                    pass
                
                self.kv_store.set(key, value)
                
                # Replicate to secondaries
                self.replicate_to_secondaries("SET", key, value)
                
                return json.dumps({"status": "OK", "message": f"Key '{key}' set"})
            
            elif cmd == "GET" and len(parts) == 2:
                if not self.is_primary():
                    return json.dumps({
                        "status": "ERROR",
                        "message": "This node is not primary. Reads not allowed."
                    })
                
                key = parts[1]
                value = self.kv_store.get(key)
                if value is None:
                    return json.dumps({"status": "ERROR", "message": f"Key '{key}' not found"})
                return json.dumps({"status": "OK", "value": value})
            
            elif cmd == "DELETE" and len(parts) == 2:
                if not self.is_primary():
                    return json.dumps({
                        "status": "ERROR",
                        "message": "This node is not primary. Deletes not allowed."
                    })
                
                key = parts[1]
                result = self.kv_store.delete(key)
                
                if result["status"] == "OK":
                    self.replicate_to_secondaries("DELETE", key, None)
                
                return json.dumps(result)
            
            elif cmd == "PING":
                return json.dumps({"status": "OK", "message": "PONG"})
            
            elif cmd == "STATUS":
                return json.dumps({
                    "status": "OK",
                    "node_id": self.node_id,
                    "role": self.role.value,
                    "election_term": self.election_term
                })
            
            elif cmd == "SHUTDOWN":
                self.stop()
                return json.dumps({"status": "OK", "message": "Server shutting down"})
            
            else:
                return json.dumps({"status": "ERROR", "message": f"Unknown command: {cmd}"})
        
        except Exception as e:
            return json.dumps({"status": "ERROR", "message": str(e)})
    
    def _handle_internal_command(self, command: dict) -> str:
        """Handle internal cluster commands"""
        cmd_type = command.get("type")
        
        if cmd_type == "REPLICATE":
            # Apply replication from primary
            operation = command.get("operation")
            key = command.get("key")
            value = command.get("value")
            
            if operation == "SET":
                self.kv_store.set(key, value)
            elif operation == "DELETE":
                self.kv_store.delete(key)
            
            return json.dumps({"status": "OK", "message": "Replicated"})
        
        elif cmd_type == "HEARTBEAT":
            # Update primary heartbeat
            if self.primary_node:
                self.primary_node.last_heartbeat = time.time()
            return json.dumps({"status": "OK", "message": "Heartbeat received"})
        
        elif cmd_type == "ELECTION":
            # Handle election request
            candidate_id = command.get("candidate_id")
            term = command.get("term")
            
            if term > self.election_term:
                self.election_term = term
                self.voted_for = candidate_id
                return json.dumps({"status": "OK", "message": "Vote granted", "term": term})
            else:
                return json.dumps({"status": "ERROR", "message": "Vote denied", "term": self.election_term})
        
        elif cmd_type == "SYNC":
            # Sync replication log
            return json.dumps({"status": "OK", "message": "Sync complete"})
        
        return json.dumps({"status": "ERROR", "message": "Unknown internal command"})
    
    def replicate_to_secondaries(self, operation: str, key: str, value: Any):
        """Replicate operation to secondary nodes"""
        if not self.is_primary():
            return
        
        replication_cmd = json.dumps({
            "type": "REPLICATE",
            "operation": operation,
            "key": key,
            "value": value
        })
        
        for node_id, node_info in self.secondary_nodes.items():
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                sock.connect((node_info.host, node_info.port))
                sock.send(replication_cmd.encode() + b'\n')
                sock.recv(1024)  # Read response
                sock.close()
            except Exception as e:
                pass  # Best effort replication


class ClusterManager:
    """Manages cluster heartbeat and elections"""
    
    def __init__(self, server: TCPServer):
        self.server = server
        self.running = True
        self.heartbeat_interval = 2  # seconds
        self.election_timeout = random.uniform(5, 8)  # seconds
    
    def start(self):
        """Start cluster management threads"""
        if self.server.is_primary():
            # Primary sends heartbeats
            heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
            heartbeat_thread.start()
        else:
            # Secondary monitors for election
            election_thread = threading.Thread(target=self._election_monitor, daemon=True)
            election_thread.start()
    
    def _heartbeat_loop(self):
        """Send periodic heartbeats to secondaries"""
        while self.running and self.server.running:
            time.sleep(self.heartbeat_interval)
            
            heartbeat_cmd = json.dumps({"type": "HEARTBEAT", "from_node": self.server.node_id})
            
            for node_id, node_info in self.server.secondary_nodes.items():
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(1)
                    sock.connect((node_info.host, node_info.port))
                    sock.send(heartbeat_cmd.encode() + b'\n')
                    sock.recv(1024)
                    sock.close()
                except Exception:
                    pass
    
    def _election_monitor(self):
        """Monitor for primary failure and start election"""
        while self.running and self.server.running:
            time.sleep(1)
            
            if self.server.primary_node:
                time_since_heartbeat = time.time() - self.server.primary_node.last_heartbeat
                
                if time_since_heartbeat > self.election_timeout:
                    print(f"[{self.server.node_id}] Primary appears down. Starting election.")
                    self._start_election()
                    # Reset timeout after election
                    self.election_timeout = random.uniform(5, 8)
    
    def _start_election(self):
        """Start leader election"""
        self.server.election_term += 1
        self.server.voted_for = self.server.node_id
        
        print(f"[{self.server.node_id}] Starting election for term {self.server.election_term}")
        
        votes = 1  # Vote for self
        
        # Request votes from other nodes
        election_cmd = json.dumps({
            "type": "ELECTION",
            "candidate_id": self.server.node_id,
            "term": self.server.election_term
        })
        
        for node in self.server.all_nodes:
            if node["node_id"] == self.server.node_id:
                continue
            
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                sock.connect((node["host"], node["port"]))
                sock.send(election_cmd.encode() + b'\n')
                response = sock.recv(1024)
                sock.close()
                
                result = json.loads(response.decode())
                if result.get("status") == "OK":
                    votes += 1
                    print(f"[{self.server.node_id}] Got vote from {node['node_id']}")
            except Exception:
                pass
        
        # Check if won election (majority)
        quorum = len(self.server.all_nodes) // 2 + 1
        if votes >= quorum:
            self._become_primary()
    
    def _become_primary(self):
        """Promote this node to primary"""
        print(f"[{self.server.node_id}] Won election! Becoming PRIMARY")
        self.server.role = NodeRole.PRIMARY
        self.server._register_with_secondaries()
        
        # Start sending heartbeats
        heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        heartbeat_thread.start()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='KV Store Server with Clustering')
    parser.add_argument('--node-id', required=True, help='Node ID (e.g., node1, node2)')
    parser.add_argument('--port', type=int, required=True, help='Port to listen on')
    parser.add_argument('--primary', action='store_true', help='Start as primary node')
    
    args = parser.parse_args()
    
    # Create store and server
    kv_store = KeyValueStore()
    role = NodeRole.PRIMARY if args.primary else NodeRole.SECONDARY
    
    server = TCPServer(
        kv_store=kv_store,
        node_id=args.node_id,
        host='0.0.0.0',
        port=args.port,
        role=role
    )
    
    # Start cluster manager
    cluster_manager = ClusterManager(server)
    cluster_manager.start()
    
    # Handle graceful shutdown
    def signal_handler(signum, frame):
        server.stop()
        cluster_manager.running = False
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    server.start()


if __name__ == "__main__":
    main()