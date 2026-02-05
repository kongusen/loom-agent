"""
Memory Layer Abstractions

Provides unified interfaces for all memory layers (L1-L4).

Note: Implementation moved to layers_merged.py for reduced module count.
This file provides backward compatibility.
"""

from loom.memory.layers_merged import (
    CircularBufferLayer,
    MemoryLayer,
    PriorityItem,
    PriorityQueueLayer,
)

__all__ = ["MemoryLayer", "CircularBufferLayer", "PriorityQueueLayer", "PriorityItem"]
