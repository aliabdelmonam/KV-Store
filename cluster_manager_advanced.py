#!/usr/bin/env python3
"""
Cluster manager for Advanced KV Store (Masterless)
"""

import subprocess
import sys
import time
import signal
from pathlib import Path


class AdvancedClusterManager:
    """Manages masterless 3-node cluster"""
    
    def __init__(self):
        self.processes = []
        self.nodes = [
            {"node_id": "node1", "port": 6379},
            {"node_id": "node2", "port": 6380},
            {"node_id": "node3", "port": 6381},
        ]
    
    def start_cluster(self):
        """Start all cluster nodes"""
        print("Starting Advanced KV Store Cluster (Masterless)")
        print("="*70)
        print("All 3 nodes are MASTERS - write to any node!")
        print("="*70)
        
        script_dir = Path(__file__).parent
        
        for node in self.nodes:
            cmd = [
                sys.executable,
                str(script_dir / "kv_store_advanced.py"),
                "--node-id", node["node_id"],
                "--port", str(node["port"]),
            ]
            
            print(f"\nStarting {node['node_id']} on port {node['port']} (MASTER)...")
            
            try:
                proc = subprocess.Popen(cmd)
                self.processes.append((node["node_id"], proc))
                time.sleep(1)
                print(f"  → Process started (PID: {proc.pid})")
            except Exception as e:
                print(f"Failed to start {node['node_id']}: {e}")
                self.stop_cluster()
                sys.exit(1)
        
        print("\n" + "="*70)
        print("Cluster started successfully!")
        print("="*70)
        print("\nCluster Configuration:")
        print("  - Node 1 (MASTER): 127.0.0.1:6379")
        print("  - Node 2 (MASTER): 127.0.0.1:6380")
        print("  - Node 3 (MASTER): 127.0.0.1:6381")
        print("\nFeatures:")
        print("  ✓ Write to ANY node (all are masters)")
        print("  ✓ Secondary indexes on values")
        print("  ✓ Full-text search (inverted index)")
        print("  ✓ Semantic search (word embeddings)")
        print("  ✓ Automatic replication to all peers")
        print("  ✓ Vector clocks for conflict detection")
        print("\nYou can now:")
        print("  1. Run examples: python examples_advanced.py --demo all")
        print("  2. Run specific demo: python examples_advanced.py --demo indexes")
        print("  3. Run tests: python test_advanced.py")
        print("\nPress Ctrl+C to stop the cluster...")
        print("="*70)
    
    def stop_cluster(self):
        """Stop all cluster nodes"""
        print("\n\nStopping cluster...")
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
        """Wait for cluster"""
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop_cluster()
            print("\nCluster stopped.")
            sys.exit(0)


def main():
    """Main entry point"""
    manager = AdvancedClusterManager()
    manager.start_cluster()
    
    def signal_handler(signum, frame):
        manager.stop_cluster()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    manager.wait_for_cluster()


if __name__ == '__main__':
    main()
