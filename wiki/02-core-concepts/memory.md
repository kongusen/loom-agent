# Memory

Loom provides four memory layers, each with a different scope and lifetime.

## Four Layers

| Layer | Class | Scope | Persisted |
|---|---|---|---|
| Session | `SessionMemory` | Current conversation window | No |
| Working | `WorkingMemory` | Current task dashboard + scratchpad | No |
| Semantic | `SemanticMemory` | Vector search across past entries | Optional (JSON) |
| Persistent | `PersistentMemory` | Cross-session key-value store (M_f) | Yes (filesystem) |

## SemanticMemory

```python
from loom.memory import SemanticMemory, MemoryEntry

mem = SemanticMemory(max_size=10_000, persist_path="memory.json")
mem.add(MemoryEntry(content="...", embedding=[...]))
results = mem.search("query", top_k=5)
```

- Cosine similarity search with lexical fallback
- FIFO eviction when `max_size` is exceeded
- Optional JSON persistence across sessions

## PersistentMemory (M_f)

The filesystem is the shared substrate for multi-agent communication (Theorem 2).

```python
from loom.memory import PersistentMemory

store = PersistentMemory(base_dir=".loom/memory")
store.set("last_result", {"summary": "..."})
value = store.get("last_result")
```

**Code:** `loom/memory/`
