#!/usr/bin/env python3
"""
Cluster management script to start and manage a 3-node KV Store cluster
"""

import subprocess
import sys
import time
import signal
import json
import os
from pathlib import Path


class ClusterManager:
    """Manages a 3-node cluster"""
    
    def __init__(self):
        self.processes = []
        self.nodes = [
            {"node_id": "node1", "port": 6379, "primary": True},
            {"node_id": "node2", "port": 6380, "primary": False},
            {"node_id": "node3", "port": 6381, "primary": False},
        ]
    
    def start_cluster(self):
        """Start all cluster nodes"""
        print("Starting KV Store Cluster (3 nodes: 1 primary + 2 secondary)...")
        print("-" * 60)
        
        script_dir = Path(__file__).parent
        
        for node in self.nodes:
            cmd = [
                sys.executable,
                str(script_dir / "kv_store_server.py"),
                "--node-id", node["node_id"],
                "--port", str(node["port"]),
            ]
            if node["primary"]:
                cmd.append("--primary")
                print(f"Starting {node['node_id']} on port {node['port']} (PRIMARY)...")
            else:
                print(f"Starting {node['node_id']} on port {node['port']} (SECONDARY)...")
            
            try:
                proc = subprocess.Popen(cmd)
                self.processes.append((node["node_id"], proc))
                time.sleep(0.5)
            except Exception as e:
                print(f"Failed to start {node['node_id']}: {e}")
                self.stop_cluster()
                sys.exit(1)
        
        print("-" * 60)
        print("Cluster started successfully!")
        print("\nCluster Configuration:")
        print("  - Node 1 (Primary):   127.0.0.1:6379")
        print("  - Node 2 (Secondary): 127.0.0.1:6380")
        print("  - Node 3 (Secondary): 127.0.0.1:6381")
        print("\nYou can now:")
        print("  1. Connect to the cluster using a client")
        print("  2. Write to port 6379 (primary)")
        print("  3. Data will be replicated to ports 6380 and 6381")
        print("  4. If primary fails, election will happen automatically")
        print("\nPress Ctrl+C to stop the cluster...")
        print("-" * 60)
    
    def stop_cluster(self):
        """Stop all cluster nodes"""
        print("\nStopping cluster...")
        for node_id, proc in self.processes:
            try:
                proc.terminate()
                proc.wait(timeout=5)
                print(f"Stopped {node_id}")
            except subprocess.TimeoutExpired:
                proc.kill()
                print(f"Killed {node_id}")
            except Exception as e:
                print(f"Error stopping {node_id}: {e}")
    
    def wait_for_cluster(self):
        """Wait for cluster to be ready"""
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop_cluster()
            print("\nCluster stopped.")
            sys.exit(0)
    
    def status_cluster(self):
        """Show cluster status"""
        import socket
        
        print("\nCluster Status:")
        print("-" * 60)
        for node in self.nodes:
            port = node["port"]
            role = "PRIMARY" if node["primary"] else "SECONDARY"
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                sock.connect(("127.0.0.1", port))
                sock.send(b"PING\n")
                response = sock.recv(1024)
                sock.close()
                print(f"✓ {node['node_id']:6} ({role:9}) - Port {port}: RUNNING")
            except:
                print(f"✗ {node['node_id']:6} ({role:9}) - Port {port}: DOWN")
        print("-" * 60)


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Manage KV Store cluster')
    parser.add_argument('--action', choices=['start', 'status'], default='start',
                       help='Action to perform')
    
    args = parser.parse_args()
    
    manager = ClusterManager()
    
    if args.action == 'start':
        manager.start_cluster()
        
        # Setup signal handlers
        def signal_handler(signum, frame):
            manager.stop_cluster()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        manager.wait_for_cluster()
    
    elif args.action == 'status':
        manager.status_cluster()


if __name__ == '__main__':
    main()
