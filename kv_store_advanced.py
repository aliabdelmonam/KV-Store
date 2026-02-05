#!/usr/bin/env python3
"""
Advanced Key-Value Store with:
1. Value Indexing
2. Full-Text Search (Inverted Index)
3. Word Embeddings (Semantic Search)
4. Masterless Replication (Multi-master)
"""

from typing import Any, Optional, List, Dict, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import json
import threading
import time
import socket
import signal
import sys
import argparse
import random
import re
import math
import hashlib
import shlex


# ============================================================================
# INDEXING SYSTEM
# ============================================================================

class Index:
    """Secondary index on values"""
    
    def __init__(self, field_path: str):
        """
        field_path: dot-notation path to index (e.g., 'user.age', 'tags', 'price')
        """
        self.field_path = field_path
        self.index: Dict[Any, Set[str]] = defaultdict(set)  # value -> set of keys
        self.lock = threading.Lock()
    
    def _extract_value(self, obj: Any, path: str) -> List[Any]:
        """Extract value from nested object using dot notation"""
        parts = path.split('.')
        values = [obj]
        
        for part in parts:
            new_values = []
            for val in values:
                if isinstance(val, dict) and part in val:
                    new_values.append(val[part])
                elif isinstance(val, list):
                    for item in val:
                        if isinstance(item, dict) and part in item:
                            new_values.append(item[part])
            values = new_values
        
        return values
    
    def add(self, key: str, value: Any):
        """Add key to index based on its value"""
        with self.lock:
            indexed_values = self._extract_value(value, self.field_path)
            for indexed_val in indexed_values:
                if indexed_val is not None:
                    # Handle lists by indexing each element
                    if isinstance(indexed_val, list):
                        for item in indexed_val:
                            self.index[item].add(key)
                    else:
                        self.index[indexed_val].add(key)
    
    def remove(self, key: str, value: Any):
        """Remove key from index"""
        with self.lock:
            indexed_values = self._extract_value(value, self.field_path)
            for indexed_val in indexed_values:
                if indexed_val is not None:
                    if isinstance(indexed_val, list):
                        for item in indexed_val:
                            self.index[item].discard(key)
                    else:
                        self.index[indexed_val].discard(key)
    
    def search(self, value: Any) -> Set[str]:
        """Find all keys with given indexed value"""
        with self.lock:
            return self.index.get(value, set()).copy()
    
    def range_search(self, min_val: Any, max_val: Any) -> Set[str]:
        """Find all keys with indexed value in range [min_val, max_val]"""
        with self.lock:
            results = set()
            for val, keys in self.index.items():
                if isinstance(val, (int, float)) and min_val <= val <= max_val:
                    results.update(keys)
            return results


# ============================================================================
# INVERTED INDEX (FULL-TEXT SEARCH)
# ============================================================================

