"""
Loom Builtin Memory - "The Past"
================================

This module provides implementations for agent memory.

## 💾 Memory Systems

### 1. InMemoryMemory (`InMemoryMemory`)
Stores messages in a simple Python list. 
- **Use Case**: Testing, ephemeral scripts.
- **Persistence**: None. Lost on restart.

### 2. PersistentMemory (`PersistentMemory`)
Stores messages in a persistent store (e.g. File, DB).
- **Use Case**: Production apps, long-running sessions.
- **Persistence**: Saved to disk/DB.

### 3. HierarchicalMemory (`HierarchicalMemory`)
Structured memory for complex state (Working Memory vs Long-term).
"""

from .in_memory import InMemoryMemory
from .persistent_memory import PersistentMemory
from .hierarchical_memory import HierarchicalMemory, MemoryEntry

__all__ = [
    "InMemoryMemory",
    "PersistentMemory",
    "HierarchicalMemory",
    "MemoryEntry",
]

