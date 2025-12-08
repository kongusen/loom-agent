# Loom Agent v0.0.8 API Reference

**Version**: v0.0.8
**Release Date**: 2025-12-09
**Architecture**: Recursive State Machine (RSM)

---

## Table of Contents

1. [High-Level API](#high-level-api)
   - [agent() Factory Function](#agent-factory-function)
   - [agent_from_env()](#agent_from_env)
2. [Core Components](#core-components)
   - [ExecutionFrame](#executionframe)
   - [EventJournal](#eventjournal)
   - [StateReconstructor](#statereconstructor)
   - [ContextDebugger](#contextdebugger)
3. [Lifecycle Hooks](#lifecycle-hooks)
   - [Hook Protocol](#hook-protocol)
   - [Built-in Hooks](#built-in-hooks)
   - [Custom Hooks](#custom-hooks)
4. [AgentExecutor API](#agentexecutor-api)
5. [Tool API](#tool-api)
6. [LLM API](#llm-api)
7. [Memory API](#memory-api)

---

## High-Level API

### agent() Factory Function

The main entry point for creating agents with v0.0.8 features.

```python
from loom import agent
from pathlib import Path
from loom.core.lifecycle_hooks import LifecycleHook
from loom.core import EventJournal, ContextDebugger

my_agent = agent(
    # LLM Configuration (choose one)
    llm: Optional[BaseLLM] = None,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,

    # Agent Options
    tools: Optional[List[BaseTool]] = None,
    memory: Optional[BaseMemory] = None,
    compressor: Optional[BaseCompressor] = None,
    max_iterations: int = 50,
    max_context_tokens: int = 16000,
    system_instructions: Optional[str] = None,

    # 🆕 v0.0.8 - Recursive State Machine Features
    hooks: Optional[List[LifecycleHook]] = None,
    enable_persistence: bool = False,
    journal_path: Optional[Path] = None,
    event_journal: Optional[EventJournal] = None,
    context_debugger: Optional[ContextDebugger] = None,
    thread_id: Optional[str] = None,
)
```

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `provider` | `str` | `None` | LLM provider (`"openai"`, `"anthropic"`, etc.) |
| `model` | `str` | `None` | Model name (e.g., `"gpt-4"`) |
| `tools` | `List[BaseTool]` | `None` | List of available tools |
| `max_iterations` | `int` | `50` | Maximum recursion depth |
| `max_context_tokens` | `int` | `16000` | Token budget for context |
| `system_instructions` | `str` | `None` | System prompt |
| **🆕 `hooks`** | `List[LifecycleHook]` | `None` | Lifecycle hooks for execution control |
| **🆕 `enable_persistence`** | `bool` | `False` | Auto-enable event sourcing |
| **🆕 `journal_path`** | `Path` | `None` | Path to store event journal |
| **🆕 `event_journal`** | `EventJournal` | `None` | Pre-configured event journal |
| **🆕 `context_debugger`** | `ContextDebugger` | `None` | Context debugging tool |
| **🆕 `thread_id`** | `str` | `None` | Unique thread ID for event isolation |

#### Examples

**Basic Usage (v0.0.7 compatible)**:
```python
from loom import agent

my_agent = agent(
    provider="openai",
    model="gpt-4",
    tools=[]
)

result = await my_agent.run("Hello")
```

**🆕 With Event Sourcing**:
```python
from loom import agent
from pathlib import Path

my_agent = agent(
    provider="openai",
    model="gpt-4",
    tools=tools,
    enable_persistence=True,  # 🆕 Auto-creates EventJournal
    journal_path=Path("./logs"),  # 🆕 Storage location
    thread_id="session-123"  # 🆕 Thread ID
)
```

**🆕 With Lifecycle Hooks**:
```python
from loom import agent
from loom.core.lifecycle_hooks import LoggingHook, MetricsHook, HITLHook

my_agent = agent(
    provider="openai",
    model="gpt-4",
    tools=tools,
    hooks=[  # 🆕 Lifecycle hooks
        LoggingHook(verbose=True),
        MetricsHook(),
        HITLHook(dangerous_tools=["delete_file"])
    ]
)
```

**🆕 Production Setup**:
```python
from loom import agent
from loom.core import ContextDebugger
from loom.core.lifecycle_hooks import LoggingHook, MetricsHook, HITLHook
from pathlib import Path

debugger = ContextDebugger(enable_auto_export=True)

my_agent = agent(
    provider="openai",
    model="gpt-4",
    tools=production_tools,
    system_instructions="You are a production assistant.",
    # 🆕 All v0.0.8 features
    enable_persistence=True,
    journal_path=Path("/var/log/loom"),
    hooks=[
        HITLHook(dangerous_tools=["delete_file", "execute_shell"]),
        LoggingHook(verbose=False),
        MetricsHook()
    ],
    context_debugger=debugger,
    thread_id=session_id,
    max_iterations=100,
    max_context_tokens=32000
)
```

---

### agent_from_env()

Create agent from environment variables with v0.0.8 features.

```python
from loom import agent_from_env

my_agent = agent_from_env(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    # ... same parameters as agent()
    # 🆕 v0.0.8 parameters also supported
    hooks: Optional[List[LifecycleHook]] = None,
    enable_persistence: bool = False,
    journal_path: Optional[Path] = None,
)
```

**Environment Variables**:
- `OPENAI_API_KEY` - OpenAI API key
- `ANTHROPIC_API_KEY` - Anthropic API key
- `LOOM_PROVIDER` - Default provider
- `LOOM_MODEL` - Default model

---

## Core Components

### ExecutionFrame

**🆕 v0.0.8** - Immutable execution stack frame representing one recursion level.

```python
from loom.core.execution_frame import ExecutionFrame, ExecutionPhase
```

#### Class Definition

```python
@dataclass(frozen=True)
class ExecutionFrame:
    frame_id: str
    parent_frame_id: Optional[str] = None
    depth: int = 0
    phase: ExecutionPhase = ExecutionPhase.INITIAL
    messages: List[Dict[str, Any]] = field(default_factory=list)
    context_snapshot: Dict[str, Any] = field(default_factory=dict)
    context_metadata: Dict[str, Any] = field(default_factory=dict)
    llm_response: Optional[str] = None
    llm_tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    tool_results: List[Dict[str, Any]] = field(default_factory=list)
    max_iterations: int = 50
    tool_call_history: List[str] = field(default_factory=list)
    error_count: int = 0
    last_outputs: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
```

#### ExecutionPhase Enum

```python
class ExecutionPhase(str, Enum):
    INITIAL = "initial"
    CONTEXT_ASSEMBLY = "context_assembly"
    LLM_CALL = "llm_call"
    DECISION = "decision"
    TOOL_EXECUTION = "tool_execution"
    RECURSION = "recursion"
    COMPLETED = "completed"
    ERROR = "error"
```

#### Methods

##### `next_frame(new_messages: List[Dict]) -> ExecutionFrame`

Create next recursion frame.

```python
next_frame = current_frame.next_frame(new_messages=[
    {"role": "assistant", "content": "..."},
    {"role": "tool", "content": "..."}
])
```

##### `with_context(context_snapshot: Dict, context_metadata: Dict) -> ExecutionFrame`

Update frame with context assembly results.

```python
frame = frame.with_context(
    context_snapshot={"system_prompt": "..."},
    context_metadata={"tokens": 1500, "components": 3}
)
```

##### `with_llm_response(content: str, tool_calls: List[Dict]) -> ExecutionFrame`

Update frame with LLM response.

```python
frame = frame.with_llm_response(
    content="I'll search for that.",
    tool_calls=[{"id": "call_1", "name": "search", "arguments": {...}}]
)
```

##### `with_tool_results(tool_results: List[Dict], had_error: bool) -> ExecutionFrame`

Update frame with tool execution results.

```python
frame = frame.with_tool_results(
    tool_results=[{
        "tool_call_id": "call_1",
        "tool_name": "search",
        "content": "Found results",
        "is_error": False
    }],
    had_error=False
)
```

##### `to_checkpoint() -> Dict`

Serialize frame to checkpoint for crash recovery.

```python
checkpoint = frame.to_checkpoint()
# Save to journal for later resumption
```

---

### EventJournal

**🆕 v0.0.8** - Append-only event log for event sourcing.

```python
from loom.core.event_journal import EventJournal
from pathlib import Path
```

#### Class Definition

```python
class EventJournal:
    def __init__(
        self,
        storage_path: Path,
        batch_size: int = 100,
        flush_interval_seconds: float = 5.0
    ):
        ...
```

#### Methods

##### `async start() -> None`

Start the journal (begins flush loop).

```python
journal = EventJournal(storage_path=Path("./logs"))
await journal.start()
```

##### `async stop() -> None`

Stop the journal and flush remaining events.

```python
await journal.stop()
```

##### `async append(event: AgentEvent, thread_id: str) -> None`

Append event to journal.

```python
from loom.core.events import AgentEvent, AgentEventType

event = AgentEvent(
    type=AgentEventType.LLM_COMPLETE,
    iteration=1
)
await journal.append(event, thread_id="session-123")
```

##### `async replay(thread_id: str) -> List[AgentEvent]`

Replay all events for a thread.

```python
events = await journal.replay(thread_id="session-123")
print(f"Replayed {len(events)} events")
```

#### Usage Example

```python
from loom.core.event_journal import EventJournal
from pathlib import Path

journal = EventJournal(
    storage_path=Path("./logs"),
    batch_size=100,  # Batch size for async writes
    flush_interval_seconds=5.0  # Auto-flush every 5s
)

await journal.start()

# Events automatically recorded during execution
# ...

await journal.stop()

# Later, replay events
events = await journal.replay(thread_id="session-123")
```

---

### StateReconstructor

**🆕 v0.0.8** - Rebuild execution state from event stream.

```python
from loom.core.state_reconstructor import StateReconstructor
```

#### Methods

##### `async reconstruct(events: List[AgentEvent]) -> Tuple[ExecutionFrame, ReconstructionMetadata]`

Reconstruct state from events.

```python
reconstructor = StateReconstructor()

events = await journal.replay(thread_id="session-123")
frame, metadata = await reconstructor.reconstruct(events)

print(f"Reconstructed to depth {frame.depth}")
print(f"Total events: {metadata.total_events}")
print(f"Final phase: {metadata.final_phase}")
```

##### `async reconstruct_at_iteration(events: List[AgentEvent], target_iteration: int) -> Tuple[ExecutionFrame, ReconstructionMetadata]`

Reconstruct state at specific iteration (time travel).

```python
# Time travel to iteration 5
frame, metadata = await reconstructor.reconstruct_at_iteration(
    events, target_iteration=5
)
```

##### `async reconstruct_with_new_strategy(events: List[AgentEvent], compression_strategy: BaseCompressor) -> Tuple[ExecutionFrame, ReconstructionMetadata]`

**🌟 Unique Feature** - Replay events with new strategies.

```python
# Use new compression strategy on old events
from loom.compression import NewCompressionStrategy

frame, metadata = await reconstructor.reconstruct_with_new_strategy(
    events,
    compression_strategy=NewCompressionStrategy()
)
# State reconstructed using NEW strategy!
```

#### ReconstructionMetadata

```python
@dataclass
class ReconstructionMetadata:
    total_events: int
    final_phase: Optional[ExecutionPhase]
    final_depth: int
    warnings: List[str]
    reconstruction_time_ms: float
```

---

### ContextDebugger

**🆕 v0.0.8** - Make context management decisions transparent.

```python
from loom.core.context_debugger import ContextDebugger
```

#### Constructor

```python
debugger = ContextDebugger(
    enable_auto_export: bool = False,
    export_dir: Path = Path("./context_debug")
)
```

#### Methods

##### `generate_summary() -> str`

Generate human-readable summary of all context decisions.

```python
summary = debugger.generate_summary()
print(summary)
```

**Output**:
```
Context Management Summary
=========================
Total iterations: 5
Total assemblies: 5
Average token utilization: 87.3%

Iteration Breakdown:
  - Iteration 1: 8,234 tokens (51.5% utilization)
  - Iteration 2: 12,456 tokens (77.9% utilization)
  - Iteration 3: 15,123 tokens (94.5% utilization) ⚠️ Near limit
```

##### `explain_iteration(iteration: int) -> str`

Explain what happened in a specific iteration.

```python
explanation = debugger.explain_iteration(3)
print(explanation)
```

**Output**:
```
Iteration 3 Context Assembly
=============================
Token Budget: 16,000
Tokens Used: 15,123 (94.5% utilization)

✅ Included Components:
  - base_instructions (1,200 tokens, priority=CRITICAL)
  - rag_docs (5,000 tokens, priority=HIGH)

❌ Excluded Components:
  - file_content.py (2,500 tokens, priority=MEDIUM)
    Reason: Token limit exceeded
```

##### `explain_component(component_name: str) -> str`

Track a specific component across all iterations.

```python
history = debugger.explain_component("file_content.py")
```

**Output**:
```
Component History: file_content.py
===================================
Iteration 1: ✅ Included (2,500 tokens)
Iteration 2: ✅ Included (2,500 tokens)
Iteration 3: ❌ Excluded (token limit exceeded)
Iteration 4: ❌ Excluded (token limit exceeded)
Iteration 5: ✅ Included (2,500 tokens)
```

##### `record_from_frame(frame: ExecutionFrame) -> None`

Record context decision from execution frame (called internally).

```python
# Called automatically by AgentExecutor
debugger.record_from_frame(frame)
```

---

## Lifecycle Hooks

**🆕 v0.0.8** - Intercept execution at 9 different points.

### Hook Protocol

```python
from loom.core.lifecycle_hooks import LifecycleHook

class MyCustomHook:
    """
    Implement any of these methods (all optional):
    """

    async def before_iteration_start(
        self, frame: ExecutionFrame
    ) -> Optional[ExecutionFrame]:
        """Called before each iteration starts."""
        return None  # or modified frame

    async def before_context_assembly(
        self, frame: ExecutionFrame
    ) -> Optional[ExecutionFrame]:
        """Called before context assembly."""
        return None

    async def after_context_assembly(
        self, frame: ExecutionFrame,
        context_snapshot: Dict,
        context_metadata: Dict
    ) -> Optional[Tuple[Dict, Dict]]:
        """Called after context assembly."""
        return None  # or (modified_snapshot, modified_metadata)

    async def before_llm_call(
        self, frame: ExecutionFrame,
        messages: List[Dict]
    ) -> Optional[List[Dict]]:
        """Called before LLM call."""
        return None  # or modified messages

    async def after_llm_response(
        self, frame: ExecutionFrame,
        content: str,
        tool_calls: List[Dict]
    ) -> Optional[Tuple[str, List[Dict]]]:
        """Called after LLM responds."""
        return None  # or (modified_content, modified_tool_calls)

    async def before_tool_execution(
        self, frame: ExecutionFrame,
        tool_call: Dict
    ) -> Optional[Dict]:
        """
        🔥 HITL KEY POINT
        Called before EACH tool execution.
        Raise InterruptException to pause execution.
        """
        return None  # or modified tool_call

    async def after_tool_execution(
        self, frame: ExecutionFrame,
        tool_result: Dict
    ) -> Optional[Dict]:
        """Called after each tool execution."""
        return None  # or modified result

    async def before_recursion(
        self, frame: ExecutionFrame,
        next_frame: ExecutionFrame
    ) -> Optional[ExecutionFrame]:
        """Called before recursive call."""
        return None  # or modified next_frame

    async def after_iteration_end(
        self, frame: ExecutionFrame
    ) -> Optional[ExecutionFrame]:
        """Called at end of iteration."""
        return None
```

### Built-in Hooks

#### LoggingHook

```python
from loom.core.lifecycle_hooks import LoggingHook

hook = LoggingHook(verbose: bool = True)
```

Logs all lifecycle events to console.

#### MetricsHook

```python
from loom.core.lifecycle_hooks import MetricsHook

hook = MetricsHook()

# After execution
metrics = hook.get_metrics()
# {
#   "llm_calls": 3,
#   "tool_calls": 5,
#   "iterations": 3,
#   "total_tokens": 12500
# }
```

Collects execution metrics.

#### HITLHook

```python
from loom.core.lifecycle_hooks import HITLHook

hook = HITLHook(
    dangerous_tools: List[str],
    ask_user_callback: Callable[[str], bool]
)
```

Human-in-the-Loop confirmation for dangerous operations.

**Example**:
```python
hitl_hook = HITLHook(
    dangerous_tools=["delete_file", "send_email", "execute_shell"],
    ask_user_callback=lambda msg: input(f"{msg} (y/n): ").lower() == "y"
)

my_agent = agent(
    provider="openai",
    model="gpt-4",
    tools=tools,
    hooks=[hitl_hook],
    enable_persistence=True  # Required for checkpoints
)
```

### Custom Hooks

#### Example: Analytics Hook

```python
class AnalyticsHook:
    def __init__(self):
        self.tool_usage = {}
        self.llm_calls = 0

    async def after_tool_execution(self, frame, tool_result):
        tool_name = tool_result["tool_name"]
        self.tool_usage[tool_name] = self.tool_usage.get(tool_name, 0) + 1
        return None

    async def before_llm_call(self, frame, messages):
        self.llm_calls += 1
        print(f"🤖 LLM call #{self.llm_calls} with {len(messages)} messages")
        return None

# Usage
analytics = AnalyticsHook()
my_agent = agent(
    provider="openai",
    model="gpt-4",
    tools=tools,
    hooks=[analytics]
)

await my_agent.run("Task")
print(f"Tool usage: {analytics.tool_usage}")
```

#### Example: Smart HITL Hook

```python
from loom.core.lifecycle_hooks import InterruptException

class SmartHITLHook:
    async def before_tool_execution(self, frame, tool_call):
        tool_name = tool_call["name"]
        args = tool_call["arguments"]

        # Rule: Confirm all delete operations
        if "delete" in tool_name.lower():
            confirmed = input(f"Confirm delete: {args}? (y/n): ") == "y"
            if not confirmed:
                raise InterruptException(
                    reason="User rejected delete operation",
                    requires_user_input=True
                )

        # Rule: Check email urgency
        if tool_name == "send_email" and "urgent" in args.get("subject", "").lower():
            confirmed = input(f"Send urgent email? (y/n): ") == "y"
            if not confirmed:
                raise InterruptException(
                    reason="User rejected urgent email",
                    requires_user_input=True
                )

        return None  # Allow execution
```

### Hook Exceptions

#### InterruptException

Pause execution and save checkpoint.

```python
from loom.core.lifecycle_hooks import InterruptException

raise InterruptException(
    reason: str = "User intervention required",
    requires_user_input: bool = True
)
```

#### SkipToolException

Skip current tool execution.

```python
from loom.core.lifecycle_hooks import SkipToolException

raise SkipToolException(reason="Tool not needed")
```

---

## AgentExecutor API

Low-level executor with direct access to v0.0.8 features.

```python
from loom.core.agent_executor import AgentExecutor
```

### Constructor

```python
executor = AgentExecutor(
    llm: BaseLLM,
    tools: Dict[str, BaseTool],
    memory: Optional[BaseMemory] = None,
    compressor: Optional[BaseCompressor] = None,
    max_iterations: int = 50,
    max_context_tokens: int = 16000,
    system_instructions: Optional[str] = None,
    # 🆕 v0.0.8 parameters
    hooks: Optional[List[LifecycleHook]] = None,
    event_journal: Optional[EventJournal] = None,
    context_debugger: Optional[ContextDebugger] = None,
    thread_id: Optional[str] = None,
)
```

### Methods

#### `async tt(messages, turn_state, context, frame) -> AsyncGenerator[AgentEvent]`

Tail-recursive control loop (core execution method).

```python
from loom.core.turn_state import TurnState
from loom.core.execution_context import ExecutionContext
from loom.core.types import Message

turn_state = TurnState.initial(max_iterations=10)
context = ExecutionContext.create()
messages = [Message(role="user", content="Hello")]

async for event in executor.tt(messages, turn_state, context):
    if event.type == AgentEventType.AGENT_FINISH:
        print(f"Done: {event.content}")
```

#### `async execute(user_input, cancel_token, correlation_id) -> str`

High-level execution wrapper.

```python
result = await executor.execute(
    user_input="Search for Python docs",
    cancel_token=None,
    correlation_id="req-123"
)
```

#### 🆕 `async resume(thread_id, journal, cancel_token, correlation_id) -> AsyncGenerator[AgentEvent]`

**Crash recovery** - Resume from interruption.

```python
# After crash, resume execution
async for event in executor.resume(thread_id="session-123"):
    if event.type == AgentEventType.PHASE_START and event.phase == "resume":
        print("📼 Replaying events...")
    elif event.type == AgentEventType.AGENT_FINISH:
        print(f"✅ Recovered: {event.content}")
```

---

## Tool API

Tool definition remains unchanged from v0.0.7.

### @tool Decorator

```python
from loom import tool

@tool(description="Search for information")
async def search(query: str) -> str:
    return f"Found results for: {query}"
```

See [v0.0.7 documentation](USAGE_GUIDE_V0_0_5.md#tools) for details.

---

## LLM API

LLM configuration remains unchanged from v0.0.7.

### OpenAI

```python
from loom.builtin.llms import OpenAILLM

llm = OpenAILLM(
    api_key="sk-...",
    model="gpt-4",
    temperature=0.7
)
```

### Anthropic

```python
from loom.builtin.llms import AnthropicLLM

llm = AnthropicLLM(
    api_key="sk-ant-...",
    model="claude-3-opus-20240229"
)
```

---

## Memory API

Memory API remains unchanged from v0.0.7.

### InMemoryMemory

```python
from loom.builtin.memory import InMemoryMemory

memory = InMemoryMemory()
```

### PersistentMemory

```python
from loom.builtin.memory import PersistentMemory

memory = PersistentMemory(
    persist_dir=".loom",
    session_id="session-123"
)
```

---

## Event Types

### AgentEventType

```python
from loom.core.events import AgentEventType

AgentEventType.ITERATION_START
AgentEventType.LLM_START
AgentEventType.LLM_DELTA
AgentEventType.LLM_COMPLETE
AgentEventType.LLM_TOOL_CALLS
AgentEventType.TOOL_RESULT
AgentEventType.TOOL_ERROR
AgentEventType.TOOL_CALLS_COMPLETE
AgentEventType.AGENT_FINISH
AgentEventType.MAX_ITERATIONS_REACHED
AgentEventType.EXECUTION_CANCELLED
AgentEventType.RECURSION
AgentEventType.RECURSION_TERMINATED
AgentEventType.COMPRESSION_APPLIED
AgentEventType.PHASE_START
AgentEventType.PHASE_END
AgentEventType.ERROR
```

---

## Migration from v0.0.7

**No Breaking Changes** - v0.0.8 is fully backward compatible.

### To Use New Features

1. **Add Event Sourcing**:
   ```python
   # OLD (v0.0.7)
   agent(provider="openai", model="gpt-4", tools=tools)

   # NEW (v0.0.8)
   agent(
       provider="openai", model="gpt-4", tools=tools,
       enable_persistence=True,  # 🆕
       journal_path=Path("./logs")  # 🆕
   )
   ```

2. **Add Lifecycle Hooks**:
   ```python
   from loom.core.lifecycle_hooks import LoggingHook, MetricsHook

   agent(
       provider="openai", model="gpt-4", tools=tools,
       hooks=[LoggingHook(), MetricsHook()]  # 🆕
   )
   ```

3. **Enable Context Debugging**:
   ```python
   from loom.core import ContextDebugger

   debugger = ContextDebugger(enable_auto_export=True)
   agent(
       provider="openai", model="gpt-4", tools=tools,
       context_debugger=debugger  # 🆕
   )
   ```

---

## Best Practices

### Development

```python
# Minimal setup for development
agent(provider="openai", model="gpt-4", tools=tools)
```

### Testing

```python
# Enable metrics for testing
from loom.core.lifecycle_hooks import MetricsHook

metrics_hook = MetricsHook()
agent(
    provider="openai", model="gpt-4", tools=tools,
    hooks=[metrics_hook]
)
# Check metrics after test
```

### Production

```python
# Full feature set
from loom.core import ContextDebugger
from loom.core.lifecycle_hooks import LoggingHook, MetricsHook, HITLHook
from pathlib import Path

debugger = ContextDebugger(enable_auto_export=True)

agent(
    provider="openai", model="gpt-4", tools=production_tools,
    system_instructions="...",
    enable_persistence=True,
    journal_path=Path("/var/log/loom"),
    hooks=[
        HITLHook(dangerous_tools=["delete_file"]),
        LoggingHook(verbose=False),
        MetricsHook()
    ],
    context_debugger=debugger,
    thread_id=session_id,
    max_iterations=100,
    max_context_tokens=32000
)
```

---

## Additional Resources

- **Quick Start Guide**: [docs/QUICKSTART_v0_0_8.md](QUICKSTART_v0_0_8.md)
- **Architecture Details**: [docs/ARCHITECTURE_REFACTOR.md](ARCHITECTURE_REFACTOR.md)
- **Complete Examples**: [examples/integration_example.py](../examples/integration_example.py)
- **Changelog**: [CHANGELOG.md](../CHANGELOG.md)

---

**Loom Agent v0.0.8 - The Stateful Recursive Agent Framework**
