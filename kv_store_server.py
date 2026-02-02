#!/usr/bin/env python3
"""
Key-Value Store Database Server with TCP Interface
Redis-like protocol for high performance
"""

from typing import Any, Optional
import json
import os
import threading
import time
import socket
import signal
import sys


class KeyValueStore:
    """Thread-safe in-memory key-value store"""
    
    def __init__(self):
        self.store: dict[str, Any] = {}
        self.lock = threading.Lock()
    
    def set(self, key: str, value: Any) -> dict:
        """Set a key-value pair"""
        with self.lock:
            self.store[key] = value
            return {"status": "OK"}
    
    def get(self, key: str) -> Optional[Any]:
        """Get value for a key"""
        with self.lock:
            return self.store.get(key)
    
    def delete(self, key: str) -> dict:
        """Delete a key"""
        with self.lock:
            if key in self.store:
                del self.store[key]
                return {"status": "OK"}
            else:
                return {"status": "ERROR"}


class TCPServer:
    """TCP server with simple command protocol"""
    
    def __init__(self, kv_store: KeyValueStore, host: str = '0.0.0.0', port: int = 6379):
        self.kv_store = kv_store
        self.host = host
        self.port = port
        self.socket = None
        self.running = True
    
    def start(self):
        """Start the TCP server"""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((self.host, self.port))
        self.socket.listen(5)
        print(f"TCP Server listening on {self.host}:{self.port}")
        
        try:
            while self.running:
                client_socket, addr = self.socket.accept()
                print(f"Client connected: {addr}")
                # Handle client in a separate thread
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket, addr),
                    daemon=True
                )
                client_thread.start()
        except KeyboardInterrupt:
            self.stop()
    
    def stop(self):
        """Stop the server"""
        self.running = False
        if self.socket:
            self.socket.close()
        print("Server stopped")
    
    def handle_client(self, client_socket: socket.socket, addr):
        """Handle a client connection"""
        try:
            while self.running:
                # Receive data
                data = client_socket.recv(4096)
                if not data:
                    break
                
                # Parse command
                command_str = data.decode('utf-8').strip()
                response = self.process_command(command_str)
                
                # Send response
                client_socket.send(response.encode('utf-8') + b'\n')
        except Exception as e:
            print(f"Error handling client {addr}: {e}")
        finally:
            client_socket.close()
            print(f"Client disconnected: {addr}")
    
    def process_command(self, command_str: str) -> str:
        """Process a command and return response"""
        try:
            parts = command_str.split(None, 2)  # Split on whitespace, max 3 parts
            if not parts:
                return json.dumps({"status": "ERROR", "message": "Empty command"})
            
            cmd = parts[0].upper()
            
            if cmd == "SET" and len(parts) == 3:
                key, value = parts[1], parts[2]
                try:
                    value = json.loads(value)  # Try to parse as JSON
                except:
                    pass  # Keep as string if not valid JSON
                self.kv_store.set(key, value)
                return json.dumps({"status": "OK", "message": f"Key '{key}' set"})
            
            elif cmd == "GET" and len(parts) == 2:
                key = parts[1]
                value = self.kv_store.get(key)
                if value is None:
                    return json.dumps({"status": "ERROR", "message": f"Key '{key}' not found"})
                return json.dumps({"status": "OK", "value": value})
            
            elif cmd == "DELETE" and len(parts) == 2:
                key = parts[1]
                result = self.kv_store.delete(key)
                return json.dumps(result)
            
            elif cmd == "FLUSH":
                return json.dumps({"status": "OK", "message": "No persistence enabled"})
            
            elif cmd == "SNAPSHOT":
                return json.dumps({"status": "OK", "message": "No persistence enabled"})
            
            elif cmd == "PING":
                return json.dumps({"status": "OK", "message": "PONG"})
            
            elif cmd == "SHUTDOWN":
                self.stop()
                return json.dumps({"status": "OK", "message": "Server shutting down"})
            
            else:
                return json.dumps({"status": "ERROR", "message": f"Unknown command: {cmd}"})
        
        except Exception as e:
            return json.dumps({"status": "ERROR", "message": str(e)})


# Initialize key-value store
kv_store = KeyValueStore()


if __name__ == "__main__":
    # Create and start TCP server
    server = TCPServer(kv_store, host="0.0.0.0", port=6379)
    
    # Handle graceful shutdown
    def signal_handler(signum, frame):
        server.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    server.start()