class InvertedIndex:
    """Full-text search using inverted index"""
    
    def __init__(self):
        self.index: Dict[str, Set[str]] = defaultdict(set)  # word -> set of keys
        self.doc_words: Dict[str, Set[str]] = {}  # key -> set of words
        self.lock = threading.Lock()
        
        # Stop words (common words to ignore)
        self.stop_words = {
            'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from',
            'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the',
            'to', 'was', 'will', 'with'
        }
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into words"""
        # Convert to lowercase and split on non-alphanumeric
        words = re.findall(r'\w+', text.lower())
        # Remove stop words and short words
        return [w for w in words if w not in self.stop_words and len(w) > 2]
    
    def _extract_text(self, obj: Any) -> str:
        """Extract all text from an object recursively"""
        if isinstance(obj, str):
            return obj
        elif isinstance(obj, dict):
            return ' '.join(self._extract_text(v) for v in obj.values())
        elif isinstance(obj, list):
            return ' '.join(self._extract_text(item) for item in obj)
        else:
            return str(obj)
    
    def add(self, key: str, value: Any):
        """Index a document"""
        with self.lock:
            # Extract all text from value
            text = self._extract_text(value)
            words = set(self._tokenize(text))
            
            # Update inverted index
            for word in words:
                self.index[word].add(key)
            
            # Store words for this document
            self.doc_words[key] = words
    
    def remove(self, key: str):
        """Remove document from index"""
        with self.lock:
            if key in self.doc_words:
                words = self.doc_words[key]
                for word in words:
                    self.index[word].discard(key)
                del self.doc_words[key]
    
    def search(self, query: str) -> Set[str]:
        """Search for documents containing query terms (OR)"""
        with self.lock:
            query_words = self._tokenize(query)
            if not query_words:
                return set()
            
            # Union of all documents containing any query word
            results = set()
            for word in query_words:
                results.update(self.index.get(word, set()))
            return results
    
    def search_and(self, query: str) -> Set[str]:
        """Search for documents containing ALL query terms (AND)"""
        with self.lock:
            query_words = self._tokenize(query)
            if not query_words:
                return set()
            
            # Intersection of documents containing all query words
            results = self.index.get(query_words[0], set()).copy()
            for word in query_words[1:]:
                results.intersection_update(self.index.get(word, set()))
            return results
    
    def search_phrase(self, phrase: str) -> Set[str]:
        """Search for exact phrase (simplified - just checks all words present)"""
        return self.search_and(phrase)


# ============================================================================
# WORD EMBEDDINGS (SEMANTIC SEARCH)
# ============================================================================

class SimpleEmbedding:
    """Simple word embeddings using character n-grams and TF-IDF"""
    
    def __init__(self, dimensions: int = 50):
        self.dimensions = dimensions
        self.embeddings: Dict[str, List[float]] = {}
        self.doc_vectors: Dict[str, List[float]] = {}
        self.lock = threading.Lock()
    
    def _char_ngrams(self, word: str, n: int = 3) -> Set[str]:
        """Generate character n-grams"""
        word = f"#{word}#"  # Add boundaries
        return {word[i:i+n] for i in range(len(word) - n + 1)}
    
    def _hash_to_dim(self, ngram: str) -> int:
        """Hash n-gram to dimension"""
        return int(hashlib.md5(ngram.encode()).hexdigest(), 16) % self.dimensions
    
    def _compute_embedding(self, word: str) -> List[float]:
        """Compute embedding for a word using character n-grams"""
        embedding = [0.0] * self.dimensions
        ngrams = self._char_ngrams(word.lower())
        
        for ngram in ngrams:
            dim = self._hash_to_dim(ngram)
            embedding[dim] += 1.0
        
        # Normalize
        magnitude = math.sqrt(sum(x*x for x in embedding))
        if magnitude > 0:
            embedding = [x / magnitude for x in embedding]
        
        return embedding
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Compute cosine similarity between two vectors"""
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        return dot_product
    
    def add(self, key: str, value: Any):
        """Create embedding for document"""
        with self.lock:
            # Extract text and tokenize
            text = self._extract_text(value)
            words = re.findall(r'\w+', text.lower())
            
            # Average word embeddings to get document embedding
            if words:
                doc_embedding = [0.0] * self.dimensions
                for word in words:
                    if word not in self.embeddings:
                        self.embeddings[word] = self._compute_embedding(word)
                    word_emb = self.embeddings[word]
                    doc_embedding = [a + b for a, b in zip(doc_embedding, word_emb)]
                
                # Average and normalize
                doc_embedding = [x / len(words) for x in doc_embedding]
                magnitude = math.sqrt(sum(x*x for x in doc_embedding))
                if magnitude > 0:
                    doc_embedding = [x / magnitude for x in doc_embedding]
                
                self.doc_vectors[key] = doc_embedding
    
    def remove(self, key: str):
        """Remove document embedding"""
        with self.lock:
            if key in self.doc_vectors:
                del self.doc_vectors[key]
    
    def _extract_text(self, obj: Any) -> str:
        """Extract text from object"""
        if isinstance(obj, str):
            return obj
        elif isinstance(obj, dict):
            return ' '.join(self._extract_text(v) for v in obj.values())
        elif isinstance(obj, list):
            return ' '.join(self._extract_text(item) for item in obj)
        else:
            return str(obj)
    
    def search(self, query: str, top_k: int = 10) -> List[Tuple[str, float]]:
        """Semantic search - find most similar documents"""
        with self.lock:
            # Compute query embedding
            words = re.findall(r'\w+', query.lower())
            if not words:
                return []
            
            query_emb = [0.0] * self.dimensions
            for word in words:
                if word not in self.embeddings:
                    self.embeddings[word] = self._compute_embedding(word)
                word_emb = self.embeddings[word]
                query_emb = [a + b for a, b in zip(query_emb, word_emb)]
            
            # Normalize
            query_emb = [x / len(words) for x in query_emb]
            magnitude = math.sqrt(sum(x*x for x in query_emb))
            if magnitude > 0:
                query_emb = [x / magnitude for x in query_emb]
            
            # Compute similarities
            similarities = []
            for key, doc_vec in self.doc_vectors.items():
                similarity = self._cosine_similarity(query_emb, doc_vec)
                similarities.append((key, similarity))
            
            # Sort by similarity and return top-k
            similarities.sort(key=lambda x: x[1], reverse=True)
            return similarities[:top_k]


