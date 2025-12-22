"""
Loom Patterns - "The Glue"
==========================

This module provides the structural primitives to compose Agents and Runnables.

## 🧩 Composition Primitives

### 1. Sequence (`A >> B`)
Executes components linearly. The output of A becomes the input of B.
```python
chain = Sequence([Researcher, Writer])
# Researcher output -> Writer input
```

### 2. Group (`[A, B]`)
Executes components in parallel.
```python
team = Group(
    Runnables=[Analyst1, Analyst2], 
    aggregator=Synthesizer
)
# Both run at once -> Synthesizer combines results
```

### 3. Router (`A -> {B, C}`)
Conditional branching based on input or previous result.
```python
route = Router(
    routes={
        "code": CoderAgent,
        "chat": ChatAgent
    },
    selector=lambda x: "code" if "def" in x else "chat"
)
```

## 👥 Crew (`Crew`)
High-level Orchestration wrapper. 
Currently implements a `Sequence` pattern but designed for expansion.
"""

from .crew import Crew
from .composition import Sequence, Group, Router

__all__ = [
    "Crew",
    "Sequence",
    "Group",
    "Router",
]
