# Key-Value Store Database Server

A lightweight, high-performance, thread-safe key-value store database server with TCP protocol support. Includes comprehensive performance benchmarking tools to measure throughput, latency, and data durability.

## Features

- **TCP Server Protocol**: High-performance Redis-like protocol for direct socket communication
- **Commands**: SET, GET, DELETE, PING, SHUTDOWN, FLUSH, SNAPSHOT
- **Thread-Safe**: Concurrent client handling with proper locking
- **Benchmarking Suite**: Multiple benchmarks to measure performance and durability
  - Direct in-memory performance
  - TCP protocol overhead
  - Write performance at various store sizes
  - Data durability under forced shutdown

## Installation

Install the required dependencies:

```bash
pip install -r requirements.txt
```

Or install manually:

```bash
pip install python-dateutil
```

## Quick Start

### 1. Start the Server

```bash
python kv_store_server.py
```

The server will start on `localhost:6379` (TCP protocol)

```
TCP Server listening on 0.0.0.0:6379
```

### 2. Test with Basic Commands (in another terminal)

**Using Python:**
```python
import socket
import json

def send_command(host, port, command):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))
    sock.send(command.encode('utf-8') + b'\n')
    response = sock.recv(4096).decode('utf-8').strip()
    sock.close()
    return json.loads(response)

# SET a value
result = send_command('localhost', 6379, 'SET mykey "hello world"')
print(result)  # {'status': 'OK', 'message': "Key 'mykey' set"}

# GET a value
result = send_command('localhost', 6379, 'GET mykey')
print(result)  # {'status': 'OK', 'value': 'hello world'}

# DELETE a key
result = send_command('localhost', 6379, 'DELETE mykey')
print(result)  # {'status': 'OK'}

# PING
result = send_command('localhost', 6379, 'PING')
print(result)  # {'status': 'OK', 'message': 'PONG'}
```

**Using telnet (Windows):**
```bash
telnet localhost 6379
# Type: SET key1 "value1"
# Type: GET key1
# Type: PING
```

## Server API Commands

### SET - Store a Key-Value Pair

```
SET <key> <value>
```

**Example:**
```
SET username "john"
SET counter "42"
SET data '{"name": "Alice", "age": 30}'
```

**Response:**
```json
{"status": "OK", "message": "Key 'username' set"}
```

### GET - Retrieve a Value

```
GET <key>
```

**Example:**
```
GET username
GET counter
```

**Response (found):**
```json
{"status": "OK", "value": "john"}
```

**Response (not found):**
```json
{"status": "ERROR", "message": "Key 'nonexistent' not found"}
```

### DELETE - Remove a Key

```
DELETE <key>
```

**Example:**
```
DELETE username
```

**Response (success):**
```json
{"status": "OK"}
```

**Response (key not found):**
```json
{"status": "ERROR"}
```

### PING - Test Connection

```
PING
```

**Response:**
```json
{"status": "OK", "message": "PONG"}
```

### SHUTDOWN - Gracefully Shutdown Server

```
SHUTDOWN
```

**Response:**
```json
{"status": "OK", "message": "Server shutting down"}
```

### FLUSH - Flush All Data

```
FLUSH
```

**Response:**
```json
{"status": "OK", "message": "No persistence enabled"}
```

### SNAPSHOT - Create Data Snapshot

```
SNAPSHOT
```

**Response:**
```json
{"status": "OK", "message": "No persistence enabled"}
```

## Benchmarking

The `benchmarks/` directory contains performance testing scripts. All benchmarks must be run while the server is running.

### Running Benchmarks

**Terminal 1 - Start the Server:**
```bash
python kv_store_server.py
```

**Terminal 2 - Run Benchmarks:**

#### 1. Direct Performance Benchmark (No Protocol Overhead)

```bash
cd benchmarks
python benchmark_direct.py
```

Measures raw in-memory performance without TCP overhead.