# ============================================================================
# VECTOR CLOCK (for masterless replication)
# ============================================================================

@dataclass
class VectorClock:
    """Vector clock for conflict detection"""
    clocks: Dict[str, int] = field(default_factory=dict)
    
    def increment(self, node_id: str):
        """Increment clock for this node"""
        self.clocks[node_id] = self.clocks.get(node_id, 0) + 1
    
    def update(self, other: 'VectorClock'):
        """Update with another vector clock (merge)"""
        for node_id, timestamp in other.clocks.items():
            self.clocks[node_id] = max(self.clocks.get(node_id, 0), timestamp)
    
    def compare(self, other: 'VectorClock') -> str:
        """
        Compare with another vector clock
        Returns: 'before', 'after', 'concurrent', 'equal'
        """
        before = False
        after = False
        
        all_nodes = set(self.clocks.keys()) | set(other.clocks.keys())
        
        for node in all_nodes:
            self_val = self.clocks.get(node, 0)
            other_val = other.clocks.get(node, 0)
            
            if self_val < other_val:
                before = True
            elif self_val > other_val:
                after = True
        
        if not before and not after:
            return 'equal'
        elif before and not after:
            return 'before'
        elif after and not before:
            return 'after'
        else:
            return 'concurrent'
    
    def to_dict(self) -> dict:
        return {'clocks': self.clocks}
    
    @staticmethod
    def from_dict(data: dict) -> 'VectorClock':
        return VectorClock(clocks=data.get('clocks', {}))


# ============================================================================
# VERSIONED VALUE (for multi-version storage)
# ============================================================================

@dataclass
class VersionedValue:
    """Value with vector clock version"""
    value: Any
    vector_clock: VectorClock
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> dict:
        return {
            'value': self.value,
            'vector_clock': self.vector_clock.to_dict(),
            'timestamp': self.timestamp
        }
    
    @staticmethod
    def from_dict(data: dict) -> 'VersionedValue':
        return VersionedValue(
            value=data['value'],
            vector_clock=VectorClock.from_dict(data['vector_clock']),
            timestamp=data.get('timestamp', time.time())
        )


# ============================================================================
# ADVANCED KEY-VALUE STORE
# ============================================================================

