# KV Store Database Server - Replication & Clustering Guide

## Overview

This KV Store implementation now supports **3-node cluster replication** with automatic leader election. The cluster consists of:
- **1 Primary Node**: Handles all reads and writes
- **2 Secondary Nodes**: Replicate data from primary, can become primary if primary fails

## Architecture

### Cluster Topology
```
                 ┌─────────────────┐
                 │   Primary (P)   │
                 │   Node 1:6379   │
                 └────────┬────────┘
                          │
                  ┌───────┴────────┐
                  │                │
          ┌───────▼────────┐  ┌────▼───────┐
          │  Secondary (S) │  │ Secondary  │
          │   Node2:6380   │  │  Node3:6381│
          └────────────────┘  └────────────┘

Data Flow:
  Writes/Reads → Primary → Replicate → Secondaries
  
Failover:
  Primary Down → Election → Secondary Promoted → New Primary
```

## Core Features

### 1. **Data Replication**
- All writes to primary are automatically replicated to secondaries
- Replication happens asynchronously (best-effort)
- Replication log tracks all operations (SET, DELETE)
- Secondaries maintain full copy of data

### 2. **Primary-Only Operations**
- **Reads**: Only allowed on primary node
- **Writes (SET)**: Only allowed on primary node
- **Deletes**: Only allowed on primary node
- Secondary nodes reject client operations and return error

### 3. **Leader Election**
- Raft-inspired election mechanism
- Triggered when primary is detected as down
- Secondary nodes detect primary failure via heartbeat timeout
- Election uses voting system with majority quorum
- Successful candidate becomes new primary

### 4. **Heartbeat Mechanism**
- Primary sends periodic heartbeats to secondaries
- Confirms primary is alive and responsive
- Failure to receive heartbeat within timeout triggers election

## Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

## Running the Cluster

### Option 1: Using Cluster Manager (Recommended)

```bash
# Start all 3 nodes at once
python cluster_manager.py --action start

# In another terminal, check cluster status
python cluster_manager.py --action status
```

### Option 2: Manual Node Startup

```bash
# Terminal 1 - Start Primary
python kv_store_server.py --node-id node1 --port 6379 --primary

# Terminal 2 - Start Secondary 1
python kv_store_server.py --node-id node2 --port 6380

# Terminal 3 - Start Secondary 2
python kv_store_server.py --node-id node3 --port 6381
```

## API Commands

### Basic Commands

#### SET (Write)
```bash
SET <key> <value>
```
**Example:**
```
SET user:1 {"name":"Alice","age":30}
```
**Response:**
```json
{"status": "OK", "message": "Key 'user:1' set"}
```
**Note**: Only works on primary (port 6379)

#### GET (Read)
```bash
GET <key>
```
**Example:**
```
GET user:1
```
**Response:**
```json
{"status": "OK", "value": {"name":"Alice","age":30}}
```
**Note**: Only works on primary (port 6379)

#### DELETE (Remove)
```bash
DELETE <key>
```
**Example:**
```
DELETE user:1
```
**Response:**
```json
{"status": "OK"}
```
**Note**: Only works on primary (port 6379)

### Cluster Commands

#### PING
```bash
PING
```
**Response:**
```json
{"status": "OK", "message": "PONG"}
```

#### STATUS
```bash
STATUS
```
**Response:**
```json
{
  "status": "OK",
  "node_id": "node1",
  "role": "primary",
  "election_term": 0
}
```

#### SHUTDOWN
```bash
SHUTDOWN
```
Gracefully shuts down the node.

## Client Examples

### Python Client

```python
import socket
import json

class KVClient:
    def __init__(self, host='127.0.0.1', port=6379):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host, port))
    
    def execute(self, command):
        self.sock.send(command.encode() + b'\n')
        response = self.sock.recv(4096)
        return json.loads(response.decode())
    
    def set(self, key, value):
        return self.execute(f'SET {key} {json.dumps(value)}')
    
    def get(self, key):
        return self.execute(f'GET {key}')
    
    def delete(self, key):
        return self.execute(f'DELETE {key}')

# Usage
client = KVClient()
client.set('user:1', {'name': 'Alice'})
print(client.get('user:1'))
client.delete('user:1')
```

### Bash Client Example

```bash
# Connect to primary and write data
(echo 'SET mykey myvalue'; sleep 1) | nc 127.0.0.1 6379

# Read from primary
(echo 'GET mykey'; sleep 1) | nc 127.0.0.1 6379

# Check node status
(echo 'STATUS'; sleep 1) | nc 127.0.0.1 6379
```

## Replication Behavior

### Write Flow
```
Client Request to Primary
         ↓
  Update Primary Store
         ↓
 Log Operation in Replication Log
         ↓
  Return OK to Client
         ↓
Async: Send replication command to each secondary
         ↓
Secondaries apply operation to their stores
```

### Read Flow
```
Client Request to Primary
         ↓
   Check if Primary
         ↓
 Lookup key in store
         ↓
  Return value or error
```

### Secondary Replication Process
1. Primary performs SET/DELETE operation
2. Operation is added to replication log
3. Primary sends async replication command to secondaries
4. Secondary receives command with operation details
5. Secondary applies operation to its data store
6. Secondary confirms receipt

## Failover & Leader Election

