# Visual Guide - KV Store Cluster Architecture

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    KV Store Cluster (3 Nodes)                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                   PRIMARY NODE (node1)                   │  │
│  │                  127.0.0.1:6379                          │  │
│  ├──────────────────────────────────────────────────────────┤  │
│  │                                                          │  │
│  │  ┌────────────────────────────────────────────────────┐ │  │
│  │  │  KeyValueStore                                     │ │  │
│  │  │  ┌──────────┐ ┌──────────┐ ┌──────────┐           │ │  │
│  │  │  │ user:1   │ │ config:1 │ │ data:100 │ ...      │ │  │
│  │  │  └──────────┘ └──────────┘ └──────────┘           │ │  │
│  │  └────────────────────────────────────────────────────┘ │  │
│  │                                                          │  │
│  │  ┌────────────────────────────────────────────────────┐ │  │
│  │  │  ReplicationLog                                    │ │  │
│  │  │  ┌────────────────────────────────────────────────┐ │ │  │
│  │  │  │ T=1.001  SET user:1 {"name":"Alice"}         │ │ │  │
│  │  │  │ T=1.002  SET config:1 30                      │ │ │  │
│  │  │  │ T=1.003  SET data:100 {...}                  │ │ │  │
│  │  │  │ T=1.004  DELETE user:1                        │ │ │  │
│  │  │  └────────────────────────────────────────────────┘ │ │  │
│  │  └────────────────────────────────────────────────────┘ │  │
│  │                                                          │  │
│  │  TCP Server: Listens on port 6379                      │  │
│  │  - Accepts client connections                          │  │
│  │  - Processes SET, GET, DELETE commands                 │  │
│  │  - Sends replication commands to secondaries           │  │
│  │  - Sends heartbeats every 2 seconds                    │  │
│  │                                                          │  │
│  └──────────────────────────────────────────────────────────┘  │
│           │                              │                     │
│           │ REPLICATE                    │ HEARTBEAT          │
│           │ {SET/DELETE}                 │ {alive}            │
│           ▼                              ▼                     │
│  ┌──────────────────┐          ┌──────────────────┐            │
│  │  SECONDARY (n2)  │          │  SECONDARY (n3)  │            │
│  │  127.0.0.1:6380  │          │  127.0.0.1:6381  │            │
│  ├──────────────────┤          ├──────────────────┤            │
│  │ Same data copy   │          │ Same data copy   │            │
│  │ Replicated log   │          │ Replicated log   │            │
│  │ Can be primary   │          │ Can be primary   │            │
│  └──────────────────┘          └──────────────────┘            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Data Write Flow

```
Client                  Primary                 Secondaries
  │                       │                         │
  │  SET key value       │                         │
  ├──────────────────→   │                         │
  │                       │ Store locally          │
  │                       ├─────→ (in memory)      │
  │                       │ Add to replication log │
  │                       ├─────→                  │
  │  OK                   │                         │
  │  ←──────────────────┤                         │
  │                       │ Async: Send REPLICATE  │
  │                       │                  command│
  │                       ├─────────────────────→  │
  │                       │                    │   │
  │                       │                    │ Apply operation
  │                       │                    │ ├─────→
  │                       │                    │   │
  │                       │                    │ Acknowledge
  │                       │                  ←────┤
  │                       │                         │
```

## Read Flow

```
Client              Primary                Secondary (Block)
  │                   │                          │
  │  GET key          │                          │
  ├──────────────→    │                          │
  │                   │ Lookup in store          │
  │                   ├──────→                   │
  │  value            │                          │
  │  ←──────────────┤                          │
  │                   │                          │
  │                   │                          │
  │  GET key (ERROR)  │                          │
  ├─────────────────────────────────────────────→
  │                   │                    (Error)
  │  ERROR: "Not      │                   ←─────┤
  │  primary"         │                         │
  │  ←──────────────────────────────────────────┤
```

## Leader Election Flow

### Normal Operation
```
PRIMARY                    SECONDARY 1            SECONDARY 2
   │                           │                      │
   │ HEARTBEAT              │                      │
   ├──────────────────────→ │                      │
   │                        │ (Updated: alive)    │
   │ HEARTBEAT              │                      │
   ├─────────────────────────────────────────────→ │
   │                        │                  (Updated: alive)
   │ ... repeat every 2s    │                      │
   │                        │                      │
```

