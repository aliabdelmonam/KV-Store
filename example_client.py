#!/usr/bin/env python3
"""
Example client demonstrating KV Store cluster usage
"""

import socket
import json
import sys
import time


class KVStoreClient:
    """Simple KV Store client"""
    
    def __init__(self, host='127.0.0.1', port=6379):
        self.host = host
        self.port = port
        self.socket = None
    
    def connect(self):
        """Connect to server"""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.host, self.port))
        print(f"Connected to {self.host}:{self.port}")
    
    def disconnect(self):
        """Disconnect from server"""
        if self.socket:
            self.socket.close()
            self.socket = None
    
    def send_command(self, command):
        """Send command and get response"""
        if not self.socket:
            self.connect()
        
        self.socket.send(command.encode() + b'\n')
        response = self.socket.recv(4096)
        return json.loads(response.decode())
    
    def set(self, key, value):
        """Set a key-value pair"""
        cmd = f"SET {key} {json.dumps(value)}"
        return self.send_command(cmd)
    
    def get(self, key):
        """Get a value"""
        cmd = f"GET {key}"
        return self.send_command(cmd)
    
    def delete(self, key):
        """Delete a key"""
        cmd = f"DELETE {key}"
        return self.send_command(cmd)
    
    def ping(self):
        """Ping server"""
        return self.send_command("PING")
    
    def status(self):
        """Get node status"""
        return self.send_command("STATUS")


def print_result(title, result):
    """Pretty print result"""
    print(f"\n{title}")
    print(f"Response: {json.dumps(result, indent=2)}")


def demo_basic_operations():
    """Demonstrate basic operations"""
    print("\n" + "="*60)
    print("DEMO 1: Basic Operations (Write to Primary)")
    print("="*60)
    
    client = KVStoreClient(port=6379)  # Primary
    
    try:
        client.connect()
        
        # Check node status
        print("\n1. Checking node status...")
        status = client.status()
        print_result("Status", status)
        
        # Set values
        print("\n2. Setting key-value pairs...")
        result = client.set("user:1", {"name": "Alice", "age": 30})
        print_result("SET user:1", result)
        
        result = client.set("user:2", {"name": "Bob", "age": 25})
        print_result("SET user:2", result)
        
        result = client.set("config:timeout", 30)
        print_result("SET config:timeout", result)
        
        # Get values
        print("\n3. Reading key-value pairs...")
        result = client.get("user:1")
        print_result("GET user:1", result)
        
        result = client.get("config:timeout")
        print_result("GET config:timeout", result)
        
        # Delete value
        print("\n4. Deleting a key...")
        result = client.delete("config:timeout")
        print_result("DELETE config:timeout", result)
        
        # Try to get deleted value
        result = client.get("config:timeout")
        print_result("GET config:timeout (after delete)", result)
        
    finally:
        client.disconnect()


def demo_replication():
    """Demonstrate replication"""
    print("\n" + "="*60)
    print("DEMO 2: Replication Verification")
    print("="*60)
    
    # Write to primary
    print("\n1. Writing data to PRIMARY (port 6379)...")
    primary = KVStoreClient(port=6379)
    primary.connect()
    
    data = {
        "product:1": {"name": "Laptop", "price": 999.99},
        "product:2": {"name": "Mouse", "price": 29.99},
        "product:3": {"name": "Keyboard", "price": 79.99},
    }
    
    for key, value in data.items():
        result = primary.set(key, value)
        print(f"  SET {key}: {result['status']}")
    
    primary.disconnect()
    
    # Wait for replication
    print("\n2. Waiting for replication (2 seconds)...")
    time.sleep(2)
    
    # Read from secondary nodes
    print("\n3. Attempting to read from SECONDARY nodes...")
    for port in [6380, 6381]:
        secondary = KVStoreClient(port=port)
        secondary.connect()
        
        status = secondary.status()
        node_id = status.get('node_id', 'unknown')
        
        print(f"\n  Secondary node {node_id} (port {port}):")
        
        # Try to get a value (should fail as secondaries don't serve reads)
        result = secondary.get("product:1")
        if result['status'] == 'OK':
            print(f"    ✓ Data is replicated: {result['value']}")
        else:
            print(f"    Note: Secondaries don't serve client reads")
            print(f"    Response: {result['message']}")
        
        secondary.disconnect()


def demo_multi_type_values():
    """Demonstrate different value types"""
    print("\n" + "="*60)
    print("DEMO 3: Multiple Data Types")
    print("="*60)
    
    client = KVStoreClient(port=6379)
    client.connect()
    
    test_values = {
        "string_key": "Hello, World!",
        "number_key": 42,
        "float_key": 3.14159,
        "bool_key": True,
        "list_key": [1, 2, 3, 4, 5],
        "dict_key": {"nested": "value", "count": 10},
        "complex_key": {
            "user": {
                "name": "Charlie",
                "email": "charlie@example.com",
                "tags": ["admin", "developer"],
                "settings": {
                    "notifications": True,
                    "theme": "dark"
                }
            }
        }
    }
    
    print("\nStoring various data types...")
    for key, value in test_values.items():
        result = client.set(key, value)
        print(f"  {key}: {type(value).__name__:10} → {result['status']}")
    
    print("\nRetrieving and verifying data types...")
    for key, original_value in test_values.items():
        result = client.get(key)
        if result['status'] == 'OK':
            retrieved_value = result['value']
            match = retrieved_value == original_value
            status = "✓" if match else "✗"
            print(f"  {status} {key}: {type(retrieved_value).__name__:10}")
    
    client.disconnect()


