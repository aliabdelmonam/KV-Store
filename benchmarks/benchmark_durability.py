#!/usr/bin/env python3
"""
Durability Benchmark for key-value store
Tests data persistence by killing the server at random points
and checking how many successful writes were lost
"""

import socket
import json
import time
import subprocess
import sys
import os
import random
import platform
from typing import Tuple, Dict, List


HOST = "localhost"
PORT = 6379
SERVER_SCRIPT = "../kv_store_server.py"
DB_FILE = "../kvstore.db.snapshot"


def get_server_pid(host: str, port: int) -> int:
    """Find the PID of the server process listening on the given port"""
    if platform.system() == "Windows":
        import subprocess
        result = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True,
            text=True
        )
        for line in result.stdout.split('\n'):
            if f":{port}" in line and "LISTENING" in line:
                parts = line.split()
                if parts:
                    return int(parts[-1])
    else:
        # Unix/Linux
        import subprocess
        result = subprocess.run(
            ["lsof", "-i", f":{port}", "-t"],
            capture_output=True,
            text=True
        )
        pid_str = result.stdout.strip()
        if pid_str:
            return int(pid_str.split('\n')[0])
    
    return None


def kill_server(pid: int):
    """Forcefully kill the server process"""
    try:
        if platform.system() == "Windows":
            subprocess.run(["taskkill", "/F", "/PID", str(pid)], check=False)
        else:
            os.kill(pid, 9)  # SIGKILL on Unix
        print(f"  Force-killed server (PID: {pid})")
    except Exception as e:
        print(f"  Error killing server: {e}")


def send_command(sock: socket.socket, command: str) -> Tuple[bool, str]:
    """Send a command and receive response, returns (success, response)"""
    try:
        sock.send(command.encode('utf-8') + b'\n')
        response = sock.recv(4096).decode('utf-8').strip()
        return True, response
    except Exception as e:
        return False, str(e)


