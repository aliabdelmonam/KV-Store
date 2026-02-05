# Key-Value Store Benchmarks

This directory contains comprehensive performance benchmarking scripts for the key-value store server.

## Quick Start

**Terminal 1 - Start the Server:**
```bash
cd ..
python kv_store_server.py
```

**Terminal 2 - Run a Benchmark:**
```bash
cd benchmarks

# Quick test
python benchmark_direct.py

# Or run any of the other benchmarks
python benchmark_tcp.py
python benchmark_writes.py
python benchmark_durability.py --writes 100
```

## Benchmarks Overview

### 1. Direct Performance Benchmark (`benchmark_direct.py`)

**Purpose:** Measure raw in-memory performance with no network overhead

**What it tests:**
- Direct function calls to KeyValueStore class
- No TCP/socket overhead
- Performance with different store sizes (0, 100, 1K, 5K, 10K keys)

**Run it:**
```bash
python benchmark_direct.py
```

**Example output:**
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

Benchmark: 100 existing keys
  Pre-populating store with 100 keys... Done
  Measuring 500 write operations... Done
  Writes/sec: 84500.50
  Avg time: 0.0118ms
  Min time: 0.0086ms, Max time: 0.3100ms
```

**What to expect:**
- Baseline performance (highest throughput)
- Very low latencies (~0.01ms per operation)
- Minimal degradation with store size growth

---

### 2. TCP Protocol Benchmark (`benchmark_tcp.py`)

**Purpose:** Measure performance through TCP socket connections

**What it tests:**
- TCP protocol overhead
- Client-server communication
- Multiple write operations per test case
- Performance with different store sizes

**Run it:**
```bash
python benchmark_tcp.py
```

**Example output:**
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

Benchmark: 100 existing keys
  Pre-populating store with 100 keys... Done
  Measuring 500 write operations via TCP... Done
  Writes/sec: 2280.45
  Avg time: 0.4383ms
  Min time: 0.1200ms, Max time: 2.3450ms
```

**What to expect:**
- Much lower throughput than direct (network overhead)
- Higher latencies (~0.4ms per operation)
- Performance difference: direct vs TCP shows protocol overhead

**Calculation:**
```
TCP Overhead = Direct Performance / TCP Performance
            = 85714 / 2350
            = ~36x slower due to network
```

---

### 3. Write Performance vs Store Size (`benchmark_writes.py`)

**Purpose:** Test how write performance degrades as the store grows

**What it tests:**
- Write performance at different store sizes (0, 100, 1K, 5K, 10K keys)
- Performance degradation with data growth
- Memory/lookup efficiency

**Run it:**
```bash
python benchmark_writes.py
```

**Example output:**
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

Benchmark: 1000 existing keys
  Pre-populating store with 1000 keys... Done
  Measuring 10 write operations... Done
  Writes/sec: 2300.15
  Avg time: 0.4348ms
  Min time: 0.3950ms, Max time: 0.7100ms

...
```

**What to expect:**
- Small degradation as store grows
- Python dict performance is O(1) on average
- Lock contention may increase slightly
- Typical: <5% performance drop per 10x store size increase

---

### 4. Durability Benchmark (`benchmark_durability.py`)

**Purpose:** Test data persistence under forced server shutdown (kill -9)

**How it works:**
1. Starts a fresh server
2. Sends write operations and tracks which received "OK" responses
3. Randomly kills the server with `kill -9` (Unix) or `taskkill /F` (Windows)
4. Restarts the server
5. Checks which writes actually persisted
6. Reports data loss rate

**Run it:**

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

**Example output:**
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

**What to expect:**
- **No persistence**: 100% data loss (server is in-memory only)
- **With persistence**: Depends on when data is flushed to disk
- **Key metrics:**
  - Data loss rate: % of successful writes that didn't persist
  - Shows reliability of data storage

**Interpreting results:**
```
Data Loss Rate = (Writes Lost) / (Total Successful Writes) * 100%

0% = Perfect durability (all data persisted)
100% = No durability (all data lost)
50% = Some writes persisted, some lost (partial durability)
```

---

## Benchmark Comparison Table

| Benchmark | Command | Performance | Shows |
|-----------|---------|-------------|-------|
| Direct | `benchmark_direct.py` | Highest | Raw speed |
| TCP | `benchmark_tcp.py` | 30-40x slower | Network overhead |
| Write Size | `benchmark_writes.py` | Medium | Scalability |
| Durability | `benchmark_durability.py` | N/A | Data safety |

## Understanding Performance Metrics

### Writes Per Second (Throughput)
```
Higher is better
Example: 2400 writes/sec = 2400 operations in 1 second
```

### Latency (Min/Max/Avg Time in ms)
```
Lower is better
0.4167ms = 0.0004167 seconds = very fast

Interpretation:
- Min: Best case
- Max: Worst case (could be system interruption)
- Avg: Typical operation time
```

### Standard Deviation (Variance in latency)
```
Lower is better
Consistent latency = predictable performance
High variance = unpredictable latencies
```

## Tips for Running Benchmarks

1. **Baseline First**: Run `benchmark_direct.py` to get baseline performance
2. **Server Dependency**: Ensure server is running for TCP/write benchmarks
3. **Warm Up**: Benchmarks auto-warm with pre-population
4. **No Other Load**: Close other apps for accurate measurements
5. **Run Multiple Times**: Results vary slightly between runs
6. **Compare Results**: Keep results to compare improvements

## Saved Results

Some benchmarks save results:

```
benchmark_direct_results.json  # Direct benchmark results
```

Example format:
```json
{
  "existing_keys": 0,
  "writes_per_second": 85714.29,
  "min_time_ms": 0.0087,
  "max_time_ms": 0.2839,
  "avg_time_ms": 0.0117
}
```

## Performance Expectations

### Healthy Server Performance

**Direct Performance:**
- ~80,000+ writes/sec
- ~0.01ms average latency
- <1% latency variance

**TCP Performance:**
- ~2,000-3,000 writes/sec
- ~0.4ms average latency
- Depends on network conditions

**Durability:**
- 0% data loss with persistence enabled
- 100% data loss without persistence (in-memory only)

## Troubleshooting

### "Connection refused" error
```
Make sure the server is running:
python kv_store_server.py
```

### "Port already in use" error
```
Kill existing server:
# Windows
taskkill /F /IM python.exe /T

# Linux/Mac
killall python
```

### Very low performance results
```
Check:
1. Other apps not consuming CPU/network
2. Server not overloaded with other connections
3. System not under stress
```

### Inconsistent results
```
This is normal for network benchmarks
Try running tests multiple times and averaging
```

## Files Structure

```
benchmarks/
├── benchmark_direct.py           # Direct performance (no network)
├── benchmark_tcp.py              # TCP protocol performance
├── benchmark_writes.py           # Performance vs store size
├── benchmark_durability.py       # Data persistence test
├── benchmark_direct_results.json # Saved results
└── README.md                     # This file
```

## Next Steps

1. Run all benchmarks to understand your system's performance
2. Compare results with TCP vs Direct to see network overhead
3. Run durability tests to verify data persistence behavior
4. Use these metrics as baseline for optimizations

## Requirements

- Python 3.7+
- Running server instance (for TCP/write/durability benchmarks)
- Windows/Linux/Mac compatible

---

For general documentation, see [../README.md](../README.md)
