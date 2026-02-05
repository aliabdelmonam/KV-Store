#!/usr/bin/env python3
"""
Examples demonstrating advanced KV Store features:
1. Secondary indexes
2. Full-text search
3. Semantic search (embeddings)
4. Masterless replication
"""

import socket
import json
import time
import shlex


class AdvancedKVClient:
    """Client for advanced KV store"""
    
    def __init__(self, host='127.0.0.1', port=6379):
        self.host = host
        self.port = port
        self.socket = None
    
    def connect(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.host, self.port))
    
    def disconnect(self):
        if self.socket:
            self.socket.close()
    
    def send_command(self, command: str) -> dict:
        if not self.socket:
            self.connect()
        
        self.socket.send(command.encode() + b'\n')
        response = self.socket.recv(16384)
        return json.loads(response.decode())
    
    def set(self, key: str, value) -> dict:
        # Quote the JSON string so it's treated as a single argument
        val_str = shlex.quote(json.dumps(value))
        cmd = f"SET {key} {val_str}"
        return self.send_command(cmd)
    
    def get(self, key: str) -> dict:
        return self.send_command(f"GET {key}")
    
    def delete(self, key: str) -> dict:
        return self.send_command(f"DELETE {key}")
    
    def create_index(self, name: str, field_path: str) -> dict:
        """Create secondary index on a field"""
        return self.send_command(f"CREATE_INDEX {name} {field_path}")
    
    def search(self, index_name: str, value) -> dict:
        """Search using secondary index"""
        val_str = shlex.quote(json.dumps(value))
        cmd = f"SEARCH {index_name} {val_str}"
        return self.send_command(cmd)
    
    def range_search(self, index_name: str, min_val, max_val) -> dict:
        """Range search using secondary index"""
        min_str = shlex.quote(json.dumps(min_val))
        max_str = shlex.quote(json.dumps(max_val))
        cmd = f"RANGE_SEARCH {index_name} {min_str} {max_str}"
        return self.send_command(cmd)
    
    def fulltext_search(self, query: str, mode: str = 'or') -> dict:
        """Full-text search"""
        query_str = shlex.quote(query)
        return self.send_command(f"FULLTEXT {query_str} {mode}")
    
    def semantic_search(self, query: str, top_k: int = 10) -> dict:
        """Semantic search using embeddings"""
        query_str = shlex.quote(query)
        return self.send_command(f"SEMANTIC {query_str} {top_k}")
    
    def status(self) -> dict:
        return self.send_command("STATUS")


# ============================================================================
# DEMO 1: Secondary Indexes
# ============================================================================

def demo_secondary_indexes():
    """Demonstrate secondary indexes on values"""
    print("\n" + "="*70)
    print("DEMO 1: Secondary Indexes")
    print("="*70)
    
    client = AdvancedKVClient(port=6379)
    client.connect()
    
    # Insert user data
    print("\n1. Inserting user data...")
    users = [
        {"id": 1, "name": "Alice", "age": 30, "city": "NYC", "role": "engineer"},
        {"id": 2, "name": "Bob", "age": 25, "city": "SF", "role": "designer"},
        {"id": 3, "name": "Charlie", "age": 35, "city": "NYC", "role": "manager"},
        {"id": 4, "name": "Diana", "age": 28, "city": "LA", "role": "engineer"},
        {"id": 5, "name": "Eve", "age": 32, "city": "SF", "role": "engineer"},
    ]
    
    for user in users:
        client.set(f"user:{user['id']}", user)
        print(f"   Inserted user:{user['id']}")
    
    # Create indexes
    print("\n2. Creating indexes...")
    client.create_index("age_index", "age")
    print("   [OK] Created index on 'age'")
    
    client.create_index("city_index", "city")
    print("   [OK] Created index on 'city'")
    
    client.create_index("role_index", "role")
    print("   [OK] Created index on 'role'")
    
    # Search by exact value
    print("\n3. Searching by city = 'NYC'...")
    result = client.search("city_index", "NYC")
    print(f"   Found keys: {result['keys']}")
    
    print("\n4. Searching by role = 'engineer'...")
    result = client.search("role_index", "engineer")
    print(f"   Found keys: {result['keys']}")
    
    # Range search
    print("\n5. Range search: age between 25 and 30...")
    result = client.range_search("age_index", 25, 30)
    print(f"   Found keys: {result['keys']}")
    
    client.disconnect()
    print("\n[OK] Demo 1 complete!")


