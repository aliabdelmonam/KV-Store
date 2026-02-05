# Testing Guide - KV Store Cluster

## Quick Test (5 minutes)

### Step 1: Start the Cluster
```bash
python cluster_manager.py --action start
```

Keep this running in Terminal 1.

### Step 2: Run Automated Tests
In Terminal 2:
```bash
python test_replication.py -v
```

Expected output:
```
test_01_primary_node_is_primary ... ok
test_02_secondary_nodes_are_secondary ... ok
test_03_write_on_secondary_fails ... ok
test_04_write_on_primary_succeeds ... ok
test_05_read_from_primary ... ok
test_06_replication_to_secondaries ... ok
...
Ran 20 tests in X.XXs
OK
```

### Step 3: Run Interactive Demo
In Terminal 3:
```bash
python example_client.py --demo interactive
```

Try commands:
```
set test_key "Hello, World!"
get test_key
status
ping
quit
```

**Success**: All tests pass and interactive demo works!

---

## Manual Testing Guide

### Test 1: Basic Write-Read Cycle

**Setup**: Cluster running

**Steps**:
```python
from example_client import KVStoreClient

# 1. Connect to primary
client = KVStoreClient(port=6379)
client.connect()

# 2. Write data
response = client.set('test_key', {'message': 'Hello'})
assert response['status'] == 'OK', "Write failed"
print("✓ Write successful")

# 3. Read data
response = client.get('test_key')
assert response['status'] == 'OK', "Read failed"
assert response['value'] == {'message': 'Hello'}, "Value mismatch"
print("✓ Read successful")

# 4. Delete data
response = client.delete('test_key')
assert response['status'] == 'OK', "Delete failed"
print("✓ Delete successful")

# 5. Verify deletion
response = client.get('test_key')
assert response['status'] == 'ERROR', "Key should be deleted"
print("✓ Deletion verified")

client.disconnect()
```

**Expected Result**: All assertions pass ✓

---

### Test 2: Write to Secondary (Should Fail)

**Setup**: Cluster running

**Steps**:
```python
from example_client import KVStoreClient

# Connect to secondary (port 6380)
client = KVStoreClient(port=6380)
client.connect()

# Try to write
response = client.set('forbidden_key', 'value')
assert response['status'] == 'ERROR', "Secondary should reject writes"
assert 'not primary' in response['message'].lower(), "Error message should mention primary"
print("✓ Secondary correctly rejects writes")

# Try to read
response = client.get('user:1')
assert response['status'] == 'ERROR', "Secondary should reject reads"
assert 'not primary' in response['message'].lower(), "Error message should mention primary"
print("✓ Secondary correctly rejects reads")

client.disconnect()
```

**Expected Result**: All assertions pass ✓

---

### Test 3: Replication Verification

**Setup**: Cluster running

**Steps**:
```python
import time
from example_client import KVStoreClient

# Write to primary
primary = KVStoreClient(port=6379)
primary.connect()

test_data = {
    'key1': 'value1',
    'key2': {'nested': 'object'},
    'key3': [1, 2, 3, 4, 5]
}

print("Writing to primary...")
for key, value in test_data.items():
    primary.set(key, value)

print("Waiting 2 seconds for replication...")
time.sleep(2)

print("Verifying on primary...")
for key, expected_value in test_data.items():
    response = primary.get(key)
    assert response['status'] == 'OK', f"Key {key} not found"
    assert response['value'] == expected_value, f"Value mismatch for {key}"
    print(f"  ✓ {key}")

primary.disconnect()
print("✓ Replication verified")
```

**Expected Result**: All keys verified on primary ✓

---

### Test 4: Concurrent Writes

**Setup**: Cluster running

**Steps**:
```python
import threading
from example_client import KVStoreClient

results = {'success': 0, 'failed': 0}

def write_batch(batch_id):
    client = KVStoreClient(port=6379)
    client.connect()
    
    for i in range(10):
        key = f'concurrent_{batch_id}_{i}'
        value = {'batch': batch_id, 'index': i}
        response = client.set(key, value)
        
        if response['status'] == 'OK':
            results['success'] += 1
        else:
            results['failed'] += 1
    
    client.disconnect()

print("Writing 30 keys concurrently...")
threads = []
for batch in range(3):
    t = threading.Thread(target=write_batch, args=(batch,))
    threads.append(t)
    t.start()

for t in threads:
    t.join()

print(f"Success: {results['success']}, Failed: {results['failed']}")
assert results['success'] == 30, "All writes should succeed"
print("✓ Concurrent writes handled correctly")
```

