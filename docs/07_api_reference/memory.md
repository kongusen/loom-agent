# Memory System

Loom's Metabolic Memory system is designed to "digest" information rather than just appending it.

## `loom.builtin.memory.metabolic.MetabolicMemory`

The default memory strategy for `AgentNode`.

### Constructor
```python
def __init__(
    self, 
    validator: Optional[MemoryValidator] = None,
    pso: Optional[ProjectStateObject] = None,
    sanitizer: Optional[ContextSanitizer] = None
)
```
- **validator**: Scores incoming information (0.0 - 1.0). Default: `HeuristicValueAssessor`.
- **pso**: Maintains the long-term project state. Default: `SimplePSO`.
- **sanitizer**: Compresses content during consolidation. Default: `CompressiveSanitizer`.

### Methods
- `add(role: str, content: str, metadata: dict)`: Ingests new information.
- `get_context(task: str)`: Returns the current Context (PSO + Short Term).
- `consolidate()`: Triggers the metabolic cycle to merge Short Term -> PSO.

---

## Protocols (`loom.protocol.memory_operations`)

### `MemoryValidator`
```python
class MemoryValidator(Protocol):
    async def validate(self, content: Any) -> float: ...
```
Implement this to filter noise. Return `0.0` to discard, `1.0` to keep forever.

### `ProjectStateObject` (PSO)
```python
class ProjectStateObject(Protocol):
    async def update(self, events: List[Dict]) -> None: ...
    def to_markdown(self) -> str: ...
```
The "Brain" of the project. It should extract goals, status, and key facts from the event stream.

### `ContextSanitizer`
```python
class ContextSanitizer(Protocol):
    async def sanitize(self, context: str, target_token_limit: int) -> str: ...
```
Implement this to summarize or extract key points from verbose outputs (e.g., long tool logs).
