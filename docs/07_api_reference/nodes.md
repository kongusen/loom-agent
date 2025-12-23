# Nodes & Agents

All components in Loom inherit from the base `Node` class.

## `loom.node.base.Node` (Abstract)

### Constructor
```python
def __init__(self, node_id: str, dispatcher: Dispatcher)
```
- **node_id**: Unique identifier.
- **dispatcher**: Reference to the kernel dispatcher.

### Methods

#### `call`
```python
async def call(self, target_node: str, data: Dict[str, Any]) -> Any
```
Performs a synchronous Request-Reply RPC call to another node.
- **target_node**: ID of the destination.
- **data**: Payload dictionary.
- **Returns**: Result from the target.

#### `process` (Abstract)
```python
async def process(self, event: CloudEvent) -> Any
```
Core logic handler. Must be implemented by subclasses.

---

## `loom.node.agent.AgentNode`

An LLM-driven autonomous agent with Metabolic Memory.

### Constructor
```python
def __init__(
    self,
    node_id: str,
    dispatcher: Dispatcher,
    role: str = "Assistant",
    system_prompt: str = "...",
    tools: Optional[List[ToolNode]] = None,
    provider: Optional[LLMProvider] = None,
    memory: Optional[MemoryInterface] = None
)
```
- **role**: Friendly name/role.
- **tools**: List of `ToolNode` instances this agent can control.
- **provider**: LLM implementation (e.g., OpenAI).
- **memory**: Context management strategy.

---

## `loom.node.tool.ToolNode`

Wraps a function as a Loom Node, compliant with MCP.

### Constructor
```python
def __init__(
    self,
    node_id: str,
    dispatcher: Dispatcher,
    tool_def: MCPToolDefinition,
    func: Callable[[Dict], Awaitable[Any]]
)
```
- **tool_def**: MCP Schema definition.
- **func**: The implementation function. Must accept a dict and return JSON-serializable data.

---

## `loom.node.crew.CrewNode`

Orchestrates a group of agents.

### Constructor
```python
def __init__(
    self,
    node_id: str,
    dispatcher: Dispatcher,
    agents: List[AgentNode],
    pattern: Literal["sequential", "parallel"] = "sequential",
    sanitizer: Optional[ContextSanitizer] = None
)
```
- **pattern**: Currently supports "sequential" (Pipeline).
- **sanitizer**: Logic to compress outputs before bubbling up.

---

## `loom.node.router.AttentionRouter`

Routes tasks using LLM reasoning.

### Constructor
```python
def __init__(
    self,
    node_id: str,
    dispatcher: Dispatcher,
    agents: List[AgentNode],
    provider: LLMProvider
)
```
- **agents**: Candidate agents to route to.
