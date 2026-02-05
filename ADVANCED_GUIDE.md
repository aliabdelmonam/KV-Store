# Advanced KV Store - Complete Guide

## 🚀 New Features

Your KV Store now includes 4 advanced features:

1. **Secondary Indexes** - Index any field in your values for fast lookups
2. **Full-Text Search** - Search document content with inverted index
3. **Semantic Search** - Find similar documents using word embeddings
4. **Masterless Replication** - Write to any node, no single point of failure

---

## 🎯 Quick Start (5 minutes)

### Step 1: Start the Cluster

```bash
python cluster_manager_advanced.py
```

Output:
```
Starting Advanced KV Store Cluster (Masterless)
All 3 nodes are MASTERS - write to any node!
...
Cluster started successfully!
```

### Step 2: Run Examples

In another terminal:

```bash
# Run all demos
python examples_advanced.py --demo all

# Or run specific demos
python examples_advanced.py --demo indexes
python examples_advanced.py --demo fulltext
python examples_advanced.py --demo semantic
python examples_advanced.py --demo masterless
```

---

## 📚 Feature Documentation

### 1. Secondary Indexes

**What it does**: Create indexes on any field in your values for O(1) lookups and range queries.

**Commands**:
```
CREATE_INDEX <name> <field_path>    # Create an index
SEARCH <index_name> <value>         # Exact match search
RANGE_SEARCH <index_name> <min> <max>  # Range query
```

**Example**:

```python
client = AdvancedKVClient(port=6379)
client.connect()

# Store user data
client.set("user:1", {"name": "Alice", "age": 30, "city": "NYC"})
client.set("user:2", {"name": "Bob", "age": 25, "city": "SF"})
client.set("user:3", {"name": "Charlie", "age": 35, "city": "NYC"})

# Create index on age
client.create_index("age_index", "age")

# Search by exact age
result = client.search("age_index", 30)
# Returns: {"status": "OK", "keys": ["user:1"]}

# Range search: ages 25-30
result = client.range_search("age_index", 25, 30)
# Returns: {"status": "OK", "keys": ["user:1", "user:2"]}

# Create index on nested field
client.set("order:1", {"user": {"id": 1, "name": "Alice"}, "total": 99.99})
client.create_index("user_id_index", "user.id")
result = client.search("user_id_index", 1)
```

**Field Path Syntax**:
- Simple field: `"age"`
- Nested field: `"user.id"`
- Array field: `"tags"` (indexes each element)
- Deep nesting: `"address.location.city"`

**Use Cases**:
- Filter products by category
- Find users by age range
- Query by price range
- Filter by status, tags, etc.

---

### 2. Full-Text Search (Inverted Index)

**What it does**: Search text content across all fields. Automatically indexes all text in values.

**Commands**:
```
FULLTEXT <query> [mode]
# mode: 'or' (default), 'and', 'phrase'
```

**Example**:

```python
# Store documents
client.set("doc:1", {
    "title": "Python Programming",
    "content": "Python is a great language for beginners"
})
client.set("doc:2", {
    "title": "Machine Learning",
    "content": "Learn Python for machine learning and AI"
})

# OR search - any word matches
result = client.fulltext_search("python machine", "or")
# Returns: {"keys": ["doc:1", "doc:2"]}

# AND search - all words must be present
result = client.fulltext_search("python machine", "and")
# Returns: {"keys": ["doc:2"]}

# Phrase search
result = client.fulltext_search("machine learning", "phrase")
# Returns: {"keys": ["doc:2"]}
```

**How it works**:
- Tokenizes all text (splits into words)
- Removes stop words (a, an, the, etc.)
- Creates inverted index: word → documents containing word
- Searches are case-insensitive

**Use Cases**:
- Search product descriptions
- Find documents by keywords
- Content search
- Log searching

---

### 3. Semantic Search (Word Embeddings)

**What it does**: Find similar documents even if they don't share exact words. Uses character n-gram embeddings.

**Commands**:
```
SEMANTIC <query> [top_k]
# Returns top_k most similar documents with similarity scores
```

**Example**:

```python
# Store product descriptions
client.set("product:1", {
    "name": "Wireless Headphones",
    "description": "High-quality audio with noise cancellation"
})
client.set("product:2", {
    "name": "Laptop Computer",
    "description": "Powerful device for productivity"
})
client.set("product:3", {
    "name": "Bluetooth Speaker",
    "description": "Portable speaker with great sound"
})

# Semantic search - finds related products
result = client.semantic_search("audio music sound", top_k=2)
# Returns: [
#   {"key": "product:1", "score": 0.85},
#   {"key": "product:3", "score": 0.72}
# ]
```

**How it works**:
- Computes embeddings using character n-grams
- Each document gets a 50-dimensional vector
- Similarity measured by cosine similarity
- Returns ranked results

**Use Cases**:
- "Find similar products"
- Recommendation systems
- Fuzzy matching
- Typo-tolerant search

---

### 4. Masterless Replication