### Primary Failure Detection
```
PRIMARY                    SECONDARY 1            SECONDARY 2
(CRASHED)                      │                      │
   ✗                           │                      │
                               │ Wait for heartbeat  │
                               │ Timeout 5-8 seconds │
                               │ No heartbeat!       │
                               │ Start ELECTION      │
                               │                     │
                               │ REQUEST_VOTE        │
                               ├────────────────────→│
                               │                     │
                               │                  VOTE GRANTED
                               │                   ←─────────┤
                               │ I WIN! (2 votes)   │
                               │ Become PRIMARY      │
                               │ Start HEARTBEAT     │
                               │                     │
                               │ HEARTBEAT           │
                               ├────────────────────→│
                               │                     │
```

### Election Process
```
SECONDARY 1                    SECONDARY 2
   │ Detect no heartbeat           │
   │ for 5-8 seconds               │
   │ Start election                │
   │ Term = 1                       │
   ├──────────────────────────────→│
   │ REQUEST_VOTE (term=1)         │
   │                               │
   │                          Check term
   │                          term 1 > 0?
   │                          Yes! Vote!
   │                          VOTE_GRANTED
   │                        ←─────────┤
   │ Got 2 votes (mine + n2)      │
   │ BECOME PRIMARY                │
   │ Start accepting reads/writes  │
   │ Send HEARTBEAT                │
   │                               │
```

## Failover Timeline

```
Time (seconds)    Event
─────────────────────────────────────────────────────────────
T=0               PRIMARY CRASHES ✗
                  
T=0-5             Secondaries haven't noticed yet
                  Still sending heartbeat requests
                  No response from primary
                  
T=5               SECONDARY 1 detects missing heartbeat
                  (Election timeout reached)
                  Increments term: 0 → 1
                  Starts election
                  
T=5-6             SECONDARY 1 sends election requests to all nodes
                  SECONDARY 2 receives request
                  SECONDARY 2 votes for SECONDARY 1
                  
T=6               SECONDARY 1 receives votes
                  Has 2 votes (itself + SECONDARY 2)
                  Meets quorum requirement (2 out of 3)
                  
T=6               SECONDARY 1 becomes PRIMARY
                  Starts accepting reads and writes
                  Sends heartbeat to SECONDARY 2
                  
T=6-8             System operational with new primary
                  Clients reconnect and continue
                  
T>8               If original primary recovers:
                  Sees higher term
                  Becomes secondary
                  Syncs data with new primary
```

## Data Consistency Model

```
                    Time →
PRIMARY:            T1: SET user:1
┌────────────────────┬─────────────────────────┐
│ Committed          │ Available for read      │
└────────────────────┴─────────────────────────┘

SECONDARY 1:        
                    T1+δ: Apply replication
┌─────────────────────────────────┬──────────────┐
│ Not yet have data               │ Now available │
└─────────────────────────────────┴──────────────┘

SECONDARY 2:        
                    T1+δ': Apply replication
┌──────────────────────────────────────┬────────┐
│ Not yet have data                    │ Now    │
└──────────────────────────────────────┴────────┘
                                       δ' > δ

Legend:
┌───────┐ = Data available
│ ✓     │
└───────┘
δ = replication lag to secondary 1 (~1-5ms)
δ'= replication lag to secondary 2 (~1-5ms)

Model: Eventually Consistent
- Primary: Strong consistency
- Secondaries: Eventual consistency (ms to seconds lag)
```

## Replication Log Structure

```
ReplicationLog Entry:
┌─────────────────────────────────┐
│ timestamp: 1234567890.123       │
│ operation: "SET"                │
│ key: "user:1"                   │
│ value: {                         │
│   "name": "Alice",              │
│   "age": 30                      │
│ }                               │
└─────────────────────────────────┘

Another Entry:
┌─────────────────────────────────┐
│ timestamp: 1234567891.001       │
│ operation: "DELETE"             │
│ key: "session:100"              │
│ value: null                      │
└─────────────────────────────────┘

Replicated to Secondaries:
┌─────────────────────────────────┐
│ [                               │
│   {op, key, value, timestamp},  │
│   {op, key, value, timestamp},  │
│   {op, key, value, timestamp},  │
│   ...                           │
│ ]                               │
└─────────────────────────────────┘
```

