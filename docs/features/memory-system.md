# Memory System

## Overview

Loom implements a dual-perspective memory system to handle both **Time** (Temporal Entropy) and **Space** (Complexity/Fractal Depth):

1.  **Metabolic Memory (L1-L4)**: Handles the *temporal* aspect. It metabolizes raw experience into structured knowledge over time.
2.  **Fractal Memory Scopes**: Handles the *spatial* aspect. It manages how memory is shared or isolated between parent and child nodes in the fractal tree.

---

## Part 1: Metabolic Memory (L1-L4)

Just as biological organisms metabolize food into energy and waste, Loom metabolizes **Experience** into **Knowledge** and **Noise**.

### The Hierarchy

| Layer | Name | Purpose | Retention | Capacity | Access |
|-------|------|---------|-----------|----------|--------|
| **L1** | Working Memory | Immediate context (RAM) | 1 hour | 10 items | Auto-included |
| **L2** | Session Memory | Short-term workspace | 24 hours | 50 items | Tool search |
| **L3** | Episodic Memory | Cross-session history | 7 days | 200 items | Tool search |
| **L4** | Semantic Memory | Long-term knowledge base | Permanent | ∞ | Vector search |

### The Metabolic Process

1.  **Ingest (L1)**: Raw interactions entering the system.
2.  **Digest (L2)**: Important items are promoted to L2 based on access frequency (≥3 accesses).
3.  **Assimilate (L3)**: key sessions are summarized and stored as episodes.
4.  **Sediment (L4)**: High-value insights are compressed, vectorized, and stored in the permanent knowledge base.

---

## Part 2: Fractal Memory Scopes

In a Fractal Architecture, thousands of nodes might exist simultaneously. If every node shared the same memory, context would explode. If every node was isolated, collaboration would be impossible.

Loom solves this with **Scoped Memory** (`loom.fractal.memory`).

### defined Scopes

#### 1. LOCAL (`MemoryScope.LOCAL`)
- **Visibility**: Private to the specific node.
- **Use Case**: Temporary variables, internal chain-of-thought, intermediate calculations.
- **Persistence**: Cleared when the node task updates.

#### 2. SHARED (`MemoryScope.SHARED`)
- **Visibility**: Visible to the Node, its Parent, and its Children.
- **Use Case**: Collaborative data, active sub-task requirements.
- **Sync**: Changes propagate up and down one level.

#### 3. GLOBAL (`MemoryScope.GLOBAL`)
- **Visibility**: Visible to every node in the organism.
- **Use Case**: Core directives, immutable facts, world state.
- **Cost**: Expensive (use sparingly).

### FractalMemory Manager

The `FractalMemory` class acts as the bridge. It manages the scopes and delegates storage to the underlying `LoomMemory` (L1-L4).

```python
class FractalMemory:
    async def read(self, entry_id, scopes=[MemoryScope.LOCAL, MemoryScope.SHARED]):
        # Tries to find entry in LOCAL, then SHARED, then asks Parent
        ...
```

---

## Configuration

You can configure the memory system via `AgentConfig`:

```python
from loom.config.memory import MemoryConfig, MemoryLayerConfig

config = MemoryConfig(
    # Metabolic Configuration
    l1=MemoryLayerConfig(capacity=20, retention_hours=1),
    l4=MemoryLayerConfig(capacity=1000, retention_hours=None),
    
    # Fractal Features
    enable_scopes=True
)
```

## Best Practices

1.  **Keep L1 lean**: L1 is auto-injected. If it's too big, it wastes tokens on every call.
2.  **Promote aggressively**: If a piece of info is used twice, move it to L2.
3.  **Default to LOCAL**: only use SHARED scope if extensive collaboration is required.
