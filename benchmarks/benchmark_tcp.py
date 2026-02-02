#!/usr/bin/env python3
"""
TCP Client benchmark for key-value store
Tests write performance via TCP instead of HTTP
"""

import socket
import json
import time
import statistics
from typing import Tuple

HOST = "localhost"
PORT = 6379


def send_command(sock: socket.socket, command: str) -> str:
    """Send a command and receive response"""
    sock.send(command.encode('utf-8') + b'\n')
    response = sock.recv(4096).decode('utf-8').strip()
    return response


def measure_writes(num_writes: int) -> Tuple[float, float, float, float]:
    """Measure write performance via TCP"""
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((HOST, PORT))
    
    write_times = []
    print(f"  Measuring {num_writes} write operations via TCP...", end="", flush=True)
    
    for i in range(num_writes):
        start = time.perf_counter()
        command = f'SET bench_key_{i} "{{"value": "{i}"}}"'
        response = send_command(sock, command)
        end = time.perf_counter()
        write_times.append((end - start) * 1000)  # Convert to ms
    
    sock.close()
    print(" Done")
    
    # Calculate statistics
    total_time = sum(write_times) / 1000
    writes_per_second = num_writes / total_time
    min_time = min(write_times)
    max_time = max(write_times)
    avg_time = statistics.mean(write_times)
    
    return writes_per_second, min_time, max_time, avg_time


def run_benchmark():
    """Run benchmark"""
    
    print("\n" + "="*70)
    print("TCP Client Performance Benchmark")
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
    
    # Pre-populate if needed
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((HOST, PORT))
    
    for existing_keys, num_writes in test_cases:
        print(f"\nBenchmark: {existing_keys} existing keys")
        
        # Pre-populate the store with existing keys
        if existing_keys > 0:
            print(f"  Pre-populating store with {existing_keys} keys...", end="", flush=True)
            for i in range(existing_keys):
                command = f'SET existing_key_{i} "value_{i}"'
                send_command(sock, command)
            print(" Done")
        
        # Measure write performance
        try:
            writes_per_sec, min_time, max_time, avg_time = measure_writes(num_writes)
            results.append({
                "existing_keys": existing_keys,
                "writes_per_second": writes_per_sec,
                "min_time_ms": min_time,
                "max_time_ms": max_time,
                "avg_time_ms": avg_time
            })
            print(f"  Writes/sec: {writes_per_sec:.2f}")
            print(f"  Avg time: {avg_time:.4f}ms")
            print(f"  Min time: {min_time:.4f}ms, Max time: {max_time:.4f}ms")
        except Exception as e:
            print(f"  Error: {e}")
            return
    
    sock.close()
    
    # Print summary
    print("\n" + "="*70)
    print("Summary - TCP Performance")
    print("="*70)
    print(f"{'Existing Keys':<20} {'Writes/sec':<20} {'Avg Time (ms)':<20}")
    print("-"*70)
    for result in results:
        print(f"{result['existing_keys']:<20} {result['writes_per_second']:<20.2f} {result['avg_time_ms']:<20.4f}")
    
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
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((HOST, PORT))
        sock.close()
    except ConnectionRefusedError:
        print(f"Error: Cannot connect to server at {HOST}:{PORT}")
        print("Please start the server first: python kv_store_server.py")
        sys.exit(1)
    
    run_benchmark()