**Output Example:**
```
======================================================================
Direct KeyValueStore Performance Benchmark (No HTTP)
======================================================================

Benchmark: 0 existing keys
  Pre-populating store with 0 keys... Done
  Measuring 500 write operations... Done
  Writes/sec: 85714.29
  Avg time: 0.0117ms
  Min time: 0.0087ms, Max time: 0.2839ms
```

#### 2. TCP Protocol Benchmark

```bash
python benchmark_tcp.py
```

Measures write performance through TCP connections with protocol overhead.

**Output Example:**
```
======================================================================
TCP Client Performance Benchmark
======================================================================

Benchmark: 0 existing keys
  Pre-populating store with 0 keys... Done
  Measuring 500 write operations via TCP... Done
  Writes/sec: 2350.15
  Avg time: 0.4255ms
  Min time: 0.1234ms, Max time: 2.1567ms
```

#### 3. Write Performance with Growing Store Size

```bash
python benchmark_writes.py
```

Tests how write performance changes as the store grows with more keys.

**Output Example:**
```
======================================================================
Key-Value Store Write Performance Benchmark
======================================================================

Benchmark: 0 existing keys
  Pre-populating store with 0 keys... Done
  Measuring 10 write operations... Done
  Writes/sec: 2400.50
  Avg time: 0.4167ms
  Min time: 0.3850ms, Max time: 0.6200ms

Benchmark: 100 existing keys
  Pre-populating store with 100 keys... Done
  Measuring 10 write operations... Done
  Writes/sec: 2380.20
  Avg time: 0.4202ms
  Min time: 0.3900ms, Max time: 0.6500ms

...
```

#### 4. Durability Benchmark (Data Loss on Forced Shutdown)

```bash
# Single test with 100 writes
python benchmark_durability.py

# Single test with 500 writes
python benchmark_durability.py --writes 500

# Run 5 tests with 100 writes each
python benchmark_durability.py --tests 5

# Run 5 tests with 200 writes each
python benchmark_durability.py --writes 200 --tests 5
```

Tests data durability by:
1. Starting the server
2. Sending writes and tracking successful responses
3. Force-killing the server at a random point (`kill -9` / `taskkill /F`)
4. Restarting the server
5. Checking which writes persisted
6. Reporting data loss rate

**Output Example:**
```
[Test 1/5]

Starting server...
Server will be killed after write #67/100

Sending writes... [KILL] Done (0.456s)
Successful writes before kill: 67
Total writes with OK status: 67

Restarting server...

Verifying persisted writes...

======================================================================
DURABILITY TEST RESULTS
======================================================================
Total successful writes (got OK): 67
Persisted after restart: 0
Lost writes: 67
Data loss rate: 100.00%
======================================================================
```

## Benchmarking Summary

| Benchmark | Command | Purpose |
|-----------|---------|---------|
| Direct | `python benchmark_direct.py` | Raw in-memory throughput (no network) |
| TCP | `python benchmark_tcp.py` | TCP protocol performance |
| Write Size Impact | `python benchmark_writes.py` | Performance degradation with store growth |
| Durability | `python benchmark_durability.py` | Data survival under forced shutdown |

## Project Structure

```
├── kv_store_server.py          # Main server implementation
├── kvstore.db.snapshot         # Database snapshot file (if persistence enabled)
├── requirements.txt            # Python dependencies
├── README.md                   # This file
│
└── benchmarks/
    ├── benchmark_direct.py     # Direct performance benchmark
    ├── benchmark_tcp.py        # TCP protocol benchmark
    ├── benchmark_writes.py     # Write performance vs store size
    ├── benchmark_durability.py # Durability under forced shutdown
    ├── benchmark_direct_results.json
    └── README.md              # Benchmark documentation
```

## Python Code Examples

### Example 1: Simple Client