def demo_secondary_node_restrictions():
    """Demonstrate secondary node write restrictions"""
    print("\n" + "="*60)
    print("DEMO 4: Secondary Node Restrictions")
    print("="*60)
    
    secondary = KVStoreClient(port=6380)  # Secondary
    secondary.connect()
    
    print("\nNode Status:")
    status = secondary.status()
    print_result("Status", status)
    
    print("\nAttempting to write to secondary node...")
    result = secondary.set("test_key", "test_value")
    print_result("SET on Secondary", result)
    
    print("\nAttempting to read from secondary node...")
    result = secondary.get("user:1")
    print_result("GET on Secondary", result)
    
    print("\nAttempting to delete from secondary node...")
    result = secondary.delete("user:1")
    print_result("DELETE on Secondary", result)
    
    print("\nPING works on any node...")
    result = secondary.ping()
    print_result("PING on Secondary", result)
    
    secondary.disconnect()


def demo_concurrent_operations():
    """Demonstrate handling concurrent operations"""
    print("\n" + "="*60)
    print("DEMO 5: Concurrent Operations")
    print("="*60)
    
    import threading
    
    client = KVStoreClient(port=6379)
    client.connect()
    
    results = []
    
    def write_batch(batch_num, count):
        """Write a batch of keys"""
        for i in range(count):
            key = f"batch{batch_num}:key{i}"
            value = {"batch": batch_num, "index": i}
            result = client.set(key, value)
            if result['status'] == 'OK':
                results.append((key, True))
            else:
                results.append((key, False))
    
    print("\nWriting 30 keys concurrently from 3 threads...")
    threads = []
    for batch in range(3):
        t = threading.Thread(target=write_batch, args=(batch, 10))
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join()
    
    successful = sum(1 for _, success in results if success)
    print(f"Successfully wrote {successful} keys")
    
    print("\nVerifying keys were written...")
    verified = 0
    for batch in range(3):
        for i in range(10):
            key = f"batch{batch}:key{i}"
            result = client.get(key)
            if result['status'] == 'OK':
                verified += 1
    
    print(f"Successfully verified {verified} keys")
    
    client.disconnect()


def interactive_mode():
    """Interactive command prompt"""
    print("\n" + "="*60)
    print("INTERACTIVE MODE")
    print("="*60)
    print("\nAvailable commands:")
    print("  set <key> <value>  - Set a key-value pair")
    print("  get <key>          - Get a value")
    print("  delete <key>       - Delete a key")
    print("  status             - Get node status")
    print("  ping               - Ping the server")
    print("  help               - Show this help")
    print("  quit               - Exit")
    
    client = KVStoreClient(port=6379)
    
    try:
        client.connect()
        
        while True:
            try:
                cmd = input("\n> ").strip()
                
                if not cmd:
                    continue
                
                if cmd == "quit":
                    break
                
                elif cmd == "help":
                    print("Available commands:")
                    print("  set <key> <value>  - Set a key-value pair")
                    print("  get <key>          - Get a value")
                    print("  delete <key>       - Delete a key")
                    print("  status             - Get node status")
                    print("  ping               - Ping the server")
                
                elif cmd.startswith("set "):
                    parts = cmd.split(" ", 2)
                    if len(parts) >= 3:
                        key, value = parts[1], parts[2]
                        try:
                            value = json.loads(value)
                        except:
                            pass
                        result = client.set(key, value)
                        print(json.dumps(result, indent=2))
                    else:
                        print("Usage: set <key> <value>")
                
                elif cmd.startswith("get "):
                    key = cmd[4:].strip()
                    result = client.get(key)
                    print(json.dumps(result, indent=2))
                
                elif cmd.startswith("delete "):
                    key = cmd[7:].strip()
                    result = client.delete(key)
                    print(json.dumps(result, indent=2))
                
                elif cmd == "status":
                    result = client.status()
                    print(json.dumps(result, indent=2))
                
                elif cmd == "ping":
                    result = client.ping()
                    print(json.dumps(result, indent=2))
                
                else:
                    print(f"Unknown command: {cmd}")
            
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}")
    
    finally:
        client.disconnect()


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='KV Store Cluster Client Demo'
    )
    parser.add_argument(
        '--demo',
        choices=['basic', 'replication', 'types', 'restrictions', 'concurrent', 'all', 'interactive'],
        default='all',
        help='Demo to run'
    )
    
    args = parser.parse_args()
    
    try:
        if args.demo in ['basic', 'all']:
            demo_basic_operations()
        
        if args.demo in ['replication', 'all']:
            demo_replication()
        
        if args.demo in ['types', 'all']:
            demo_multi_type_values()
        
        if args.demo in ['restrictions', 'all']:
            demo_secondary_node_restrictions()
        
        if args.demo in ['concurrent', 'all']:
            demo_concurrent_operations()
        
        if args.demo == 'interactive':
            interactive_mode()
        
        if args.demo == 'all':
            print("\n" + "="*60)
            print("DEMO COMPLETED")
            print("="*60)
            print("\nRun with --demo interactive for interactive mode")
    
    except ConnectionRefusedError:
        print("Error: Could not connect to KV Store server")
        print("Make sure the cluster is running with: python cluster_manager.py --action start")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(0)


if __name__ == '__main__':
    main()
