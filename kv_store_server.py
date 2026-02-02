#!/usr/bin/env python3
"""
Key-Value Store Database Server with TCP Interface
Redis-like protocol for high performance
"""

from typing import Any, Optional
import json
import os
import threading
import time
import socket
import signal
import sys


class KeyValueStore:
    """Thread-safe persistent key-value store with Write-Ahead Log (WAL)"""
    
    def __init__(self, data_file: str = 'kvstore.db', batch_size: int = 500, flush_interval: float = 2.0):
        self.store: dict[str, Any] = {}
        self.lock = threading.Lock()
        self.data_file = data_file
        self.log_file = data_file + '.log'
        self.snapshot_file = data_file + '.snapshot'
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.pending_writes = 0
        self.log_entries = 0
        self.max_log_entries = 10000  # Snapshot after this many log entries
        self._load_from_disk()
        
        # Start background flush thread
        self.flush_thread = threading.Thread(target=self._flush_worker, daemon=True)
        self.flush_thread.start()
    
    def _flush_worker(self):
        """Background thread that periodically flushes log to disk"""
        while True:
            time.sleep(self.flush_interval)
            with self.lock:
                if self.pending_writes > 0:
                    self._flush_log()
                    self.pending_writes = 0
                
                # Create snapshot if log is getting too large
                if self.log_entries >= self.max_log_entries:
                    self._create_snapshot()
    
    def _load_from_disk(self):
        """Load data from snapshot and replay log"""
        # Load snapshot if exists
        if os.path.exists(self.snapshot_file):
            try:
                with open(self.snapshot_file, 'r') as f:
                    self.store = json.load(f)
                print(f"Loaded snapshot with {len(self.store)} keys from {self.snapshot_file}")
            except Exception as e:
                print(f"Error loading snapshot: {e}")
                self.store = {}
        
        # Replay log file
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        entry = json.loads(line)
                        if entry['op'] == 'SET':
                            self.store[entry['key']] = entry['value']
                        elif entry['op'] == 'DELETE':
                            self.store.pop(entry['key'], None)
                        self.log_entries += 1
                print(f"Replayed {self.log_entries} log entries")
            except Exception as e:
                print(f"Error loading log: {e}")
    
    def _save_to_disk(self):
        """Save data to disk"""
        pass  # Not used with WAL
    
    def _append_to_log(self, operation: str, key: str, value: Any = None):
        """Append operation to write-ahead log"""
        try:
            entry = {'op': operation, 'key': key}
            if operation == 'SET':
                entry['value'] = value
            
            with open(self.log_file, 'a') as f:
                f.write(json.dumps(entry) + '\n')
            self.log_entries += 1
        except Exception as e:
            print(f"Error appending to log: {e}")
    
    def _flush_log(self):
        """Flush log to disk (already appended, just sync)"""
        try:
            # Force OS to write to disk
            with open(self.log_file, 'a') as f:
                f.flush()
                os.fsync(f.fileno())
        except Exception as e:
            print(f"Error flushing log: {e}")
    
    def _create_snapshot(self):
        """Create a snapshot of current state and reset log"""
        try:
            # Write snapshot
            temp_file = self.snapshot_file + '.tmp'
            with open(temp_file, 'w') as f:
                json.dump(self.store, f)
            os.replace(temp_file, self.snapshot_file)
            
            # Clear log
            open(self.log_file, 'w').close()
            self.log_entries = 0
            print(f"Created snapshot with {len(self.store)} keys")
        except Exception as e:
            print(f"Error creating snapshot: {e}")
    
    def set(self, key: str, value: Any) -> dict:
        """Set a key-value pair"""
        with self.lock:
            self.store[key] = value
            self._append_to_log('SET', key, value)
            self.pending_writes += 1
            
            # Flush if batch size reached
            if self.pending_writes >= self.batch_size:
                self._flush_log()
                self.pending_writes = 0
            
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
                self._append_to_log('DELETE', key)
                self.pending_writes += 1
                
                # Flush if batch size reached
                if self.pending_writes >= self.batch_size:
                    self._flush_log()
                    self.pending_writes = 0
                
                return {"status": "OK"}
            else:
                return {"status": "ERROR"}


class TCPServer:
    """TCP server with simple command protocol"""
    
    def __init__(self, kv_store: KeyValueStore, host: str = '0.0.0.0', port: int = 6379):
        self.kv_store = kv_store
        self.host = host
        self.port = port
        self.socket = None
        self.running = True
    
    def start(self):
        """Start the TCP server"""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((self.host, self.port))
        self.socket.listen(5)
        print(f"TCP Server listening on {self.host}:{self.port}")
        
        try:
            while self.running:
                client_socket, addr = self.socket.accept()
                print(f"Client connected: {addr}")
                # Handle client in a separate thread
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket, addr),
                    daemon=True
                )
                client_thread.start()
        except KeyboardInterrupt:
            self.stop()
    
    def stop(self):
        """Stop the server"""
        self.running = False
        if self.socket:
            self.socket.close()
        print("Server stopped")
    
    def handle_client(self, client_socket: socket.socket, addr):
        """Handle a client connection"""
        try:
            while self.running:
                # Receive data
                data = client_socket.recv(4096)
                if not data:
                    break
                
                # Parse command
                command_str = data.decode('utf-8').strip()
                response = self.process_command(command_str)
                
                # Send response
                client_socket.send(response.encode('utf-8') + b'\n')
        except Exception as e:
            print(f"Error handling client {addr}: {e}")
        finally:
            client_socket.close()
            print(f"Client disconnected: {addr}")
    
    def process_command(self, command_str: str) -> str:
        """Process a command and return response"""
        try:
            parts = command_str.split(None, 2)  # Split on whitespace, max 3 parts
            if not parts:
                return json.dumps({"status": "ERROR", "message": "Empty command"})
            
            cmd = parts[0].upper()
            
            if cmd == "SET" and len(parts) == 3:
                key, value = parts[1], parts[2]
                try:
                    value = json.loads(value)  # Try to parse as JSON
                except:
                    pass  # Keep as string if not valid JSON
                self.kv_store.set(key, value)
                return json.dumps({"status": "OK", "message": f"Key '{key}' set"})
            
            elif cmd == "GET" and len(parts) == 2:
                key = parts[1]
                value = self.kv_store.get(key)
                if value is None:
                    return json.dumps({"status": "ERROR", "message": f"Key '{key}' not found"})
                return json.dumps({"status": "OK", "value": value})
            
            elif cmd == "DELETE" and len(parts) == 2:
                key = parts[1]
                result = self.kv_store.delete(key)
                return json.dumps(result)
            
            elif cmd == "FLUSH":
                self.kv_store._flush_log()
                return json.dumps({"status": "OK", "message": "Log flushed"})
            
            elif cmd == "SNAPSHOT":
                self.kv_store._create_snapshot()
                return json.dumps({"status": "OK", "message": "Snapshot created"})
            
            elif cmd == "PING":
                return json.dumps({"status": "OK", "message": "PONG"})
            
            elif cmd == "SHUTDOWN":
                self.stop()
                return json.dumps({"status": "OK", "message": "Server shutting down"})
            
            else:
                return json.dumps({"status": "ERROR", "message": f"Unknown command: {cmd}"})
        
        except Exception as e:
            return json.dumps({"status": "ERROR", "message": str(e)})


# Initialize key-value store
kv_store = KeyValueStore()


if __name__ == "__main__":
    # Create and start TCP server
    server = TCPServer(kv_store, host="0.0.0.0", port=6379)
    
    # Handle graceful shutdown
    def signal_handler(signum, frame):
        server.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    server.start()