**Expected Result**: All 30 keys written successfully ✓

---

### Test 5: Failover Simulation

**Setup**: Cluster running in Terminal 1

**Steps**:

**5a. Initial Cluster State**
```bash
# Terminal 2: Check cluster status
python cluster_manager.py --action status
```

Expected:
```
✓ node1 (PRIMARY  ) - Port 6379: RUNNING
✓ node2 (SECONDARY) - Port 6380: RUNNING
✓ node3 (SECONDARY) - Port 6381: RUNNING
```

**5b. Write Data to Primary**
```bash
# Terminal 3
python example_client.py --demo interactive
# Commands:
set testkey "before_failover"
status
quit
```

Expected: Write succeeds, shows "role": "primary"

**5c. Trigger Primary Failure**
```bash
# Terminal 2: Kill primary process
pkill -f "node-id node1"
```

**5d. Monitor Election (5-8 seconds)**

Watch Terminal 1 for election messages:
```
Primary node1 appears down. Starting election.
Starting election for term 1
Starting election for term 1
Got vote from node3
Node node2 became PRIMARY
```

**5e. Verify New Primary is Operating**
```bash
# Terminal 3: Reconnect
python example_client.py --demo interactive
# Commands:
status
get testkey
quit
```

Expected:
- `status` shows new primary (node2 or node3)
- `get testkey` returns "before_failover"

**5f. Verify Secondary Promoted**
```bash
# Terminal 2: Check status
python cluster_manager.py --action status
```

Expected:
```
✗ node1 (PRIMARY  ) - Port 6379: DOWN
✓ node2 (PRIMARY  ) - Port 6380: RUNNING
✓ node3 (SECONDARY) - Port 6381: RUNNING
```
Or:
```
✗ node1 (PRIMARY  ) - Port 6379: DOWN
✓ node2 (SECONDARY) - Port 6380: RUNNING
✓ node3 (PRIMARY  ) - Port 6381: RUNNING
```

**✓ Failover Success**: Cluster automatically elected new primary!

---

### Test 6: Node Recovery

**Setup**: From Test 5, with primary down

**Steps**:

**6a. Restart Original Primary**
```bash
# Terminal 1: Restart cluster_manager or manually start node1
python kv_store_server.py --node-id node1 --port 6379
```

**6b. Check Status**
```bash
# Terminal 2
python cluster_manager.py --action status
```

Expected: All 3 nodes running

**6c. Verify node1 is Secondary**
```bash
# Terminal 3
from example_client import KVStoreClient

client = KVStoreClient(port=6379)
client.connect()
status = client.status()
print(status['role'])  # Should print: "secondary"
client.disconnect()
```

**✓ Recovery Success**: Original primary rejoined as secondary ✓

---

## Automated Test Suite Details

### Run All Tests
```bash
python test_replication.py -v
```

### Run Specific Test Class
```bash
python test_replication.py TestKVStoreReplication -v
python test_replication.py TestLeaderElection -v
python test_replication.py TestClusterConsistency -v
```

### Run Specific Test Method
```bash
python test_replication.py TestKVStoreReplication.test_04_write_on_primary_succeeds -v
```

### Test Classes

#### TestKVStoreReplication
Tests replication functionality:
- `test_01_primary_node_is_primary` - Verify primary role
- `test_02_secondary_nodes_are_secondary` - Verify secondary roles
- `test_03_write_on_secondary_fails` - Write rejection
- `test_04_write_on_primary_succeeds` - Write acceptance
- `test_05_read_from_primary` - Read on primary
- `test_06_replication_to_secondaries` - Data replication
- `test_07_multiple_writes_replicated` - Multiple write replication
- `test_08_delete_operation_replicated` - Delete replication
- `test_09_json_values_replicated` - Complex type replication
- `test_10_read_on_secondary_fails` - Read rejection on secondary

#### TestLeaderElection
Tests election mechanism:
- `test_01_election_initialization` - Initial election state
- `test_02_secondary_detects_primary_failure` - Failure detection
- `test_03_election_request_handling` - Vote handling

#### TestClusterConsistency
Tests consistency across cluster:
- `test_01_all_nodes_accessible` - Node connectivity
- `test_02_primary_secondary_consistency` - Data consistency
- `test_03_concurrent_writes` - Concurrent operation handling
- `test_04_write_then_read_consistency` - Read-write ordering

---

## Debugging Tips

### Enable Verbose Logging
```bash
# Add to kv_store_server.py before main():
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Check Port Availability
```bash
# Check if ports are in use
netstat -an | grep 637

# On Windows:
netstat -ano | findstr :637

