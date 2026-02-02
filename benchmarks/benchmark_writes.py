#!/usr/bin/env python3
"""
Benchmark script for key-value store write performance
Tests write operations per second with varying store sizes
"""

import requests
import time
import statistics
from typing import List, Tuple
import json

BASE_URL = "http://localhost:8000"
NUM_ITERATIONS = 100  # Number of write operations per test


def measure_writes(num_existing_keys: int, num_writes: int) -> Tuple[float, float, float]:
    """
    Measure write performance
    
    Args:
        num_existing_keys: Number of keys already in store
        num_writes: Number of write operations to perform
    
    Returns:
        Tuple of (writes_per_second, min_time, max_time)
    """
    # Pre-populate the store with existing keys
    if num_existing_keys > 0:
        print(f"  Pre-populating store with {num_existing_keys} keys...", end="", flush=True)
        for i in range(num_existing_keys):
            requests.post(f"{BASE_URL}/set", json={
                "key": f"existing_key_{i}",
                "value": f"value_{i}"
            })
        print(" Done")
    
    # Measure write performance
    write_times = []
    print(f"  Measuring {num_writes} write operations...", end="", flush=True)
    
    for i in range(num_writes):
        start = time.perf_counter()
        response = requests.post(f"{BASE_URL}/set", json={
            "key": f"bench_key_{num_existing_keys}_{i}",
            "value": f"benchmark_value_{i}"
        })
        end = time.perf_counter()
        
        if response.status_code == 200:
            write_times.append((end - start) * 1000)  # Convert to ms
        else:
            print(f"\nError: {response.status_code}")
            return 0, 0, 0
    
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
    print("Key-Value Store Write Performance Benchmark")
    print("="*70)
    
    # Test with increasing store sizes
    test_cases = [
        (0, 100),      # 0 existing keys, 100 writes
        (100, 100),    # 100 existing keys, 100 writes
        (1000, 100),   # 1000 existing keys, 100 writes
        (5000, 100),   # 5000 existing keys, 100 writes
        (10000, 100),  # 10000 existing keys, 100 writes
    ]
    
    results = []
    
    for existing_keys, num_writes in test_cases:
        print(f"\nBenchmark: {existing_keys} existing keys")
        try:
            writes_per_sec, min_time, max_time, avg_time = measure_writes(existing_keys, num_writes)
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
    print("Summary")
    print("="*70)
    print(f"{'Existing Keys':<20} {'Writes/sec':<20} {'Avg Time (ms)':<20}")
    print("-"*70)
    for result in results:
        print(f"{result['existing_keys']:<20} {result['writes_per_second']:<20.2f} {result['avg_time_ms']:<20.2f}")
    
    # Save results to file
    with open("benchmark_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to benchmark_results.json")
    
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
    import sys
    
    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/")
        if response.status_code != 200:
            print("Error: Server is not responding correctly")
            sys.exit(1)
    except requests.exceptions.ConnectionError:
        print("Error: Cannot connect to server at " + BASE_URL)
        print("Please start the server first: python kv_store_server.py")
        sys.exit(1)
    
    run_benchmark()
