"""Persistent memory (M_f)"""

import json
from pathlib import Path


class PersistentMemory:
    """File-based persistent memory"""
    
    def __init__(self, storage_path: str = ".loom/memory"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
    
    def save(self, key: str, data: dict):
        """Save data to file"""
        file_path = self.storage_path / f"{key}.json"
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load(self, key: str) -> dict | None:
        """Load data from file"""
        file_path = self.storage_path / f"{key}.json"
        if not file_path.exists():
            return None
        with open(file_path, 'r') as f:
            return json.load(f)
    
    def delete(self, key: str):
        """Delete data"""
        file_path = self.storage_path / f"{key}.json"
        if file_path.exists():
            file_path.unlink()