class AdvancedKeyValueStore:
    """KV Store with indexing, full-text search, embeddings, and versioning"""
    
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.store: Dict[str, List[VersionedValue]] = {}  # key -> list of versions
        self.lock = threading.Lock()
        
        # Indexes
        self.indexes: Dict[str, Index] = {}
        self.inverted_index = InvertedIndex()
        self.embedding_index = SimpleEmbedding(dimensions=50)
        
        # Replication log
        self.replication_log: List[dict] = []
    
    def create_index(self, name: str, field_path: str):
        """Create a secondary index"""
        with self.lock:
            if name not in self.indexes:
                self.indexes[name] = Index(field_path)
                # Index existing data
                for key, versions in self.store.items():
                    if versions:
                        latest = versions[-1]
                        self.indexes[name].add(key, latest.value)
    
    def set(self, key: str, value: Any, vector_clock: Optional[VectorClock] = None) -> dict:
        """Set a key-value pair with vector clock"""
        with self.lock:
            # Create or update vector clock
            if vector_clock is None:
                vector_clock = VectorClock()
            vector_clock.increment(self.node_id)
            
            # Create versioned value
            versioned = VersionedValue(value=value, vector_clock=vector_clock)
            
            # Handle conflicts
            if key in self.store:
                existing_versions = self.store[key]
                new_versions = []
                
                for existing in existing_versions:
                    comparison = vector_clock.compare(existing.vector_clock)
                    
                    if comparison == 'after':
                        # New version supersedes existing
                        # Remove from indexes
                        for idx in self.indexes.values():
                            idx.remove(key, existing.value)
                        self.inverted_index.remove(key)
                        self.embedding_index.remove(key)
                        continue
                    elif comparison == 'before':
                        # Existing version supersedes new - keep existing
                        return {"status": "OK", "message": "Outdated version ignored"}
                    elif comparison == 'concurrent':
                        # Concurrent versions - keep both
                        new_versions.append(existing)
                
                new_versions.append(versioned)
                self.store[key] = new_versions
            else:
                self.store[key] = [versioned]
            
            # Update indexes (only for latest version)
            for idx in self.indexes.values():
                idx.add(key, value)
            self.inverted_index.add(key, value)
            self.embedding_index.add(key, value)
            
            # Add to replication log
            self.replication_log.append({
                'operation': 'SET',
                'key': key,
                'value': value,
                'vector_clock': vector_clock.to_dict(),
                'timestamp': time.time()
            })
            
            return {"status": "OK", "versions": len(self.store[key])}
    
    def get(self, key: str) -> Optional[List[VersionedValue]]:
        """Get all versions of a key"""
        with self.lock:
            return self.store.get(key, [])
    
    def get_latest(self, key: str) -> Optional[Any]:
        """Get latest version (last write wins)"""
        versions = self.get(key)
        if versions:
            # Return most recent by timestamp
            return max(versions, key=lambda v: v.timestamp).value
        return None
    
    def delete(self, key: str) -> dict:
        """Delete a key"""
        with self.lock:
            if key in self.store:
                versions = self.store[key]
                
                # Remove from indexes
                for version in versions:
                    for idx in self.indexes.values():
                        idx.remove(key, version.value)
                self.inverted_index.remove(key)
                self.embedding_index.remove(key)
                
                del self.store[key]
                
                # Add to replication log
                self.replication_log.append({
                    'operation': 'DELETE',
                    'key': key,
                    'timestamp': time.time()
                })
                
                return {"status": "OK"}
            else:
                return {"status": "ERROR", "message": "Key not found"}
    
    def index_search(self, index_name: str, value: Any) -> Set[str]:
        """Search using a secondary index"""
        if index_name in self.indexes:
            return self.indexes[index_name].search(value)
        return set()
    
    def index_range_search(self, index_name: str, min_val: Any, max_val: Any) -> Set[str]:
        """Range search using a secondary index"""
        if index_name in self.indexes:
            return self.indexes[index_name].range_search(min_val, max_val)
        return set()
    
    def fulltext_search(self, query: str, mode: str = 'or') -> Set[str]:
        """Full-text search"""
        if mode == 'or':
            return self.inverted_index.search(query)
        elif mode == 'and':
            return self.inverted_index.search_and(query)
        elif mode == 'phrase':
            return self.inverted_index.search_phrase(query)
        return set()
    
    def semantic_search(self, query: str, top_k: int = 10) -> List[Tuple[str, float]]:
        """Semantic search using embeddings"""
        return self.embedding_index.search(query, top_k)
    
    def merge_replication_log(self, log_entries: List[dict]):
        """Merge replication log from another node"""
        for entry in log_entries:
            op = entry['operation']
            key = entry['key']
            
            if op == 'SET':
                value = entry['value']
                vc = VectorClock.from_dict(entry['vector_clock'])
                self.set(key, value, vc)
            elif op == 'DELETE':
                self.delete(key)


# ============================================================================
# TCP SERVER (Masterless)
# ============================================================================