**What it does**: All nodes are masters - write to any node. No single point of failure. Uses vector clocks for conflict detection.

**Architecture**:
```
     Node 1 (MASTER)
         /  \
        /    \
   Node 2 ←→ Node 3
  (MASTER)  (MASTER)
```

**Key Concepts**:

1. **Write to Any Node**: All nodes accept writes
2. **Vector Clocks**: Track causality and detect conflicts
3. **Last-Write-Wins**: Simple conflict resolution
4. **Anti-Entropy**: Background sync every 10 seconds

**Example**:

```python
# Connect to different nodes
node1 = AdvancedKVClient(port=6379)
node2 = AdvancedKVClient(port=6380)
node3 = AdvancedKVClient(port=6381)

node1.connect()
node2.connect()
node3.connect()

# Write to node 1
node1.set("key1", "value from node 1")

# Write to node 2
node2.set("key2", "value from node 2")

# Write to node 3
node3.set("key3", "value from node 3")

# Wait for replication
time.sleep(2)

# All nodes have all data!
print(node1.get("key2"))  # Works!
print(node2.get("key3"))  # Works!
print(node3.get("key1"))  # Works!
```

**Conflict Scenario**:
```python
# Two nodes write to same key concurrently
node1.set("counter", 100)  # Vector clock: {node1: 1}
node2.set("counter", 200)  # Vector clock: {node2: 1}

# After sync, vector clocks are compared:
# {node1: 1} vs {node2: 1} → CONCURRENT
# Resolution: Last write wins (by timestamp)
```

**How Vector Clocks Work**:
```
Initial: {}
Node1 writes: {node1: 1}
Node2 reads and writes: {node1: 1, node2: 1}
Node1 writes again: {node1: 2, node2: 1}

Comparison:
{node1: 2, node2: 1} vs {node1: 1, node2: 1}
→ "after" (first supersedes second)

{node1: 1, node2: 0} vs {node1: 0, node2: 1}
→ "concurrent" (neither supersedes)
```

**Use Cases**:
- High availability
- Multi-datacenter setup
- Offline-first applications
- No single point of failure

---

## 🎮 API Reference

### Client Commands

```python
client = AdvancedKVClient(port=6379)
client.connect()

# Basic operations
client.set(key, value)
client.get(key)
client.delete(key)

# Indexing
client.create_index(name, field_path)
client.search(index_name, value)
client.range_search(index_name, min_val, max_val)

# Search
client.fulltext_search(query, mode='or')  # mode: or, and, phrase
client.semantic_search(query, top_k=10)

# Status
client.status()
```

### Raw TCP Commands

```
SET key {"field": "value"}
GET key
DELETE key

CREATE_INDEX age_index age
SEARCH age_index 30
RANGE_SEARCH price_index 10 100

FULLTEXT python programming or
SEMANTIC machine learning 5

STATUS
PING
SHUTDOWN
```

---

## 📊 Performance Characteristics

| Operation | Time Complexity | Notes |
|-----------|----------------|-------|
| SET | O(1) | Plus indexing overhead |
| GET | O(1) | Direct lookup |
| Index Search | O(1) | Hash table lookup |
| Range Search | O(n) | Scans index entries |
| Full-Text Search | O(k) | k = # words in query |
| Semantic Search | O(n) | Computes similarity for all docs |
| Replication | Async | Best-effort, 1-2ms latency |

**Indexing Overhead**:
- Creating index: O(n) where n = existing keys
- Per-write: O(1) per index
- Memory: O(n × m) where m = # indexes

---

## 🧪 Testing

### Run All Examples

```bash
python examples_advanced.py --demo all
```

### Individual Demos

```bash
# Demo 1: Secondary indexes
python examples_advanced.py --demo indexes

# Demo 2: Full-text search
python examples_advanced.py --demo fulltext

# Demo 3: Semantic search
python examples_advanced.py --demo semantic

# Demo 4: Masterless replication
python examples_advanced.py --demo masterless

# Demo 5: Combined e-commerce example
python examples_advanced.py --demo combined
```

---

## 💡 Use Cases by Feature

### Use Secondary Indexes When:
- ✓ You need to filter by specific field values
- ✓ You want range queries (age 25-30, price $10-$100)
- ✓ You query by the same fields repeatedly
- ✓ Your data has structured fields

### Use Full-Text Search When:
- ✓ You want to search text content
- ✓ Users search by keywords
- ✓ You need "contains word" queries
- ✓ You have documents, articles, descriptions

### Use Semantic Search When:
- ✓ You want to find similar items
- ✓ Exact word matches aren't enough
- ✓ You need recommendation features
- ✓ You want typo tolerance

### Use Masterless Replication When:
- ✓ You need high availability
- ✓ You can't afford a single point of failure
- ✓ You want to distribute write load
- ✓ You need multi-datacenter support

---

## 🔧 Configuration

### Adjust Anti-Entropy Interval

In `kv_store_advanced.py`:

```python
class AntiEntropyManager:
    def __init__(self, server):
        self.sync_interval = 10  # Change this (seconds)
```

### Adjust Embedding Dimensions

```python
class SimpleEmbedding:
    def __init__(self, dimensions: int = 50):  # Change this
```

Higher dimensions = better accuracy but more memory

### Adjust Replication Log Size

```python
def _sync_loop(self):
    log_entries = self.server.kv_store.replication_log[-100:]  # Last N ops
```

---

## 🚨 Troubleshooting

### Ports Already in Use

```bash
# Kill existing processes
pkill -f kv_store_advanced.py

# Or on Windows
taskkill /F /IM python.exe
```

### Search Returns Empty Results

1. Check if data was inserted: `client.get(key)`
2. For index search: Verify index was created
3. For full-text: Check query has valid words (not stop words)
4. For semantic: Wait 1 second after insertion for indexing

### Replication Not Working

1. Verify all 3 nodes are running
2. Check ports 6379, 6380, 6381 are accessible
3. Wait 2 seconds after write for replication
4. Check for errors in server output

---

## 📈 Scaling Considerations

### Memory Usage

- **Indexes**: Each index stores value → keys mapping
- **Inverted Index**: Stores word → documents mapping
- **Embeddings**: 50 floats per document (200-400 bytes)
- **Vector Clocks**: Small overhead per value

**Estimate**: ~1KB overhead per document (all features enabled)

### When to Use What

**Small Dataset (<10K docs)**:
- Use all features
- Performance excellent

**Medium Dataset (10K-100K docs)**:
- Use indexes selectively
- Full-text search works well
- Semantic search may be slow

**Large Dataset (>100K docs)**:
- Consider index-only approach
- Implement pagination for semantic search
- Use sharding for scale-out

---

## 🎓 Example: E-commerce Application

```python
# Setup
client = AdvancedKVClient(port=6379)
client.connect()

# Insert products
products = [
    {"id": 1, "name": "Laptop", "category": "electronics", "price": 999.99,
     "description": "Powerful laptop for productivity"},
    {"id": 2, "name": "Mouse", "category": "electronics", "price": 29.99,
     "description": "Wireless mouse with precision tracking"},
    # ... more products
]

for p in products:
    client.set(f"product:{p['id']}", p)

# Create indexes for filtering
client.create_index("category_idx", "category")
client.create_index("price_idx", "price")

# Use Case 1: Filter by category
electronics = client.search("category_idx", "electronics")

# Use Case 2: Filter by price range
affordable = client.range_search("price_idx", 0, 50)

# Use Case 3: Search by keyword
search_results = client.fulltext_search("wireless mouse", "and")

# Use Case 4: "Similar products" feature
similar = client.semantic_search("laptop computer productivity", top_k=5)

# Use Case 5: Write from multiple locations (masterless)
node_west = AdvancedKVClient(port=6379)  # West coast
node_east = AdvancedKVClient(port=6380)  # East coast

# Both can write!
node_west.set("cart:user123", {"items": [1, 2, 3]})
node_east.set("order:456", {"user": 123, "total": 1029.98})
```

---

## 🔗 Architecture Details

### Masterless Architecture

```
Traditional (Single Master):
    PRIMARY ← All writes go here (bottleneck!)
      ↓
  REPLICAS (read-only)

Masterless (This Implementation):
   NODE 1 ← Write here
      ↕
   NODE 2 ← Or write here!
      ↕
   NODE 3 ← Or write here!
   
All nodes sync with each other
```

### Vector Clock Example

```python
# Timeline:
T1: Node1 writes key="x", value=1
    Vector Clock: {node1: 1}

T2: Node2 reads and writes key="x", value=2
    Vector Clock: {node1: 1, node2: 1}

T3: Node1 writes key="x", value=3
    Vector Clock: {node1: 2, node2: 1}

# Conflict Detection:
VC1: {node1: 2, node2: 1}  
VC2: {node1: 1, node2: 2}
→ CONCURRENT (both keep, resolve by timestamp)
```

---

## 📝 Summary

| Feature | Benefit | Trade-off |
|---------|---------|-----------|
| **Indexes** | Fast lookups O(1) | Memory overhead |
| **Full-Text** | Search content | Index size |
| **Semantic** | Find similar items | CPU cost |
| **Masterless** | High availability | Eventual consistency |

**When to use this system**:
- ✓ You need fast queries on values
- ✓ You need search capabilities
- ✓ You need high availability
- ✓ You can handle eventual consistency

**When NOT to use**:
- ✗ You need strong consistency (use primary-secondary instead)
- ✗ You need transactions
- ✗ You need relational queries (use SQL database)

---

## 🚀 Next Steps

1. **Start the cluster**: `python cluster_manager_advanced.py`
2. **Run examples**: `python examples_advanced.py --demo all`
3. **Try your own queries**: Use the client API
4. **Test failover**: Kill a node, writes still work on others!
5. **Build your app**: Use as a backend for your project

---

**Ready to go! 🎉**