def start_server() -> subprocess.Popen:
    """Start the server process"""
    try:
        # Change to the parent directory to run the server
        original_dir = os.getcwd()
        server_dir = os.path.dirname(os.path.abspath(__file__))
        server_dir = os.path.dirname(server_dir)  # Go up to parent
        
        process = subprocess.Popen(
            [sys.executable, os.path.join(server_dir, "kv_store_server.py")],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        time.sleep(0.5)  # Give server time to start
        return process
    except Exception as e:
        print(f"Error starting server: {e}")
        return None


def restore_from_snapshot() -> Dict:
    """Load the database from snapshot file if it exists"""
    db_file = os.path.join(os.path.dirname(__file__), "..", "kvstore.db.snapshot")
    if os.path.exists(db_file):
        try:
            with open(db_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"  Error loading snapshot: {e}")
    return {}


def run_durability_test(num_writes: int = 100, kill_delay_range: Tuple[float, float] = (0.1, 0.5)):
    """
    Run durability test:
    1. Start server
    2. Send writes and track which got OK response
    3. Kill server at random point
    4. Restart server and check which writes persisted
    5. Count lost writes
    
    Args:
        num_writes: Number of write operations to perform
        kill_delay_range: Range (min, max) for random kill delay in seconds
    """
    print("\n" + "="*70)
    print("Durability Test")
    print("="*70)
    print(f"Testing with {num_writes} write operations")
    print(f"Server will be killed at random point during writes\n")
    
    # Start fresh server
    print("Starting server...")
    server_process = start_server()
    if not server_process:
        print("Failed to start server")
        return
    
    time.sleep(1)  # Give server time to be fully ready
    
    # Connect to server
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((HOST, PORT))
    except Exception as e:
        print(f"Failed to connect to server: {e}")
        server_process.terminate()
        return
    
    # Track successful writes
    successful_writes: Dict[str, str] = {}
    write_order: List[str] = []
    writes_before_kill = 0
    
    # Determine random kill point
    kill_at_write = random.randint(int(num_writes * 0.3), int(num_writes * 0.9))
    print(f"Server will be killed after write #{kill_at_write}/{num_writes}\n")
    
    print("Sending writes...", end="", flush=True)
    start_time = time.perf_counter()
    
    for i in range(num_writes):
        key = f"durability_test_{i:05d}"
        value = json.dumps({"index": i, "timestamp": time.time()})
        command = f'SET {key} {value}'
        
        success, response = send_command(sock, command)
        
        if success:
            try:
                resp_obj = json.loads(response)
                if resp_obj.get("status") == "OK":
                    successful_writes[key] = value
                    write_order.append(key)
                    writes_before_kill = i + 1
            except:
                pass
        
        # Kill server at random point
        if i == kill_at_write:
            print(f" [KILL]", end="", flush=True)
            sock.close()
            pid = get_server_pid(HOST, PORT)
            if pid:
                kill_server(pid)
            time.sleep(1)  # Wait a bit after kill
            break
    
    end_time = time.perf_counter()
    write_time = end_time - start_time
    
    print(f" Done ({write_time:.3f}s)")
    print(f"Successful writes before kill: {writes_before_kill}")
    print(f"Total writes with OK status: {len(successful_writes)}\n")
    
    # Wait for server to fully shut down
    time.sleep(1)
    
    # Restart server
    print("Restarting server...")
    server_process = start_server()
    if not server_process:
        print("Failed to restart server")
        return
    
    time.sleep(1)
    
    # Check which writes persisted
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((HOST, PORT))
    except Exception as e:
        print(f"Failed to reconnect to server: {e}")
        server_process.terminate()
        return
    
    print("\nVerifying persisted writes...")
    persisted_writes = 0
    lost_writes = 0
    lost_write_indices = []
    
    for idx, key in enumerate(write_order):
        command = f'GET {key}'
        success, response = send_command(sock, command)
        
        if success:
            try:
                resp_obj = json.loads(response)
                if resp_obj.get("status") == "OK":
                    persisted_writes += 1
                else:
                    lost_writes += 1
                    lost_write_indices.append(idx)
            except:
                lost_writes += 1
                lost_write_indices.append(idx)
        else:
            lost_writes += 1
            lost_write_indices.append(idx)
    
    sock.close()
    server_process.terminate()
    
    # Calculate results
    loss_rate = (lost_writes / len(successful_writes) * 100) if successful_writes else 0
    
    print("\n" + "="*70)
    print("DURABILITY TEST RESULTS")
    print("="*70)
    print(f"Total successful writes (got OK): {len(successful_writes)}")
    print(f"Persisted after restart: {persisted_writes}")
    print(f"Lost writes: {lost_writes}")
    print(f"Data loss rate: {loss_rate:.2f}%")
    print("="*70)
    
    if lost_writes > 0:
        print(f"\nLost writes at indices: {lost_write_indices[:20]}", end="")
        if len(lost_write_indices) > 20:
            print(f" ... and {len(lost_write_indices) - 20} more")
        else:
            print()
    
    # Clean up snapshot file for next test
    db_file = os.path.join(os.path.dirname(__file__), "..", "kvstore.db.snapshot")
    if os.path.exists(db_file):
        try:
            os.remove(db_file)
        except:
            pass


def run_multiple_tests(num_tests: int = 5, num_writes: int = 100):
    """Run durability test multiple times and aggregate results"""
    
    print("\n" + "="*70)
    print(f"Running {num_tests} Durability Tests")
    print("="*70)
    
    results = []
    
    for test_num in range(num_tests):
        print(f"\n[Test {test_num + 1}/{num_tests}]")
        # Run test and collect results (simplified - just run the test)
        run_durability_test(num_writes)
        time.sleep(2)  # Wait between tests
    
    print("\n" + "="*70)
    print("All durability tests completed")
    print("="*70)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Durability benchmark for key-value store")
    parser.add_argument("--writes", type=int, default=100, help="Number of writes per test")
    parser.add_argument("--tests", type=int, default=1, help="Number of tests to run")
    
    args = parser.parse_args()
    
    if args.tests > 1:
        run_multiple_tests(args.tests, args.writes)
    else:
        run_durability_test(args.writes)