# ============================================================================
# DEMO 2: Full-Text Search
# ============================================================================

def demo_fulltext_search():
    """Demonstrate full-text search with inverted index"""
    print("\n" + "="*70)
    print("DEMO 2: Full-Text Search (Inverted Index)")
    print("="*70)
    
    client = AdvancedKVClient(port=6379)
    client.connect()
    
    # Insert documents
    print("\n1. Inserting documents...")
    documents = [
        {
            "id": 1,
            "title": "Introduction to Python Programming",
            "content": "Python is a high-level programming language that is easy to learn and versatile."
        },
        {
            "id": 2,
            "title": "Machine Learning Basics",
            "content": "Machine learning is a subset of artificial intelligence that uses algorithms to learn from data."
        },
        {
            "id": 3,
            "title": "Deep Learning with Neural Networks",
            "content": "Neural networks are the foundation of deep learning and artificial intelligence systems."
        },
        {
            "id": 4,
            "title": "Python for Data Science",
            "content": "Python has become the go-to language for data science and machine learning projects."
        },
        {
            "id": 5,
            "title": "Natural Language Processing",
            "content": "NLP enables computers to understand and process human language using machine learning."
        }
    ]
    
    for doc in documents:
        client.set(f"doc:{doc['id']}", doc)
        print(f"   Inserted doc:{doc['id']}")
    
    # Full-text search (OR mode - any word matches)
    print("\n2. Full-text search: 'python programming' (OR mode)...")
    result = client.fulltext_search("python programming", "or")
    print(f"   Found keys: {result['keys']}")
    
    # Full-text search (AND mode - all words must match)
    print("\n3. Full-text search: 'machine learning' (AND mode)...")
    result = client.fulltext_search("machine learning", "and")
    print(f"   Found keys: {result['keys']}")
    
    print("\n4. Full-text search: 'neural networks' (AND mode)...")
    result = client.fulltext_search("neural networks", "and")
    print(f"   Found keys: {result['keys']}")
    
    print("\n5. Full-text search: 'artificial intelligence' (AND mode)...")
    result = client.fulltext_search("artificial intelligence", "and")
    print(f"   Found keys: {result['keys']}")
    
    client.disconnect()
    print("\n[OK] Demo 2 complete!")


# ============================================================================
# DEMO 3: Semantic Search (Word Embeddings)
# ============================================================================

def demo_semantic_search():
    """Demonstrate semantic search using embeddings"""
    print("\n" + "="*70)
    print("DEMO 3: Semantic Search (Word Embeddings)")
    print("="*70)
    
    client = AdvancedKVClient(port=6379)
    client.connect()
    
    # Insert product descriptions
    print("\n1. Inserting product descriptions...")
    products = [
        {
            "id": 1,
            "name": "Wireless Bluetooth Headphones",
            "description": "High-quality wireless headphones with noise cancellation and comfortable ear cushions"
        },
        {
            "id": 2,
            "name": "Laptop Computer",
            "description": "Powerful laptop with fast processor and large display for productivity"
        },
        {
            "id": 3,
            "name": "Smart Phone",
            "description": "Modern smartphone with excellent camera and long battery life"
        },
        {
            "id": 4,
            "name": "Wireless Mouse",
            "description": "Ergonomic wireless mouse with precision tracking"
        },
        {
            "id": 5,
            "name": "Portable Speaker",
            "description": "Bluetooth speaker with powerful sound and waterproof design"
        },
        {
            "id": 6,
            "name": "Tablet Device",
            "description": "Lightweight tablet with touchscreen and stylus support"
        }
    ]
    
    for product in products:
        client.set(f"product:{product['id']}", product)
        print(f"   Inserted product:{product['id']}")
    
    # Semantic search - find similar products
    print("\n2. Semantic search: 'audio music sound'...")
    result = client.semantic_search("audio music sound", top_k=3)
    print("   Top 3 results:")
    for item in result['results']:
        print(f"      {item['key']} (score: {item['score']:.3f})")
    
    print("\n3. Semantic search: 'computer computing device'...")
    result = client.semantic_search("computer computing device", top_k=3)
    print("   Top 3 results:")
    for item in result['results']:
        print(f"      {item['key']} (score: {item['score']:.3f})")
    
    print("\n4. Semantic search: 'mobile phone camera'...")
    result = client.semantic_search("mobile phone camera", top_k=3)
    print("   Top 3 results:")
    for item in result['results']:
        print(f"      {item['key']} (score: {item['score']:.3f})")
    
    client.disconnect()
    print("\n[OK] Demo 3 complete!")


