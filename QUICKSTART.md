# Quick Start Guide - KV Store Cluster

## What's New

Your KV Store now supports **3-node replication cluster** with automatic failover:
- **1 Primary**: Handles all reads and writes
- **2 Secondaries**: Automatic replicas with leader election
- **Automatic Failover**: Secondaries promote to primary if primary fails

## 5-Minute Setup

### Step 1: Start the Cluster

```bash
python cluster_manager.py --action start
```

Output:
```
Starting KV Store Cluster (3 nodes: 1 primary + 2 secondary)...
Starting node1 on port 6379 (PRIMARY)...
Starting node2 on port 6380 (SECONDARY)...
Starting node3 on port 6381 (SECONDARY)...
Cluster started successfully!
```

### Step 2: Run Examples

In a **new terminal**:

```bash
# Run interactive demo
python example_client.py --demo interactive

# Or run all demos
python example_client.py --demo all
```

### Step 3: Try Basic Commands

```bash
# Write to primary (port 6379)
SET mykey "Hello, World!"

# Read from primary
GET mykey

# Check node status
STATUS

# Exit
quit
```

## Common Tasks

### Write Data to Cluster

```python
from example_client import KVStoreClient

client = KVStoreClient(port=6379)  # Connect to primary
client.connect()

# Write data
client.set('user:1', {'name': 'Alice', 'age': 30})

# Read data
result = client.get('user:1')
print(result)

client.disconnect()
```

### Run Tests

```bash
# Run comprehensive tests
python test_replication.py -v

# Run specific test
python test_replication.py TestKVStoreReplication.test_04_write_on_primary_succeeds -v
```

### Monitor Cluster

```bash
# Check cluster status
python cluster_manager.py --action status

# Output:
# ✓ node1 (PRIMARY  ) - Port 6379: RUNNING
# ✓ node2 (SECONDARY) - Port 6380: RUNNING
# ✓ node3 (SECONDARY) - Port 6381: RUNNING
```

## Key Features

### ✓ Automatic Replication
```
Write to port 6379 → Automatically replicated to ports 6380, 6381
```

### ✓ Leader Election
```
Primary down → Election → Secondary becomes Primary (5-8 seconds)
```

### ✓ Primary-Only Operations
```
Writes: Only to primary (port 6379)
Reads:  Only to primary (port 6379)
```

### ✓ Multiple Data Types
```
Strings, Numbers, Booleans, Lists, Objects, Complex Nested Structures
```

## API Overview

| Command | Usage | Where |
|---------|-------|-------|
| SET | `SET key value` | Primary only |
| GET | `GET key` | Primary only |
| DELETE | `DELETE key` | Primary only |
| PING | `PING` | All nodes |
| STATUS | `STATUS` | All nodes |
| SHUTDOWN | `SHUTDOWN` | All nodes |

## Cluster Structure

```
┌─────────────────────────────────────────────────┐
│           KV Store Cluster (3 Nodes)            │
├─────────────────────────────────────────────────┤
│                                                 │
│  node1 (PRIMARY)          node2 (SECONDARY)     │
│  127.0.0.1:6379           127.0.0.1:6380       │
│  ✓ Accepts writes         ✓ Replicates data    │
│  ✓ Accepts reads          ✓ Can become primary │
│  ✓ Sends heartbeats                           │
│                                                 │
│  node3 (SECONDARY)                              │
│  127.0.0.1:6381                                 │
│  ✓ Replicates data                              │
│  ✓ Can become primary                           │
│                                                 │
└─────────────────────────────────────────────────┘
```

## Failover Test

To test automatic failover:

```bash
# Terminal 1: Start cluster
python cluster_manager.py --action start

# Terminal 2: Write some data
python example_client.py --demo interactive
# Run: SET test_key test_value
# Run: quit

# Terminal 3: Kill primary
pkill -f "node-id node1"

# Wait 5-8 seconds...

# Terminal 2: Try to connect again
python example_client.py --demo interactive
# Note: Will now connect to new primary (was secondary)
```

## Examples

### Example 1: Write User Data
```python
client = KVStoreClient()
client.connect()

user = {
    'id': 1,
    'name': 'Alice',
    'email': 'alice@example.com',
    'tags': ['admin', 'developer']
}

client.set('user:1', user)
result = client.get('user:1')
print(result)  # {'status': 'OK', 'value': {...}}

client.disconnect()
```

### Example 2: Batch Operations
```python
client = KVStoreClient()
client.connect()

# Write multiple keys
for i in range(100):
    client.set(f'key:{i}', {'index': i, 'value': i*10})

# Read them back
for i in range(100):
    result = client.get(f'key:{i}')
    assert result['value']['index'] == i

client.disconnect()
```

### Example 3: Check Node Status
```python
for port in [6379, 6380, 6381]:
    client = KVStoreClient(port=port)
    client.connect()
    status = client.status()
    print(f"Node {status['node_id']}: {status['role']}")
    client.disconnect()
```

## Troubleshooting

### Port Already in Use
```bash
# Find and kill existing processes
pkill -f kv_store_server.py

# Or manually
lsof -i :6379
kill -9 <PID>
```

### Can't Connect to Cluster
```bash
# Check if nodes are running
python cluster_manager.py --action status

# Expected output:
# ✓ node1 (PRIMARY  ) - Port 6379: RUNNING
# ✓ node2 (SECONDARY) - Port 6380: RUNNING
# ✓ node3 (SECONDARY) - Port 6381: RUNNING
```

### Replication Not Working
1. Verify primary is running: `python cluster_manager.py --action status`
2. Check ports 6379, 6380, 6381 are accessible
3. Review server logs for errors
4. Restart cluster: `pkill -f kv_store_server.py` then `python cluster_manager.py --action start`

## Files Overview

| File | Purpose |
|------|---------|
| `kv_store_server.py` | Main server with replication & clustering |
| `cluster_manager.py` | Start/manage 3-node cluster |
| `example_client.py` | Client examples and demos |
| `test_replication.py` | Comprehensive test suite |
| `CLUSTERING.md` | Detailed clustering documentation |

## Next Steps

1. **Run examples**: `python example_client.py --demo all`
2. **Run tests**: `python test_replication.py`
3. **Test failover**: Kill primary, observe election
4. **Read docs**: See `CLUSTERING.md` for detailed info
5. **Integrate**: Use examples as templates for your application

## Common Questions

**Q: Can secondaries serve reads?**  
A: No, only primary serves reads. This ensures consistency.

**Q: What happens when primary fails?**  
A: One of the secondaries is elected as new primary within 5-8 seconds.

**Q: Is data persisted?**  
A: No, it's in-memory. On restart, data is lost.

**Q: Can I have more than 3 nodes?**  
A: Yes, edit `kv_store_server.py` to add more nodes.

**Q: How does replication work?**  
A: Primary async sends operations to secondaries. Eventual consistency.

## Support

For more details, see:
- `CLUSTERING.md` - Full clustering documentation
- `example_client.py` - Client examples with code
- `test_replication.py` - Test suite showing expected behavior

---

**Ready to go!** Start with:
```bash
python cluster_manager.py --action start
```