## Cluster State Diagram

```
                    ┌─────────────────┐
                    │   STARTING      │
                    │   (Init cluster)│
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │   NORMAL        │
                    │  - Primary      │
          ┌────────→│    accepts R/W  │←─────────┐
          │         │  - Secondary    │          │
          │         │    replicates   │          │
          │         └────────┬────────┘          │
          │                  │                   │
          │                  │ Primary failure   │
          │                  │ detected          │
          │                  ▼                   │
          │         ┌─────────────────┐          │
          │         │   ELECTION      │          │
          │         │  - Vote requests│          │
          │         │  - Voting       │          │
          │         └────────┬────────┘          │
          │                  │                   │
          │          ┌───────┴─────────┐         │
          │          │                 │         │
          │    ┌─────▼──────┐   ┌─────▼──────┐  │
          │    │ ELECTED    │   │  NOT       │  │
          │    │ Become     │   │ ELECTED    │  │
          │    │ PRIMARY    │   │ Stay       │  │
          │    │ (Resume    │   │ SECONDARY  │  │
          │    │  normal)   │   │ (Election  │  │
          │    └─────┬──────┘   │  retry)    │  │
          │          │          └─────┬──────┘  │
          └──────────┼──────────────────┘        │
                     │                          │
                     │ Recovery/Sync            │
                     ▼                          │
                ┌─────────────────┐             │
                │  SYNCING        │─────────────┘
                │  Secondaries    │
                │  catch up       │
                └─────────────────┘
```

## Message Exchange Protocol

### Normal Operation
```
CLIENT ─→ PRIMARY
  "SET mykey myvalue"
    │
    └─→ PRIMARY
        ├─ Store data
        ├─ Log operation
        └─ Return OK
  ←─ "OK"

CLIENT ─→ PRIMARY
  "GET mykey"
    │
    └─→ PRIMARY
        └─ Return value
  ←─ "OK", value

PRIMARY ─→ SECONDARY (async)
  {type: REPLICATE, operation: SET, key, value}
    │
    └─→ SECONDARY
        ├─ Apply operation
        └─ Store locally

PRIMARY ─→ SECONDARY (periodic)
  {type: HEARTBEAT, from_node: node1}
    │
    └─→ SECONDARY
        ├─ Update last_heartbeat
        └─ Reply OK
```

### Election Phase
```
SECONDARY ─→ ALL NODES
  {type: ELECTION, candidate_id, term}
    │
    ├─→ NODE 2
    │   └─ Check: haven't voted in this term?
    │   └─ Grant vote
    │   └─ Return OK
    │
    └─→ NODE 3
        └─ Check: haven't voted in this term?
        └─ Grant vote
        └─ Return OK

SECONDARY (now PRIMARY) ─→ SECONDARIES
  {type: HEARTBEAT, from_node: node1}
    │
    ├─→ NODE 2
    └─→ NODE 3
```

## Performance Characteristics

```
Operation Latency:

SET command:
├─ Network → 1ms
├─ Store locally → <1ms
├─ Log operation → <1ms
├─ Reply to client → 1ms
└─ Async replicate → 1-10ms (parallel, not blocking)
Total: ~2ms (to client), then 5-10ms for full replication

GET command:
├─ Network → 1ms
├─ Lookup → <1ms
├─ Reply → 1ms
└─ Total: ~2ms

Failover:
├─ Detection → 5-8s (election timeout)
├─ Election process → 0.5-2s
└─ Total: 5-10 seconds

Heartbeat overhead:
├─ Sent every 2 seconds
├─ Size: ~50 bytes
├─ Network: ~1ms round trip
└─ CPU: negligible
```

---

This visual guide helps understand:
- System architecture and components
- Data flow during reads and writes
- Leader election and failover process
- Consistency model and replication
- Message protocols and timing
- Performance characteristics