# ============================================================================
# DEMO 4: Masterless Replication
# ============================================================================

def demo_masterless_replication():
    """Demonstrate masterless (multi-master) replication"""
    print("\n" + "="*70)
    print("DEMO 4: Masterless Replication")
    print("="*70)
    
    # Connect to multiple nodes
    node1 = AdvancedKVClient(port=6379)
    node2 = AdvancedKVClient(port=6380)
    node3 = AdvancedKVClient(port=6381)
    
    node1.connect()
    node2.connect()
    node3.connect()
    
    print("\n1. Checking cluster status...")
    for i, client in enumerate([node1, node2, node3], 1):
        status = client.status()
        print(f"   Node {i}: {status['node_id']} - Mode: {status['mode']} - Peers: {status['peers']}")
    
    # Write to different nodes
    print("\n2. Writing to different nodes (all are masters)...")
    
    print("   Writing to Node 1...")
    node1.set("key1", {"source": "node1", "value": "Hello from node 1"})
    
    print("   Writing to Node 2...")
    node2.set("key2", {"source": "node2", "value": "Hello from node 2"})
    
    print("   Writing to Node 3...")
    node3.set("key3", {"source": "node3", "value": "Hello from node 3"})
    
    # Wait for replication
    print("\n3. Waiting for replication (2 seconds)...")
    time.sleep(2)
    
    # Read from different nodes
    print("\n4. Reading from all nodes (should have all data)...")
    
    print("\n   Node 1 has:")
    for key in ["key1", "key2", "key3"]:
        result = node1.get(key)
        if result['status'] == 'OK':
            print(f"      {key}: {result['value']}")
        else:
            print(f"      {key}: NOT FOUND")
    
    print("\n   Node 2 has:")
    for key in ["key1", "key2", "key3"]:
        result = node2.get(key)
        if result['status'] == 'OK':
            print(f"      {key}: {result['value']}")
        else:
            print(f"      {key}: NOT FOUND")
    
    print("\n   Node 3 has:")
    for key in ["key1", "key2", "key3"]:
        result = node3.get(key)
        if result['status'] == 'OK':
            print(f"      {key}: {result['value']}")
        else:
            print(f"      {key}: NOT FOUND")
    
    # Concurrent writes (conflict scenario)
    print("\n5. Concurrent writes to same key (conflict detection)...")
    print("   Node 1 writes: counter = 100")
    node1.set("counter", 100)
    
    print("   Node 2 writes: counter = 200")
    node2.set("counter", 200)
    
    time.sleep(1)
    
    print("\n   Reading 'counter' from Node 3...")
    result = node3.get("counter")
    print(f"   Value: {result.get('value')} (last write wins)")
    
    node1.disconnect()
    node2.disconnect()
    node3.disconnect()
    
    print("\n[OK] Demo 4 complete!")


# ============================================================================
# DEMO 5: Combined Example
# ============================================================================

