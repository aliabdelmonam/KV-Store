#!/usr/bin/env python3
"""
FastAPI Key-Value Store Database Server
REST API with GET, SET, and DELETE endpoints
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any, Optional
import json
import os
import threading
import time
import uvicorn
import signal
import sys


class SetRequest(BaseModel):
    """Request model for SET operation"""
    key: str
    value: Any


class KeyRequest(BaseModel):
    """Request model for GET and DELETE operations"""
    key: str


class KeyValueStore:
    """Thread-safe persistent key-value store with batched writes"""
    
    def __init__(self, data_file: str = 'kvstore.db', batch_size: int = 100, flush_interval: float = 1.0):
        self.store: dict[str, Any] = {}
        self.lock = threading.Lock()
        self.data_file = data_file
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.pending_writes = 0
        self.dirty = False
        self._load_from_disk()
        
        # Start background flush thread
        self.flush_thread = threading.Thread(target=self._flush_worker, daemon=True)
        self.flush_thread.start()
    
    def _flush_worker(self):
        """Background thread that periodically flushes data to disk"""
        while True:
            time.sleep(self.flush_interval)
            with self.lock:
                if self.dirty:
                    self._save_to_disk()
                    self.dirty = False
    
    def _load_from_disk(self):
        """Load data from disk on startup"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    self.store = json.load(f)
                print(f"Loaded {len(self.store)} keys from {self.data_file}")
            except Exception as e:
                print(f"Error loading data from disk: {e}")
                self.store = {}
        else:
            print(f"No existing data file found. Starting with empty store.")
    
    def _save_to_disk(self):
        """Save data to disk"""
        try:
            # Write to temporary file first, then rename for atomicity
            temp_file = self.data_file + '.tmp'
            with open(temp_file, 'w') as f:
                json.dump(self.store, f, indent=2)
            os.replace(temp_file, self.data_file)
        except Exception as e:
            print(f"Error saving data to disk: {e}")
    
    def set(self, key: str, value: Any) -> dict:
        """Set a key-value pair"""
        with self.lock:
            self.store[key] = value
            self.pending_writes += 1
            self.dirty = True
            
            # Flush if batch size reached
            if self.pending_writes >= self.batch_size:
                self._save_to_disk()
                self.pending_writes = 0
                self.dirty = False
            
            return {"status": "OK", "message": f"Key '{key}' set successfully"}
    
    def get(self, key: str) -> dict:
        """Get value for a key"""
        with self.lock:
            if key in self.store:
                return {"status": "OK", "key": key, "value": self.store[key]}
            else:
                return {"status": "ERROR", "message": f"Key '{key}' not found"}
    
    def delete(self, key: str) -> dict:
        """Delete a key"""
        with self.lock:
            if key in self.store:
                del self.store[key]
                self.pending_writes += 1
                self.dirty = True
                
                # Flush if batch size reached
                if self.pending_writes >= self.batch_size:
                    self._save_to_disk()
                    self.pending_writes = 0
                    self.dirty = False
                
                return {"status": "OK", "message": f"Key '{key}' deleted successfully"}
            else:
                return {"status": "ERROR", "message": f"Key '{key}' not found"}


# Initialize FastAPI app and key-value store
app = FastAPI(
    title="Key-Value Store API",
    description="Simple persistent key-value store with SET, GET, and DELETE operations",
    version="1.0.0"
)

kv_store = KeyValueStore()


@app.get("/")
def root():
    """Root endpoint"""
    return {
        "message": "Key-Value Store API",
        "endpoints": {
            "set": "POST /set",
            "get": "GET /get/{key}",
            "delete": "DELETE /delete/{key}",
            "flush": "POST /flush",
            "shutdown": "POST /shutdown"
        }
    }


@app.post("/set")
def set_value(request: SetRequest):
    """
    Set a key-value pair
    
    Request body:
    {
        "key": "mykey",
        "value": "myvalue"
    }
    """
    result = kv_store.set(request.key, request.value)
    return result


@app.get("/get/{key}")
def get_value_path(key: str):
    """
    Get value for a key (GET method with path parameter)
    
    Example: GET /get/mykey
    """
    result = kv_store.get(key)
    if result["status"] == "ERROR":
        raise HTTPException(status_code=404, detail=result["message"])
    return result


@app.delete("/delete/{key}")
def delete_value_path(key: str):
    """
    Delete a key (DELETE method with path parameter)
    
    Example: DELETE /delete/mykey
    """
    result = kv_store.delete(key)
    if result["status"] == "ERROR":
        raise HTTPException(status_code=404, detail=result["message"])
    return result


@app.post("/flush")
def flush_data():
    """
    Force flush all pending writes to disk
    
    Example: POST /flush
    """
    with kv_store.lock:
        if kv_store.dirty:
            kv_store._save_to_disk()
            kv_store.pending_writes = 0
            kv_store.dirty = False
            return {"message": f"Flushed {kv_store.pending_writes} pending writes to disk"}
        else:
            return {"message": "No pending writes to flush"}


@app.post("/shutdown")
def shutdown():
    """
    Shutdown the server
    
    Example: POST /shutdown
    """
    os.kill(os.getpid(), signal.SIGTERM)
    return {"message": "Server shutting down"}


@app.post("/restart")
def restart():
    """
    Restart the server
    
    Example: POST /restart
    """
    import subprocess
    # Spawn new process and exit current one
    subprocess.Popen([sys.executable, __file__])
    os.kill(os.getpid(), signal.SIGTERM)
    return {"message": "Server restarting"}


if __name__ == "__main__":
    # Run the server
    # host="0.0.0.0" makes it accessible externally
    uvicorn.run(app, host="0.0.0.0", port=8000)