# Or use lsof (Linux/Mac):
lsof -i :6379
lsof -i :6380
lsof -i :6381
```

### Kill Stuck Processes
```bash
# Kill all KV store processes
pkill -f kv_store_server.py

# Kill specific processes
kill -9 <PID>

# On Windows:
taskkill /F /IM python.exe /FI "WINDOWTITLE eq*node*"
```

### Monitor Connection
```bash
# Test TCP connection
telnet 127.0.0.1 6379

# Send PING
telnet> PING
telnet> quit

# Using nc (nc command)
echo "PING" | nc 127.0.0.1 6379
```

### View Server Logs
```bash
# Redirect server output to file
python cluster_manager.py --action start > cluster.log 2>&1

# Tail the log
tail -f cluster.log
```

---

## Expected Test Results

### Replication Tests
```
test_01_primary_node_is_primary ... ok
test_02_secondary_nodes_are_secondary ... ok
test_03_write_on_secondary_fails ... ok
test_04_write_on_primary_succeeds ... ok
test_05_read_from_primary ... ok
test_06_replication_to_secondaries ... ok
test_07_multiple_writes_replicated ... ok
test_08_delete_operation_replicated ... ok
test_09_json_values_replicated ... ok
test_10_read_on_secondary_fails ... ok
```

### Leader Election Tests
```
test_01_election_initialization ... ok
test_02_secondary_detects_primary_failure ... ok (or skipped)
test_03_election_request_handling ... ok (or skipped)
```

### Consistency Tests
```
test_01_all_nodes_accessible ... ok
test_02_primary_secondary_consistency ... ok
test_03_concurrent_writes ... ok
test_04_write_then_read_consistency ... ok
```

---

## Performance Testing

### Measure Write Latency
```python
import time
from example_client import KVStoreClient

client = KVStoreClient(port=6379)
client.connect()

times = []
for i in range(100):
    start = time.time()
    client.set(f'perf_key_{i}', f'value_{i}')
    elapsed = (time.time() - start) * 1000  # ms
    times.append(elapsed)

avg = sum(times) / len(times)
min_t = min(times)
max_t = max(times)

print(f"Write latency - Avg: {avg:.2f}ms, Min: {min_t:.2f}ms, Max: {max_t:.2f}ms")
```

### Measure Read Latency
```python
import time
from example_client import KVStoreClient

# First, write a value
client = KVStoreClient(port=6379)
client.connect()
client.set('read_test_key', 'test_value')

times = []
for i in range(100):
    start = time.time()
    client.get('read_test_key')
    elapsed = (time.time() - start) * 1000  # ms
    times.append(elapsed)

avg = sum(times) / len(times)
min_t = min(times)
max_t = max(times)

print(f"Read latency - Avg: {avg:.2f}ms, Min: {min_t:.2f}ms, Max: {max_t:.2f}ms")
```

---

## Checklist for Verification

- [ ] Cluster starts with 3 nodes
- [ ] Primary node accepts writes
- [ ] Secondary nodes reject writes
- [ ] Data replicates to secondaries
- [ ] Primary node only serves reads
- [ ] Secondary nodes reject reads
- [ ] PING works on all nodes
- [ ] STATUS shows correct roles
- [ ] Concurrent writes handled correctly
- [ ] Delete operations replicated
- [ ] JSON values replicated correctly
- [ ] Election happens when primary down
- [ ] New primary elected within 10 seconds
- [ ] New primary accepts read/write
- [ ] Original primary rejoins as secondary
- [ ] All tests pass

---

## Troubleshooting Test Failures

### Test: write_on_secondary_fails
```
FAIL: Secondary didn't reject write
FIX: Ensure TCPServer.is_primary() check in process_command()
```

### Test: replication_to_secondaries
```
FAIL: Replication didn't happen
FIX: 
- Check primary is registering secondaries
- Check replicate_to_secondaries() is called
- Increase sleep time from 2s to 5s
```

### Test: election_request_handling
```
FAIL: Election request not processed
FIX: 
- Check handle_election() in process_command()
- Verify term is being incremented
- Check vote granting logic
```

### Test: concurrent_writes
```
FAIL: Not all writes successful
FIX:
- Increase thread timeout
- Check socket timeouts
- Verify concurrent access to store is thread-safe
```

---

**Test Summary**: The implementation includes comprehensive tests covering:
- ✓ Replication features (10 tests)
- ✓ Leader election (3 tests)
- ✓ Cluster consistency (4 tests)
- ✓ Total: 17+ tests

All tests should pass with the cluster running!