### Detection Phase
- Secondaries monitor primary heartbeat
- Heartbeat timeout = 5-8 seconds (randomized)
- When timeout expires, secondary enters election phase

### Election Phase
1. Secondary increments election term
2. Candidate sends election request to all nodes
3. Each node votes once per term
4. Majority quorum (2 out of 3) needed to win
5. Winning candidate becomes primary

### Election Algorithm
```
Quorum = (N // 2) + 1
For N=3: Quorum = 2

Node requesting election needs:
- Its own vote (1)
- At least 1 other node's vote
- Total: 2 votes → Becomes PRIMARY
```

### Post-Election
- New primary syncs with secondaries
- New primary accepts client connections
- Old primary (if back online) becomes secondary

## Testing

### Run All Tests

```bash
python test_replication.py -v
```

### Test Categories

#### Replication Tests (`TestKVStoreReplication`)
- ✓ Primary node starts as primary
- ✓ Secondary nodes start as secondary
- ✓ Writes on secondary fail
- ✓ Writes on primary succeed
- ✓ Data replication to secondaries
- ✓ Multiple writes replicated
- ✓ Delete operations replicated
- ✓ JSON values replicated
- ✓ Reads on secondary fail

#### Leader Election Tests (`TestLeaderElection`)
- ✓ Election initialization
- ✓ Secondary detects primary failure
- ✓ Election request handling

#### Consistency Tests (`TestClusterConsistency`)
- ✓ All nodes accessible
- ✓ Primary-secondary consistency
- ✓ Concurrent writes
- ✓ Write-then-read consistency

## Configuration

### Cluster Nodes (Default)
```python
all_nodes = [
    {"node_id": "node1", "host": "127.0.0.1", "port": 6379},
    {"node_id": "node2", "host": "127.0.0.1", "port": 6380},
    {"node_id": "node3", "host": "127.0.0.1", "port": 6381},
]
```

### Election Parameters
- **Heartbeat interval**: 2 seconds
- **Election timeout**: 5-8 seconds (randomized)
- **Election quorum**: Majority (2 out of 3 nodes)

### Timeouts
- **Connection timeout**: 2 seconds
- **Replication timeout**: 2 seconds

## Limitations & Notes

1. **In-Memory Storage**: Data is not persisted to disk
2. **Async Replication**: Secondaries may lag behind primary
3. **No Partition Tolerance**: Network partitions will disrupt cluster
4. **Best-Effort Delivery**: Replication doesn't guarantee delivery
5. **Single Master**: Only one node can be primary at a time

## Future Enhancements

- [ ] Disk persistence
- [ ] Synchronous replication option
- [ ] Multi-datacenter support
- [ ] Consensus-based replication (Raft/Paxos)
- [ ] Snapshot and restore
- [ ] Read replicas (secondaries can serve reads)
- [ ] Network partition handling

## Troubleshooting

### Cluster Won't Start
```bash
# Check if ports are already in use
netstat -an | grep 637
# Kill existing processes
pkill -f kv_store_server.py
```

### No Replication
1. Check primary is running on port 6379
2. Verify secondaries can connect to primary
3. Check firewall rules
4. Review server logs for errors

### Election Issues
1. Ensure all 3 nodes are running
2. Check election timeout (should be 5-8s)
3. Verify heartbeat is being sent from primary
4. Review election logs

## Internal Message Formats

### Replication Command
```json
{
  "type": "REPLICATE",
  "operation": "SET",
  "key": "mykey",
  "value": "myvalue"
}
```

### Election Request
```json
{
  "type": "ELECTION",
  "candidate_id": "node2",
  "term": 1
}
```

### Heartbeat
```json
{
  "type": "HEARTBEAT",
  "from_node": "node1"
}
```

### Sync Request
```json
{
  "type": "SYNC",
  "from_node": "node1",
  "since_timestamp": 0
}
```

## Performance Considerations

- **Write Performance**: Limited by replication time (2+ nodes must acknowledge)
- **Read Performance**: Only on primary (no read replicas)
- **Failover Time**: 5-8 seconds (election timeout) + election time
- **Network Overhead**: Heartbeat + replication traffic

## Example Scenarios

### Scenario 1: Normal Operation
```
1. Client connects to node1 (primary, port 6379)
2. Client sends: SET user:100 {"name":"Bob"}
3. Primary stores locally and replicates to node2 & node3
4. All nodes have consistent data
5. Client reads: GET user:100 → returns {"name":"Bob"}
```

### Scenario 2: Primary Failure
```
1. Primary (node1) crashes or becomes unreachable
2. node2 & node3 detect missing heartbeat after 5-8 seconds
3. node2 initiates election, increments term to 1
4. node2 requests votes from node1 & node3
5. node3 votes for node2
6. node2 wins election (2 out of 3 votes)
7. node2 becomes PRIMARY
8. node2 starts accepting writes and reads
9. If node1 recovers, it becomes secondary
```

### Scenario 3: Writes During Election
```
1. Client is writing to primary (node1)
2. node1 fails before replication completes
3. Election begins, node2 becomes primary
4. Client must reconnect to new primary (node2)
5. Previous incomplete operation is lost
6. Client application handles retry logic
```

## References

- [Raft Consensus Algorithm](https://raft.github.io/)
- [Redis Replication](https://redis.io/topics/replication)
- [Leader Election Patterns](https://en.wikipedia.org/wiki/Leader_election)