```python
import socket
import json

HOST = "localhost"
PORT = 6379

def send_command(command):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((HOST, PORT))
    sock.send(command.encode('utf-8') + b'\n')
    response = sock.recv(4096).decode('utf-8').strip()
    sock.close()
    return json.loads(response)

# Store values
send_command('SET user:1:name "Alice"')
send_command('SET user:1:email "alice@example.com"')

# Retrieve values
result = send_command('GET user:1:name')
print(result)  # {'status': 'OK', 'value': 'Alice'}

# Delete values
send_command('DELETE user:1:name')
```

### Example 2: Batch Operations

```python
import socket
import json

def batch_set(data_dict):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(("localhost", 6379))
    
    for key, value in data_dict.items():
        value_json = json.dumps(value)
        command = f'SET {key} "{value_json}"'
        sock.send(command.encode('utf-8') + b'\n')
        response = sock.recv(4096)  # Read response
    
    sock.close()

# Set multiple values
batch_set({
    'product:1': {'name': 'Laptop', 'price': 999},
    'product:2': {'name': 'Mouse', 'price': 29},
    'product:3': {'name': 'Keyboard', 'price': 79},
})
```

### Example 3: Connection Pool

```python
import socket
import json

class KVStoreClient:
    def __init__(self, host="localhost", port=6379):
        self.host = host
        self.port = port
        self.sock = None
        self.connect()
    
    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port))
    
    def send_command(self, command):
        self.sock.send(command.encode('utf-8') + b'\n')
        response = self.sock.recv(4096).decode('utf-8').strip()
        return json.loads(response)
    
    def set(self, key, value):
        cmd = f'SET {key} "{json.dumps(value)}"'
        return self.send_command(cmd)
    
    def get(self, key):
        return self.send_command(f'GET {key}')
    
    def delete(self, key):
        return self.send_command(f'DELETE {key}')
    
    def close(self):
        self.sock.close()

# Usage
client = KVStoreClient()

client.set('config:debug', True)
client.set('config:timeout', 30)

result = client.get('config:debug')
print(result)  # {'status': 'OK', 'value': True}

client.delete('config:debug')
client.close()
```

## Performance Tips

1. **Reuse Connections**: TCP connections are expensive. Reuse them for multiple operations.
2. **Batch Operations**: Group multiple operations to reduce network overhead.
3. **Use Direct Access**: If running benchmarks, use `benchmark_direct.py` for maximum performance.
4. **Monitor Store Size**: Write performance may degrade with very large stores.

## Troubleshooting

### Server won't start

```
Address already in use
```

**Solution**: Kill the existing process using port 6379:
```bash
# Windows
netstat -ano | find ":6379"
taskkill /F /PID <PID>

# Linux/Mac
lsof -i :6379
kill -9 <PID>
```

### Connection refused

```
ConnectionRefusedError: [Errno 111] Connection refused
```

**Solution**: Make sure the server is running with `python kv_store_server.py`

### Command format error

```
{"status": "ERROR", "message": "Unknown command"}
```

**Solution**: Check command syntax. Commands are case-insensitive but must be valid.

Valid commands:
- `SET key value`
- `GET key`
- `DELETE key`
- `PING`
- `SHUTDOWN`

## Requirements

- Python 3.7+
- No external dependencies required for the server
- `python-dateutil` optional (for some utilities)

## Architecture

### KeyValueStore Class
Thread-safe in-memory storage with:
- `set(key, value)` - Store a value
- `get(key)` - Retrieve a value
- `delete(key)` - Remove a value
- Thread locks for concurrent access safety

### TCPServer Class
Network interface that:
- Listens on port 6379
- Accepts multiple concurrent connections
- Handles each client in a separate thread
- Parses and executes commands
- Returns JSON responses

## Future Enhancements

- [ ] Persistence to disk (RDB snapshots)
- [ ] Write-ahead logging (WAL)
- [ ] Expiration/TTL support
- [ ] Pub/Sub messaging
- [ ] Cluster support
- [ ] TLS/SSL encryption
- [ ] Authentication

## License

MIT
