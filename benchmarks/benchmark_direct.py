#!/usr/bin/env python3
"""
Direct benchmark of KeyValueStore without HTTP overhead
Tests the raw database performance
"""

import sys
import os
import time
import statistics
import json
from typing import Tuple

# Add parent directory to path to import kv_store_server
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kv_store_server import KeyValueStore


def measure_writes(store: KeyValueStore, num_writes: int) -> Tuple[float, float, float, float]:
    """
    Measure write performance
    
    Args:
        store: KeyValueStore instance
        num_writes: Number of write operations to perform
    
    Returns:
        Tuple of (writes_per_second, min_time, max_time, avg_time)
    """
    write_times = []
    print(f"  Measuring {num_writes} write operations...", end="", flush=True)
    
    for i in range(num_writes):
        start = time.perf_counter()
        store.set(f'bench_key_{i}', f'benchmark_value_{i}')
        end = time.perf_counter()
        write_times.append((end - start) * 1000)  # Convert to ms
    
    print(" Done")
    
    # Calculate statistics
    total_time = sum(write_times) / 1000  # Convert back to seconds
    writes_per_second = num_writes / total_time
    min_time = min(write_times)
    max_time = max(write_times)
    avg_time = statistics.mean(write_times)
    
    return writes_per_second, min_time, max_time, avg_time


def run_benchmark():
    """Run the complete benchmark suite"""
    
    print("\n" + "="*70)
    print("Direct KeyValueStore Performance Benchmark (No HTTP)")
    print("="*70)
    
    # Test with increasing store sizes
    test_cases = [
        (0, 500),      # 0 existing keys, 500 writes
        (100, 500),    # 100 existing keys, 500 writes
        (1000, 500),   # 1000 existing keys, 500 writes
        (5000, 500),   # 5000 existing keys, 500 writes
        (10000, 500),  # 10000 existing keys, 500 writes
    ]
    
    results = []
    
    for existing_keys, num_writes in test_cases:
        print(f"\nBenchmark: {existing_keys} existing keys")
        
        # Create fresh store for each test
        store = KeyValueStore()
        
        # Pre-populate the store with existing keys
        if existing_keys > 0:
            print(f"  Pre-populating store with {existing_keys} keys...", end="", flush=True)
            for i in range(existing_keys):
                store.set(f'existing_key_{i}', f'value_{i}')
            print(" Done")
        
        # Measure write performance
        try:
            writes_per_sec, min_time, max_time, avg_time = measure_writes(store, num_writes)
            results.append({
                "existing_keys": existing_keys,
                "writes_per_second": writes_per_sec,
                "min_time_ms": min_time,
                "max_time_ms": max_time,
                "avg_time_ms": avg_time
            })
            print(f"  Writes/sec: {writes_per_sec:.2f}")
            print(f"  Avg time: {avg_time:.2f}ms")
            print(f"  Min time: {min_time:.2f}ms, Max time: {max_time:.2f}ms")
        except Exception as e:
            print(f"  Error: {e}")
            return
    
    # Print summary
    print("\n" + "="*70)
    print("Summary - Direct Performance (No HTTP Overhead)")
    print("="*70)
    print(f"{'Existing Keys':<20} {'Writes/sec':<20} {'Avg Time (ms)':<20}")
    print("-"*70)
    for result in results:
        print(f"{result['existing_keys']:<20} {result['writes_per_second']:<20.2f} {result['avg_time_ms']:<20.4f}")
    
    # Save results to file
    with open("benchmark_direct_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to benchmark_direct_results.json")
    
    # Performance degradation analysis
    if len(results) > 1:
        print("\n" + "="*70)
        print("Performance Degradation Analysis")
        print("="*70)
        baseline = results[0]["writes_per_second"]
        for result in results[1:]:
            degradation = ((baseline - result["writes_per_second"]) / baseline) * 100
            print(f"With {result['existing_keys']:>5} keys: {degradation:>6.2f}% slower than baseline")


if __name__ == "__main__":
    run_benchmark()