def demo_combined():
    """Demonstrate all features together"""
    print("\n" + "="*70)
    print("DEMO 5: Combined Example - E-commerce Search")
    print("="*70)
    
    client = AdvancedKVClient(port=6379)
    client.connect()
    
    # Insert e-commerce products
    print("\n1. Inserting e-commerce products...")
    products = [
        {
            "id": 101,
            "name": "Leather Laptop Bag",
            "category": "accessories",
            "price": 89.99,
            "description": "Premium leather bag with padded laptop compartment and multiple pockets",
            "tags": ["leather", "bag", "laptop", "business"]
        },
        {
            "id": 102,
            "name": "Wireless Gaming Mouse",
            "category": "electronics",
            "price": 59.99,
            "description": "High-precision wireless mouse designed for gaming with RGB lighting",
            "tags": ["gaming", "mouse", "wireless", "rgb"]
        },
        {
            "id": 103,
            "name": "Office Desk Chair",
            "category": "furniture",
            "price": 249.99,
            "description": "Ergonomic office chair with lumbar support and adjustable height",
            "tags": ["office", "chair", "ergonomic", "furniture"]
        },
        {
            "id": 104,
            "name": "USB-C Hub Adapter",
            "category": "electronics",
            "price": 39.99,
            "description": "Multi-port USB-C hub with HDMI output and SD card reader",
            "tags": ["usb", "adapter", "hub", "electronics"]
        },
        {
            "id": 105,
            "name": "Mechanical Keyboard",
            "category": "electronics",
            "price": 129.99,
            "description": "Mechanical keyboard with tactile switches and backlight for typing and gaming",
            "tags": ["keyboard", "mechanical", "gaming", "typing"]
        }
    ]
    
    for product in products:
        client.set(f"product:{product['id']}", product)
        print(f"   Inserted product:{product['id']}")
    
    # Create indexes
    print("\n2. Creating indexes...")
    client.create_index("category_idx", "category")
    client.create_index("price_idx", "price")
    print("   [OK] Indexes created")
    
    # Use case 1: Filter by category
    print("\n3. Search by category = 'electronics':")
    result = client.search("category_idx", "electronics")
    print(f"   Found: {result['keys']}")
    
    # Use case 2: Price range search
    print("\n4. Products priced between $40 and $100:")
    result = client.range_search("price_idx", 40, 100)
    print(f"   Found: {result['keys']}")
    
    # Use case 3: Full-text search
    print("\n5. Full-text search for 'wireless gaming':")
    result = client.fulltext_search("wireless gaming", "and")
    print(f"   Found: {result['keys']}")
    
    # Use case 4: Semantic search
    print("\n6. Semantic search for 'computer accessories':")
    result = client.semantic_search("computer accessories", top_k=3)
    print("   Top 3 matches:")
    for item in result['results']:
        print(f"      {item['key']} (relevance: {item['score']:.3f})")
    
    client.disconnect()
    print("\n[OK] Demo 5 complete!")


# ============================================================================
# MAIN
# ============================================================================

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Advanced KV Store Examples')
    parser.add_argument('--demo', 
                       choices=['indexes', 'fulltext', 'semantic', 'masterless', 'combined', 'all'],
                       default='all',
                       help='Which demo to run')
    
    args = parser.parse_args()
    
    try:
        if args.demo in ['indexes', 'all']:
            demo_secondary_indexes()
        
        if args.demo in ['fulltext', 'all']:
            demo_fulltext_search()
        
        if args.demo in ['semantic', 'all']:
            demo_semantic_search()
        
        if args.demo in ['masterless', 'all']:
            demo_masterless_replication()
        
        if args.demo in ['combined', 'all']:
            demo_combined()
        
        if args.demo == 'all':
            print("\n" + "="*70)
            print("ALL DEMOS COMPLETED!")
            print("="*70)
    
    except ConnectionRefusedError:
        print("\nERROR: Cannot connect to server!")
        print("Make sure the cluster is running:")
        print("  python cluster_manager_advanced.py")
    except Exception as e:
        print(f"\nERROR: {e}")


if __name__ == '__main__':
    main()