class MasterlessTCPServer:
    """TCP server for masterless replication"""
    
    def __init__(self, kv_store: AdvancedKeyValueStore, node_id: str, 
                 host: str = '0.0.0.0', port: int = 6379):
        self.kv_store = kv_store
        self.node_id = node_id
        self.host = host
        self.port = port
        self.socket = None
        self.running = True
        
        # Peer nodes
        self.peers = []
        self.all_nodes = [
            {"node_id": "node1", "host": "127.0.0.1", "port": 6379},
            {"node_id": "node2", "host": "127.0.0.1", "port": 6380},
            {"node_id": "node3", "host": "127.0.0.1", "port": 6381},
        ]
    
    def start(self):
        """Start the TCP server"""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((self.host, self.port))
        self.socket.listen(5)
        print(f"[{self.node_id}] Masterless server on {self.host}:{self.port}")
        
        # Setup peers
        self.peers = [n for n in self.all_nodes if n['node_id'] != self.node_id]
        
        try:
            while self.running:
                try:
                    self.socket.settimeout(1.0)
                    client_socket, addr = self.socket.accept()
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, addr),
                        daemon=True
                    )
                    client_thread.start()
                except socket.timeout:
                    continue
        except KeyboardInterrupt:
            self.stop()
    
    def stop(self):
        """Stop the server"""
        self.running = False
        if self.socket:
            self.socket.close()
        print(f"[{self.node_id}] Server stopped")
    
    def handle_client(self, client_socket: socket.socket, addr):
        """Handle client connection"""
        try:
            while self.running:
                data = client_socket.recv(16384)
                if not data:
                    break
                
                command_str = data.decode('utf-8').strip()
                response = self.process_command(command_str)
                client_socket.send(response.encode('utf-8') + b'\n')
        except Exception:
            pass
        finally:
            client_socket.close()
    
    def process_command(self, command_str: str) -> str:
        """Process command"""
        try:
            # Try JSON (internal commands)
            try:
                command = json.loads(command_str)
                if isinstance(command, dict) and "type" in command:
                    return self._handle_internal_command(command)
            except json.JSONDecodeError:
                pass
            
            # Parse regular command using shlex to handle quoted arguments
            try:
                parts = shlex.split(command_str)
            except ValueError:
                return json.dumps({"status": "ERROR", "message": "Invalid command format (mismatched quotes?)"})

            if not parts:
                return json.dumps({"status": "ERROR", "message": "Empty command"})
            
            cmd = parts[0].upper()
            
            if cmd == "SET" and len(parts) == 3:
                key, value_str = parts[1], parts[2]
                try:
                    value = json.loads(value_str)
                except:
                    # In case it's not JSON, store as string (or error out)
                    # For compatibility with demo, let's assume valid JSON or string
                    value = value_str
                
                result = self.kv_store.set(key, value)
                
                # Replicate to peers
                self.replicate_to_peers("SET", key, value)
                
                return json.dumps(result)
            
            elif cmd == "GET" and len(parts) == 2:
                key = parts[1]
                value = self.kv_store.get_latest(key)
                if value is None:
                    return json.dumps({"status": "ERROR", "message": f"Key '{key}' not found"})
                return json.dumps({"status": "OK", "value": value})
            
            elif cmd == "DELETE" and len(parts) == 2:
                key = parts[1]
                result = self.kv_store.delete(key)
                
                if result["status"] == "OK":
                    self.replicate_to_peers("DELETE", key, None)
                
                return json.dumps(result)
            
            elif cmd == "CREATE_INDEX" and len(parts) == 3:
                # CREATE_INDEX name field_path
                index_name = parts[1]
                field_path = parts[2]
                self.kv_store.create_index(index_name, field_path)
                return json.dumps({"status": "OK", "message": f"Index '{index_name}' created"})
            
            elif cmd == "SEARCH" and len(parts) == 3:
                # SEARCH index_name value
                index_name = parts[1]
                value_str = parts[2]
                try:
                    value = json.loads(value_str)
                except:
                    value = value_str
                
                results = list(self.kv_store.index_search(index_name, value))
                return json.dumps({"status": "OK", "keys": results})
            
            elif cmd == "RANGE_SEARCH" and len(parts) == 4:
                # RANGE_SEARCH index_name min_value max_value
                index_name = parts[1]
                min_str = parts[2]
                max_str = parts[3]
                try:
                    min_val = json.loads(min_str)
                    max_val = json.loads(max_str)
                except:
                    min_val = min_str
                    max_val = max_str
                
                results = list(self.kv_store.index_range_search(index_name, min_val, max_val))
                return json.dumps({"status": "OK", "keys": results})
            
            elif cmd == "FULLTEXT" and len(parts) >= 2:
                # FULLTEXT query [mode]
                query = parts[1]
                mode = parts[2] if len(parts) >= 3 else 'or'
                
                results = list(self.kv_store.fulltext_search(query, mode))
                return json.dumps({"status": "OK", "keys": results})
            
            elif cmd == "SEMANTIC" and len(parts) >= 2:
                # SEMANTIC query [top_k]
                query = parts[1]
                top_k = int(parts[2]) if len(parts) >= 3 else 10
                
                results = self.kv_store.semantic_search(query, top_k)
                # Convert to serializable format
                results = [{"key": k, "score": s} for k, s in results]
                return json.dumps({"status": "OK", "results": results})
            
            elif cmd == "STATUS":
                return json.dumps({
                    "status": "OK",
                    "node_id": self.node_id,
                    "mode": "masterless",
                    "peers": len(self.peers)
                })
            
            elif cmd == "PING":
                return json.dumps({"status": "OK", "message": "PONG"})
            
            elif cmd == "SHUTDOWN":
                self.stop()
                return json.dumps({"status": "OK", "message": "Shutting down"})
            
            else:
                return json.dumps({"status": "ERROR", "message": f"Unknown command: {cmd}"})
        
        except Exception as e:
            return json.dumps({"status": "ERROR", "message": str(e)})
    
    def _handle_internal_command(self, command: dict) -> str:
        """Handle internal commands"""
        cmd_type = command.get("type")
        
        if cmd_type == "REPLICATE":
            op = command.get("operation")
            key = command.get("key")
            
            if op == "SET":
                value = command.get("value")
                vc_data = command.get("vector_clock")
                vc = VectorClock.from_dict(vc_data) if vc_data else None
                self.kv_store.set(key, value, vc)
            elif op == "DELETE":
                self.kv_store.delete(key)
            
            return json.dumps({"status": "OK"})
        
        elif cmd_type == "SYNC":
            # Anti-entropy: sync replication logs
            log_entries = command.get("log_entries", [])
            self.kv_store.merge_replication_log(log_entries)
            return json.dumps({"status": "OK"})
        
        return json.dumps({"status": "ERROR", "message": "Unknown internal command"})
    
    def replicate_to_peers(self, operation: str, key: str, value: Any):
        """Replicate to all peer nodes"""
        versions = self.kv_store.get(key)
        if not versions:
            return
        
        latest = versions[-1]
        
        replication_cmd = json.dumps({
            "type": "REPLICATE",
            "operation": operation,
            "key": key,
            "value": value,
            "vector_clock": latest.vector_clock.to_dict()
        })
        
        for peer in self.peers:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                sock.connect((peer['host'], peer['port']))
                sock.send(replication_cmd.encode() + b'\n')
                sock.recv(1024)
                sock.close()
            except Exception:
                pass  # Best effort


# ============================================================================
# ANTI-ENTROPY (Background sync)
# ============================================================================

class AntiEntropyManager:
    """Periodic anti-entropy for masterless replication"""
    
    def __init__(self, server: MasterlessTCPServer):
        self.server = server
        self.running = True
        self.sync_interval = 10  # seconds
    
    def start(self):
        """Start anti-entropy thread"""
        sync_thread = threading.Thread(target=self._sync_loop, daemon=True)
        sync_thread.start()
    
    def _sync_loop(self):
        """Periodically sync with peers"""
        while self.running and self.server.running:
            time.sleep(self.sync_interval)
            
            # Send our replication log to peers
            log_entries = self.server.kv_store.replication_log[-100:]  # Last 100 ops
            
            sync_cmd = json.dumps({
                "type": "SYNC",
                "log_entries": log_entries
            })
            
            for peer in self.server.peers:
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(2)
                    sock.connect((peer['host'], peer['port']))
                    sock.send(sync_cmd.encode() + b'\n')
                    sock.recv(1024)
                    sock.close()
                except Exception:
                    pass


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Advanced KV Store (Masterless)')
    parser.add_argument('--node-id', required=True, help='Node ID')
    parser.add_argument('--port', type=int, required=True, help='Port')
    
    args = parser.parse_args()
    
    # Create store and server
    kv_store = AdvancedKeyValueStore(node_id=args.node_id)
    server = MasterlessTCPServer(
        kv_store=kv_store,
        node_id=args.node_id,
        host='0.0.0.0',
        port=args.port
    )
    
    # Start anti-entropy
    anti_entropy = AntiEntropyManager(server)
    anti_entropy.start()
    
    # Graceful shutdown
    def signal_handler(signum, frame):
        server.stop()
        anti_entropy.running = False
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    server.start()


if __name__ == "__main__":
    main()
