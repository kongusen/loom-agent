# 🧵 Loom Agent

<div align="center">

**Enterprise-Grade Recursive State Machine Agent Framework**

**The Stateful Recursive Agent Framework with Event Sourcing & Multi-Agent Collaboration**

[![PyPI](https://img.shields.io/pypi/v/loom-agent.svg)](https://pypi.org/project/loom-agent/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-106%2B%20passing-brightgreen.svg)](tests/)

[中文文档](README.md) | **English**

[Quick Start](#-quick-start) | [Core Mechanisms](#-core-mechanisms) | [Multi-Agent Collaboration](#-crew-multi-agent-collaboration-system) | [Plugin System](#-tool-plugin-system) | [Documentation](#-documentation)

</div>

---

## 🎯 What is Loom Agent?

Loom Agent is an AI Agent framework based on **Recursive State Machine (RSM)** and **Event Sourcing**, designed for building **production-grade, reliable, and observable** complex Agent applications.

### 🌟 Why Choose Loom Agent?

Compared to traditional frameworks (like LangGraph, AutoGen, CrewAI), Loom Agent's unique advantages:

| Feature | LangGraph | AutoGen | CrewAI | **Loom Agent** |
|---------|-----------|---------|--------|----------------|
| **Core Architecture** | Graph State Machine | Conversational | Role Orchestration | **Recursive State Machine + Event Sourcing** |
| **Event Sourcing** | ❌ | ❌ | ❌ | ✅ **Complete Event Sourcing** |
| **Crash Recovery** | ⚠️ Checkpointing | ❌ | ❌ | ✅ **Resume from Any Breakpoint** |
| **Strategy Upgrade** | ❌ | ❌ | ❌ | ✅ **Inject New Strategy on Replay (Exclusive)** |
| **HITL** | Basic interrupt | ❌ | ❌ | ✅ **Complete Lifecycle Hooks** |
| **Context Debugging** | ❌ | ❌ | ❌ | ✅ **ContextDebugger (Exclusive)** |
| **Multi-Agent** | ❌ | ✅ | ✅ | ✅ **Crew System + 4 Orchestration Modes** |
| **Tool Orchestration** | Basic | Basic | Basic | ✅ **Smart Parallel + Dependency Detection** |
| **Code Simplicity** | Explicit Wiring | Complex Config | Complex Config | ✅ **Hook Injection, Zero Wiring** |

**Positioning**: Loom Agent = **LangGraph's Reliability** + **AutoGen's Collaboration** + **Exclusive Event Sourcing**

---

## 📦 Installation

```bash
# Basic installation
pip install loom-agent

# With OpenAI support
pip install loom-agent[openai]

# Full installation (all optional dependencies)
pip install loom-agent[all]
```

**Requirements**: Python 3.11+

---

## 🚀 Quick Start

### 30 Seconds to Get Started

```python
import asyncio
from loom import agent

async def main():
    # Create Agent (auto-reads OPENAI_API_KEY from environment)
    my_agent = agent(
        provider="openai",
        model="gpt-4",
        system_instructions="You are a helpful assistant."
    )

    # Run
    result = await my_agent.run("What is the weather in San Francisco?")
    print(result)

asyncio.run(main())
```

### 5 Minutes Advanced: Agent with Tools

```python
from loom import agent
from loom.builtin.tools import ReadFileTool, GlobTool, GrepTool

# Create Agent with tools
code_agent = agent(
    provider="openai",
    model="gpt-4",
    tools=[ReadFileTool(), GlobTool(), GrepTool()],
    system_instructions="You are a code analysis expert."
)

# Execute complex task
result = await code_agent.run(
    "Find all TODO comments in Python files and summarize them"
)
print(result)
```

### 10 Minutes Advanced: Enable Persistence and HITL

```python
from pathlib import Path
from loom import agent
from loom.core.lifecycle_hooks import HITLHook, LoggingHook
from loom.builtin.tools import WriteFileTool, BashTool

# Define dangerous tools list
hitl_hook = HITLHook(
    dangerous_tools=["bash", "write_file"],
    ask_user_callback=lambda msg: input(f"⚠️  {msg}\nAllow? (y/n): ") == "y"
)

# Create production-grade Agent
production_agent = agent(
    provider="openai",
    model="gpt-4",
    tools=[WriteFileTool(), BashTool()],

    # 🔥 Key features
    enable_persistence=True,           # Event sourcing
    journal_path=Path("./logs"),       # Log storage
    hooks=[hitl_hook, LoggingHook()],  # Lifecycle hooks
    thread_id="user-session-123"       # Session ID
)

# Run (dangerous operations will pause for confirmation)
result = await production_agent.run(
    "Create a backup script and test it"
)
```

---

## 🏗️ Core Mechanisms

### 1. Recursive State Machine (RSM)

The core of Loom Agent is the **tt recursion loop** - a self-driving recursive execution engine.

#### How It Works

```python
async def tt(frame: ExecutionFrame) -> str:
    """
    tt = think-tool-think-tool...
    Recursive loop until task completion
    """
    # Phase 1: Assemble context
    messages = assemble_context(frame)

    # Phase 2: LLM inference
    response = await llm.generate(messages)

    # Phase 3: Decision
    if response.finish_reason == "stop":
        return response.content  # Complete

    # Phase 4: Execute tools
    tool_results = await execute_tools(response.tool_calls)

    # Phase 5: Recursion 🔥
    next_frame = frame.next_frame(tool_results)
    return await tt(next_frame)  # Recursive call
```

**Execution Flow**:

```
User Input → tt(frame_0)
             ↓
    ┌────────────────────┐
    │ Assemble Context   │
    │ LLM Inference      │
    │ Check Completion?  │
    └────────────────────┘
             ↓
        Need Tools?
             ↓
    ┌────────────────────┐
    │ Execute Tools      │
    │ Generate Results   │
    └────────────────────┘
             ↓
    🔥 tt(frame_1) ← Recursion
             ↓
           Continue...
             ↓
         Return Result
```

**Advantages**:
- 🔄 **Natural Recursion** - No explicit state machine definition
- 📊 **Complete Execution Tree** - Each recursion is an ExecutionFrame
- 🐛 **Easy Debugging** - Clear execution stack
- 🛡️ **Loop Detection** - Automatic infinite recursion prevention

---

### 2. Event Sourcing

Loom Agent uses **Event Sourcing** rather than snapshots for state persistence.

#### Why Event Sourcing?

| Method | Checkpointing | Event Sourcing |
|--------|--------------|----------------|
| **Storage** | Periodic full state | Record all events |
| **Recovery** | Load latest snapshot | Replay event history |
| **Audit** | Only snapshot states | Complete execution history |
| **Strategy Upgrade** | ❌ Can't change past | ✅ Inject new strategy on replay |
| **Debugging** | Only snapshots | Complete time travel |

#### Event Types

```python
class AgentEventType(Enum):
    # Core events
    AGENT_START = "agent_start"           # Agent started
    AGENT_FINISH = "agent_finish"         # Agent finished

    # LLM events
    LLM_DELTA = "llm_delta"               # LLM streaming output
    LLM_COMPLETE = "llm_complete"         # LLM completed

    # Tool events
    TOOL_CALL = "tool_call"               # Tool invocation
    TOOL_RESULT = "tool_result"           # Tool result

    # State events
    COMPRESSION_APPLIED = "compression"   # Context compression
    EXECUTION_CANCELLED = "cancelled"     # HITL interruption

    # Error events
    ERROR = "error"                       # Error
```

#### Usage Example

```python
from loom.core import EventJournal
from pathlib import Path

# Create event journal
journal = EventJournal(storage_path=Path("./logs"))

# Create Agent (automatically logs all events)
my_agent = agent(
    llm=llm,
    tools=tools,
    event_journal=journal,
    thread_id="user-123"
)

# Execute task (all events auto-logged)
await my_agent.run("Analyze this codebase")

# Replay events
events = await journal.replay(thread_id="user-123")
print(f"Recorded {len(events)} events")

# Filter by type
tool_events = [e for e in events if e.type == AgentEventType.TOOL_RESULT]
print(f"Executed {len(tool_events)} tools")
```

---

### 3. Lifecycle Hooks

Loom Agent provides **9 hook points** for injecting custom logic at critical execution points.

#### Hook Points

```python
class LifecycleHook:
    # 1. Before iteration start
    async def before_iteration_start(self, frame: ExecutionFrame) -> Optional[dict]:
        """Called before new iteration starts"""
        pass

    # 2. Before context assembly
    async def before_context_assembly(self, frame: ExecutionFrame) -> Optional[dict]:
        """Called before assembling context"""
        pass

    # 3. After context assembly
    async def after_context_assembly(self, frame: ExecutionFrame, messages: list) -> Optional[dict]:
        """Called after assembling context"""
        pass

    # 4. Before LLM call
    async def before_llm_call(self, frame: ExecutionFrame, messages: list) -> Optional[dict]:
        """Called before calling LLM"""
        pass

    # 5. After LLM response
    async def after_llm_response(self, frame: ExecutionFrame, response: dict) -> Optional[dict]:
        """Called after LLM responds"""
        pass

    # 6. Before tool execution 🔥 HITL key point
    async def before_tool_execution(self, frame: ExecutionFrame, tool_call: dict) -> Optional[dict]:
        """Called before executing tool - HITL interception point"""
        pass

    # 7. After tool execution
    async def after_tool_execution(self, frame: ExecutionFrame, tool_result: dict) -> Optional[dict]:
        """Called after tool execution"""
        pass

    # 8. Before recursion
    async def before_recursion(self, frame: ExecutionFrame, next_frame: ExecutionFrame) -> Optional[dict]:
        """Called before recursive call"""
        pass

    # 9. After iteration end
    async def after_iteration_end(self, frame: ExecutionFrame, result: Any) -> Optional[dict]:
        """Called at iteration end"""
        pass
```

#### Custom Hook Example

```python
from loom.core.lifecycle_hooks import LifecycleHook

class MetricsHook(LifecycleHook):
    """Hook for collecting execution metrics"""

    def __init__(self):
        self.tool_usage = {}
        self.llm_calls = 0
        self.total_tokens = 0

    async def before_llm_call(self, frame, messages):
        self.llm_calls += 1
        return None

    async def after_llm_response(self, frame, response):
        self.total_tokens += response.get("usage", {}).get("total_tokens", 0)
        return None

    async def after_tool_execution(self, frame, tool_result):
        tool_name = tool_result["tool_name"]
        self.tool_usage[tool_name] = self.tool_usage.get(tool_name, 0) + 1
        return None

    def get_report(self):
        return {
            "llm_calls": self.llm_calls,
            "total_tokens": self.total_tokens,
            "tool_usage": self.tool_usage
        }

# Usage
metrics = MetricsHook()

my_agent = agent(
    llm=llm,
    tools=tools,
    hooks=[metrics]  # Inject hook
)

await my_agent.run("Complex task")

# Get metrics
print(metrics.get_report())
# {
#   "llm_calls": 5,
#   "total_tokens": 2500,
#   "tool_usage": {"read_file": 3, "grep": 2}
# }
```

#### Built-in Hooks

##### HITLHook - Human-in-the-Loop

```python
from loom.core.lifecycle_hooks import HITLHook

# Create HITL hook
hitl = HITLHook(
    dangerous_tools=["delete_file", "bash", "send_email"],
    ask_user_callback=lambda msg: input(f"{msg} (y/n): ") == "y"
)

my_agent = agent(
    llm=llm,
    tools=all_tools,
    hooks=[hitl]
)

# Execute (dangerous tools will auto-pause)
await my_agent.run("Clean up old files and send report")
# ⏸️  Output: "Allow delete_file with args {'path': '/old'}? (y/n):"
```

##### LoggingHook - Logging

```python
from loom.core.lifecycle_hooks import LoggingHook

logging_hook = LoggingHook(
    log_level="INFO",
    log_file=Path("./agent.log")
)

my_agent = agent(
    llm=llm,
    tools=tools,
    hooks=[logging_hook]
)
```

---

### 4. ExecutionFrame (Execution Stack Frame)

Each recursive call creates a new `ExecutionFrame`, forming an **execution tree**.

#### ExecutionFrame Structure

```python
@dataclass
class ExecutionFrame:
    """
    Immutable execution stack frame
    """
    # Identity
    id: str                              # Frame ID
    depth: int                           # Recursion depth
    parent_id: Optional[str]             # Parent frame ID
    thread_id: str                       # Thread ID

    # State
    history: List[dict]                  # Conversation history
    context_fabric: dict                 # Context fabric
    tool_results_buffer: List[dict]      # Tool results buffer

    # Metadata
    created_at: float                    # Creation time
    metadata: dict                       # Custom metadata

    def next_frame(self, tool_results: List[dict]) -> "ExecutionFrame":
        """Create next frame (recursion)"""
        return ExecutionFrame(
            id=generate_id(),
            depth=self.depth + 1,
            parent_id=self.id,
            thread_id=self.thread_id,
            history=self.history + [tool_results_to_messages(tool_results)],
            context_fabric=self.context_fabric.copy(),
            tool_results_buffer=tool_results,
            created_at=time.time(),
            metadata=self.metadata.copy()
        )
```

#### Execution Tree Example

```
frame_0 (depth=0) - "Analyze codebase"
  │
  ├─ tool_call: glob("**.py")
  │
  └─ frame_1 (depth=1) - [tool_results]
      │
      ├─ tool_call: read_file("main.py")
      │
      └─ frame_2 (depth=2) - [tool_results]
          │
          ├─ tool_call: grep("TODO")
          │
          └─ frame_3 (depth=3) - [tool_results]
              │
              └─ Return complete
```

**Advantages**:
- 📊 **Clear Execution Trace** - Each recursion level independent
- 🔍 **Easy Debugging** - View state at any depth
- 🛡️ **Immutability** - Parent state unaffected by child
- 🎯 **Precise Recovery** - Resume from any frame after crash

---

### 5. Context Management (Context Fabric)

Loom Agent uses **ContextFabric** to intelligently manage context and avoid token limits.

#### ContextFabric Architecture

```python
class ContextFabric:
    """
    Context fabric - manages various context components
    """
    components: Dict[str, ContextComponent]

    class ContextComponent:
        content: str         # Content
        priority: int        # Priority (0-100)
        tokens: int          # Token count
        strategy: str        # Compression strategy
        metadata: dict       # Metadata
```

#### Context Component Types

```python
from loom.core import ContextFabric

fabric = ContextFabric()

# 1. System instructions (highest priority)
fabric.add_system_instructions(
    content="You are a helpful assistant.",
    priority=100  # Never remove
)

# 2. RAG docs (high priority)
fabric.add_rag_docs(
    content="Documentation content...",
    priority=90
)

# 3. Tool results (medium priority)
fabric.add_tool_results(
    results=[...],
    priority=70
)

# 4. History (low priority)
fabric.add_history(
    messages=[...],
    priority=50
)

# 5. Temporary data (lowest priority)
fabric.add_scratch_pad(
    content="Temporary notes...",
    priority=30
)
```

#### Smart Compression

```python
from loom.core import ContextAssembler

assembler = ContextAssembler(
    max_tokens=4000,
    compression_strategies={
        "history": "summarize",      # Summarize history
        "tool_results": "truncate",   # Truncate tool results
        "scratch_pad": "drop"         # Drop scratch pad
    }
)

# Assemble context (auto-compress)
messages, metadata = assembler.assemble(fabric, frame)

# View compression stats
print(metadata["compression_stats"])
# {
#   "original_tokens": 6000,
#   "final_tokens": 3800,
#   "saved_tokens": 2200,
#   "components_dropped": ["scratch_pad"],
#   "components_compressed": ["history"]
# }
```

#### ContextDebugger - Context Debugger

Answers "**Why did LLM forget X?**"

```python
from loom.core import ContextDebugger

debugger = ContextDebugger(enable_auto_export=True)

my_agent = agent(
    llm=llm,
    tools=tools,
    context_debugger=debugger  # Enable debugger
)

# Execute task
await my_agent.run("Long complex task")

# View context decisions at iteration 5
print(debugger.explain_iteration(5))
# Output:
# ✅ Included Components:
#   - system_instructions (500 tokens, priority=100)
#   - rag_docs (2000 tokens, priority=90)
#   - history (1300 tokens, priority=50, compressed from 2500)
#
# ❌ Excluded Components:
#   - file_content.py (2500 tokens, priority=70)
#     Reason: Token limit exceeded, higher priority items took precedence
#
# 💡 Suggestion: Increase priority of 'file_content.py' to 85 to include it

# Track specific component
print(debugger.explain_component("file_content.py"))
# Component 'file_content.py' history:
#   Iteration 1-3: ✅ Included
#   Iteration 4-6: ❌ Excluded (token limit)
#   Iteration 7-9: ✅ Included (after compression)

# Generate full report
print(debugger.generate_summary())
```

---

### 6. Tool Orchestration

Loom Agent's **ToolOrchestrator** intelligently manages tool execution.

#### Tool Types

```python
from loom.interfaces.tool import BaseTool

class MyTool(BaseTool):
    name = "my_tool"
    description = "My custom tool"
    args_schema = MyToolInput

    # 🆕 Tool attributes
    is_read_only = True           # Read-only tool (can parallelize)
    category = "general"          # Category: general/destructive/network
    requires_confirmation = False # Requires confirmation

    async def run(self, **kwargs) -> str:
        # Tool implementation
        return "result"
```

#### Smart Parallel Execution

```python
from loom.core import ToolOrchestrator

orchestrator = ToolOrchestrator()

# Tool calls
tool_calls = [
    {"name": "read_file", "args": {"path": "a.py"}},  # Read-only
    {"name": "read_file", "args": {"path": "b.py"}},  # Read-only
    {"name": "write_file", "args": {"path": "c.py", "content": "..."}},  # Destructive
]

# Auto parallel/serial decision
results = await orchestrator.execute_batch(tool_calls, tools)

# Execution strategy:
# 1. Two read_file execute in parallel ✅
# 2. write_file waits for them to complete ✅
```

#### Dependency Detection

```python
# ToolOrchestrator automatically detects inter-tool dependencies

tool_calls = [
    {"name": "glob", "args": {"pattern": "**.py"}},
    {"name": "read_file", "args": {"path": "{glob_result[0]}"}},  # Depends on glob
]

# Auto serial execution:
# 1. glob executes first
# 2. Result injected into read_file parameters
# 3. read_file executes
```

---

### 7. Crash Recovery

Loom Agent supports resumption from **any breakpoint**.

#### Recovery Flow

```python
from loom.core import AgentExecutor, EventJournal
from pathlib import Path

# 1. Execution before crash
executor = AgentExecutor(
    llm=llm,
    tools=tools,
    event_journal=EventJournal(Path("./logs"))
)

try:
    await executor.execute("Long running task", thread_id="user-123")
except SystemExit:
    print("System crashed...")

# 2. Resume after restart
executor = AgentExecutor(
    llm=llm,
    tools=tools,
    event_journal=EventJournal(Path("./logs"))
)

# Resume from breakpoint (auto-replay event history)
async for event in executor.resume(thread_id="user-123"):
    if event.type == AgentEventType.AGENT_FINISH:
        print(f"✅ Resume complete: {event.content}")
```

#### How It Works

```
Before crash:
  Executed to iteration 5 → System crashed
  EventJournal recorded: [event_1, event_2, ..., event_5]

On resume:
  1. Read EventJournal
  2. Replay event history → Rebuild ExecutionFrame
  3. Continue from iteration 6
```

**Advantages**:
- 🛡️ **Production Reliability** - Server restart doesn't lose progress
- 💰 **Cost Savings** - Avoid duplicate LLM calls
- ⏱️ **User Experience** - Auto-resume after long task interruption
- 📊 **Complete Audit** - All execution history recorded

---

### 8. Unified Coordination Mode

Loom Agent provides **UnifiedCoordinator** for unified management of complex execution flows.

#### What is Unified Coordination?

Traditional approach has independent components; UnifiedCoordinator provides **centralized coordination**:

```
Traditional:
  LLM → Tools → Context → ... (each independent)

Unified Coordination:
  UnifiedCoordinator
      ├─ ContextAssembler
      ├─ ToolOrchestrator
      ├─ LifecycleHooks
      └─ EventJournal
```

#### Usage Example

```python
from loom.core import UnifiedCoordinator, ExecutionFrame

coordinator = UnifiedCoordinator(
    llm=llm,
    tools=tools,
    context_assembler=assembler,
    tool_orchestrator=orchestrator,
    hooks=[hitl_hook, metrics_hook],
    event_journal=journal
)

# Execute (all components work in coordination)
frame = ExecutionFrame.create(user_input="Task")
result = await coordinator.execute_iteration(frame)
```

---

## 🤝 Crew Multi-Agent Collaboration System

Loom Agent includes the **Crew system**, supporting CrewAI/AutoGen-level multi-agent collaboration.

### Core Concepts

```
Crew (Team)
  ├─ Role (role definition)
  ├─ Task (task)
  ├─ OrchestrationPlan (orchestration plan)
  ├─ MessageBus (message bus)
  └─ SharedState (shared state)
```

### Quick Start

```python
from loom.crew import Crew, Role, Task, OrchestrationPlan, OrchestrationMode

# 1. Define roles
roles = [
    Role(
        name="researcher",
        goal="Gather and analyze information",
        tools=["read_file", "grep", "web_search"],
        capabilities=["research", "analysis"]
    ),
    Role(
        name="developer",
        goal="Write and modify code",
        tools=["read_file", "write_file", "edit_file"],
        capabilities=["coding"]
    ),
    Role(
        name="qa_engineer",
        goal="Test and validate implementations",
        tools=["read_file", "bash"],
        capabilities=["testing"]
    )
]

# 2. Create team
crew = Crew(roles=roles, llm=llm)

# 3. Define tasks
tasks = [
    Task(
        id="research",
        description="Research OAuth 2.0",
        prompt="Research OAuth 2.0 best practices and security considerations",
        assigned_role="researcher",
        output_key="research_result"
    ),
    Task(
        id="implement",
        description="Implement OAuth",
        prompt="Implement OAuth 2.0 authentication based on research findings",
        assigned_role="developer",
        dependencies=["research"],  # Depends on research task
        output_key="code_result"
    ),
    Task(
        id="test",
        description="Test implementation",
        prompt="Test the OAuth implementation for security and functionality",
        assigned_role="qa_engineer",
        dependencies=["implement"]  # Depends on implementation task
    )
]

# 4. Create orchestration plan
plan = OrchestrationPlan(
    tasks=tasks,
    mode=OrchestrationMode.SEQUENTIAL  # Sequential execution
)

# 5. Execute
results = await crew.kickoff(plan)

print(results["research"])   # Research result
print(results["implement"])  # Implementation result
print(results["test"])       # Test result
```

### Orchestration Modes

#### 1. SEQUENTIAL - Sequential Execution

```python
plan = OrchestrationPlan(
    tasks=tasks,
    mode=OrchestrationMode.SEQUENTIAL
)

# Execution order: task1 → task2 → task3
```

#### 2. PARALLEL - Parallel Execution

```python
plan = OrchestrationPlan(
    tasks=[
        Task(id="research_oauth", ...),
        Task(id="research_jwt", ...),
        Task(id="research_saml", ...),  # Three research tasks in parallel
    ],
    mode=OrchestrationMode.PARALLEL,
    max_parallel=3
)

# Execution: Three tasks run concurrently
```

#### 3. CONDITIONAL - Conditional Execution

```python
from loom.crew import ConditionBuilder

tasks = [
    Task(
        id="check_security",
        description="Check security requirements",
        prompt="Analyze if OAuth is required",
        assigned_role="researcher",
        output_key="needs_oauth"
    ),
    Task(
        id="implement_oauth",
        description="Implement OAuth",
        prompt="Implement OAuth 2.0",
        assigned_role="developer",
        # 🔥 Condition: execute only when needed
        condition=ConditionBuilder.key_equals("needs_oauth", True)
    )
]

plan = OrchestrationPlan(tasks=tasks, mode=OrchestrationMode.CONDITIONAL)

# Execution: implement_oauth only executes if needs_oauth=True
```

#### 4. HIERARCHICAL - Hierarchical Coordination

```python
roles = [
    Role(
        name="manager",
        goal="Coordinate team and ensure task completion",
        tools=["delegate"],  # 🔥 Manager can delegate tasks
        delegation=True
    ),
    Role(name="researcher", ...),
    Role(name="developer", ...),
]

plan = OrchestrationPlan(
    tasks=tasks,
    mode=OrchestrationMode.HIERARCHICAL  # Manager coordinates execution
)

# Execution flow:
# 1. Manager analyzes tasks
# 2. Manager delegates to appropriate team members
# 3. Collects results and summarizes
```

### Inter-Agent Communication

#### MessageBus - Message Bus

```python
from loom.crew import MessageBus, AgentMessage, MessageType

# Create message bus
message_bus = MessageBus()

# Agent A sends message
await message_bus.publish(
    AgentMessage(
        from_agent="researcher",
        to_agent="developer",  # Point-to-point
        type=MessageType.NOTIFICATION,
        content="Found security vulnerability in OAuth implementation",
        thread_id="task-123"
    )
)

# Agent B subscribes to messages
def handle_message(msg: AgentMessage):
    print(f"Received from {msg.from_agent}: {msg.content}")

message_bus.subscribe("developer", handle_message)
```

#### SharedState - Shared State

```python
from loom.crew import SharedState

# Create shared state
shared_state = SharedState()

# Thread-safe read/write
await shared_state.set("oauth_config", {"client_id": "...", "secret": "..."})
config = await shared_state.get("oauth_config")

# Atomic update
await shared_state.update("counter", lambda x: (x or 0) + 1)
```

### Complete Example

See [examples/crew_demo.py](examples/crew_demo.py) for complete multi-agent collaboration examples, including:
- Code review workflow (Sequential)
- Parallel feature implementation (Parallel)
- Conditional task execution (Conditional)
- Manager coordination (Hierarchical)
- Inter-agent communication

---

## 🔌 Tool Plugin System

Loom Agent provides a **tool plugin system** supporting dynamic loading and management of custom tools.

### Quick Start

#### Create Plugin

Create file `weather_plugin.py`:

```python
from pydantic import BaseModel, Field
from loom.interfaces.tool import BaseTool
from loom.plugins import ToolPluginMetadata

# 1. Define plugin metadata
PLUGIN_METADATA = ToolPluginMetadata(
    name="weather-lookup",
    version="1.0.0",
    author="Your Name <you@example.com>",
    description="Weather lookup tool",
    tags=["weather", "data"],
)

# 2. Define tool input
class WeatherInput(BaseModel):
    location: str = Field(..., description="City name")
    units: str = Field("celsius", description="Temperature units")

# 3. Define tool
class WeatherTool(BaseTool):
    name = "weather"
    description = "Get current weather"
    args_schema = WeatherInput

    async def run(self, location: str, units: str = "celsius", **kwargs) -> str:
        # Tool implementation
        return f"Weather in {location}: 22°{units[0].upper()}"
```

#### Use Plugin

```python
from loom.plugins import ToolPluginManager

# Create plugin manager
manager = ToolPluginManager()

# Install plugin
await manager.install_from_file("weather_plugin.py", enable=True)

# Get tool
weather_tool = manager.get_tool("weather")

# Use tool
result = await weather_tool.run(location="Tokyo")
print(result)  # "Weather in Tokyo: 22°C"

# Use in Agent
my_agent = agent(
    llm=llm,
    tools=[weather_tool]
)
```

### Plugin Management

```python
from loom.plugins import ToolPluginManager, PluginStatus

manager = ToolPluginManager(plugin_dir="./plugins")

# Discover and install all plugins
plugins = await manager.discover_and_install("./plugins", enable=True)

# List installed plugins
for plugin in manager.list_installed():
    print(f"{plugin.metadata.name} v{plugin.metadata.version}")

# Search plugins
finance_plugins = manager.registry.search_by_tag("finance")

# Enable/disable
manager.disable("weather-lookup")
manager.enable("weather-lookup")

# Uninstall
manager.uninstall("weather-lookup")

# Get statistics
stats = manager.get_stats()
print(f"Total plugins: {stats['total_plugins']}")
print(f"Enabled: {stats['enabled']}")
```

### Built-in Example Plugins

```python
from examples.tool_plugins.example_plugins import EXAMPLE_PLUGINS

# 3 example plugins:
# 1. WeatherTool - Weather lookup
# 2. CurrencyConverterTool - Currency conversion
# 3. SentimentAnalysisTool - Sentiment analysis

for plugin in EXAMPLE_PLUGINS:
    manager.registry.register(plugin)
    plugin.enable()
```

Detailed documentation: [docs/TOOL_PLUGIN_SYSTEM.md](docs/TOOL_PLUGIN_SYSTEM.md)

---

## 📊 Comparison with Other Frameworks

### vs LangGraph

| Feature | LangGraph | Loom Agent |
|---------|-----------|------------|
| **Core Abstraction** | Graph (nodes+edges) | Recursive State Machine |
| **Code Volume** | Explicit wiring required | Hook injection, zero wiring |
| **Persistence** | Static snapshots | Event Sourcing |
| **Strategy Upgrade** | ❌ | ✅ Inject new strategy on replay |
| **HITL** | interrupt_before | LifecycleHooks |
| **Context Debugging** | ❌ | ✅ ContextDebugger |
| **Best For** | Deterministic workflows | Exploratory complex tasks |

### vs AutoGen

| Feature | AutoGen | Loom Agent |
|---------|---------|------------|
| **Multi-Agent** | ✅ Conversational | ✅ Crew System |
| **Orchestration Modes** | Basic | 4 modes (Sequential/Parallel/Conditional/Hierarchical) |
| **Persistence** | ❌ | ✅ Event Sourcing |
| **Tool Orchestration** | Basic | Smart parallel + dependency detection |
| **Config Complexity** | High | Low |

### vs CrewAI

| Feature | CrewAI | Loom Agent |
|---------|--------|------------|
| **Role System** | ✅ | ✅ More flexible |
| **Task Orchestration** | ✅ | ✅ + Conditional logic |
| **Crash Recovery** | ❌ | ✅ |
| **Event Sourcing** | ❌ | ✅ |
| **Context Management** | Basic | ContextFabric + Debugger |

**Summary**: Loom Agent = **All framework advantages** + **Exclusive Event Sourcing**

---

## 📚 Documentation

### Core Documentation
- 📖 [Complete User Guide](docs/USAGE_GUIDE_V0_0_5.md)
- 🏗️ [Architecture Design](docs/ARCHITECTURE_REFACTOR.md)
- 🔧 [API Reference](docs/user/api-reference.md)

### System Documentation
- 🤝 [Crew Multi-Agent System](docs/CREW_SYSTEM.md)
- 🔌 [Tool Plugin System](docs/TOOL_PLUGIN_SYSTEM.md)
- 📊 [Context Fabric Deep Dive](docs/CONTEXT_FABRIC.md)

### Release Documentation
- ✅ [v0.0.8 Integration Complete](docs/INTEGRATION_COMPLETE.md)
- 📊 [Phase 5-8 Summary](docs/PHASE_5-8_IMPLEMENTATION_SUMMARY.md)
- 🚀 [Milestone Planning](docs/v0.1.0_MILESTONES.md)

---

## 🎯 Use Cases

### 1. Production Environment Agent

```python
# Enterprise-grade reliability Agent
production_agent = agent(
    provider="openai",
    model="gpt-4",
    tools=production_tools,

    # Reliability features
    enable_persistence=True,
    journal_path=Path("/var/log/loom"),

    # Security features
    hooks=[
        HITLHook(dangerous_tools=["delete", "execute"]),
        LoggingHook(),
        MetricsHook()
    ],

    # Performance config
    max_iterations=100,
    max_context_tokens=8000
)

# Auto-resume after crash
if crashed:
    async for event in production_agent.resume(thread_id=session_id):
        handle_event(event)
```

### 2. Code Review Workflow

```python
from loom.crew import Crew, Role, Task

# Create code review team
roles = [
    Role(name="architect", goal="Analyze structure", ...),
    Role(name="security", goal="Find vulnerabilities", ...),
    Role(name="writer", goal="Document findings", ...)
]

crew = Crew(roles=roles, llm=llm)

# Sequential review process
tasks = [
    Task(id="structure", assigned_role="architect", ...),
    Task(id="security", assigned_role="security", dependencies=["structure"]),
    Task(id="document", assigned_role="writer", dependencies=["security"])
]

plan = OrchestrationPlan(tasks=tasks, mode=OrchestrationMode.SEQUENTIAL)
results = await crew.kickoff(plan)
```

### 3. Research and Analysis

```python
# Enable full debugging
debugger = ContextDebugger(enable_auto_export=True)

research_agent = agent(
    llm=llm,
    tools=research_tools,
    context_debugger=debugger,
    enable_persistence=True
)

# Execute long-term research task
await research_agent.run("Research quantum computing applications")

# Analyze execution process
print(debugger.generate_summary())
print(debugger.explain_iteration(5))
```

### 4. Multi-Agent Collaborative Project

```python
# Create development team
team = Crew(
    roles=[
        Role(name="pm", goal="Plan and coordinate", delegation=True),
        Role(name="researcher", goal="Research solutions"),
        Role(name="developer", goal="Implement features"),
        Role(name="tester", goal="Test quality")
    ],
    llm=llm
)

# Hierarchical mode: PM coordinates team
plan = OrchestrationPlan(
    tasks=project_tasks,
    mode=OrchestrationMode.HIERARCHICAL
)

results = await team.kickoff(plan)
```

---

## 🧪 Testing

```bash
# Run all tests
pytest

# Run specific tests
pytest tests/unit/crew/ -v
pytest tests/unit/plugins/ -v

# Run with coverage
pytest --cov=loom --cov-report=html

# Run examples
python examples/integration_example.py
python examples/crew_demo.py
python examples/plugin_demo.py
```

**Test Status**:
- ✅ Crew System: 106 tests, 100% passing
- ✅ Plugin System: 35 tests, 100% passing
- ✅ Core Functions: 50+ tests passing

---

## 🗺️ Roadmap

### ✅ v0.0.8 (Completed)
- ✅ ExecutionFrame (execution stack frame)
- ✅ EventJournal (event sourcing)
- ✅ LifecycleHooks (9 hook points)
- ✅ HITL (Human-in-the-Loop)
- ✅ ContextDebugger (context debugging)
- ✅ Crash Recovery
- ✅ StateReconstructor (state reconstruction)

### ✅ v0.1.0 (Completed)
- ✅ Crew multi-agent collaboration system
  - ✅ Role system (6 built-in roles)
  - ✅ 4 orchestration modes (Sequential/Parallel/Conditional/Hierarchical)
  - ✅ Inter-agent communication (MessageBus + SharedState)
  - ✅ Delegation tool (DelegateTool)
  - ✅ Condition builder (ConditionBuilder)
  - ✅ Performance monitoring
- ✅ Tool plugin system
  - ✅ Plugin registry
  - ✅ Dynamic loader
  - ✅ Lifecycle management
  - ✅ 3 example plugins
- ✅ Complete bilingual documentation (Chinese + English)

### 🔜 v0.2.0 (Planned)
- 📊 Web UI (real-time monitoring Dashboard)
- 🎨 Enhanced visualization (execution tree, flame graphs)
- 🧪 MockLLMWithTools improvements
- 📈 Performance benchmarking
- 🌐 Distributed execution support
- 💾 Multi-backend storage (PostgreSQL, Redis)

### 🎯 v0.3.0 (Goals)
- 🔌 More plugins (LLM, Memory, Storage)
- 🌍 Multi-language support
- 📱 Mobile adaptation
- 🔐 Enterprise security features

---

## 💡 Best Practices

### 1. Always Enable Persistence (Production)

```python
# ✅ Recommended
agent(
    llm=llm,
    tools=tools,
    enable_persistence=True,
    journal_path=Path("./logs"),
    thread_id=session_id
)

# ❌ Not recommended (production)
agent(llm=llm, tools=tools)  # No persistence
```

### 2. Add HITL for Dangerous Tools

```python
# ✅ Recommended
hitl = HITLHook(dangerous_tools=["delete_file", "bash", "send_email"])

agent(llm=llm, tools=all_tools, hooks=[hitl])

# ❌ Not recommended
agent(llm=llm, tools=all_tools)  # No protection
```

### 3. Use ContextDebugger for Context Issues

```python
# ✅ Recommended
debugger = ContextDebugger(enable_auto_export=True)

agent(llm=llm, tools=tools, context_debugger=debugger)

# Analyze after execution
print(debugger.explain_iteration(5))
```

### 4. Use Appropriate Crew Orchestration Modes

```python
# ✅ Research tasks - Parallel
OrchestrationMode.PARALLEL

# ✅ Dependent workflows - Sequential
OrchestrationMode.SEQUENTIAL

# ✅ Conditional branches - Conditional
OrchestrationMode.CONDITIONAL

# ✅ Complex coordination - Hierarchical
OrchestrationMode.HIERARCHICAL
```

### 5. Monitoring and Logging

```python
# ✅ Recommended - Add monitoring hooks
agent(
    llm=llm,
    tools=tools,
    hooks=[
        LoggingHook(log_file=Path("./agent.log")),
        MetricsHook(),
        HITLHook(...)
    ]
)
```

---

## 🙏 Acknowledgments

Special thanks to:
- **Claude Code** - Inspiration for tt recursion pattern
- **LangGraph** - Graph state machine comparison reference
- **React Fiber** - ExecutionFrame design inspiration
- **Event Sourcing Community** - Event sourcing best practices
- **CrewAI & AutoGen** - Multi-agent collaboration reference
- Early users and contributors

---

## 📄 License

MIT License - See [LICENSE](LICENSE) file for details

---

## 🔗 Links

- **GitHub**: https://github.com/kongusen/loom-agent
- **PyPI**: https://pypi.org/project/loom-agent/
- **Documentation**: [docs/](docs/)
- **Examples**: [examples/](examples/)
- **Issues**: https://github.com/kongusen/loom-agent/issues

---

<div align="center">

**Built with ❤️ for reliable, stateful AI Agents**

### 🎬 Core Innovations

**Event Sourcing** | **Lifecycle Hooks** | **HITL** | **Crash Recovery** | **Context Debugger** | **Crew System** | **Plugin System**

---

### ⭐ If Loom Agent helps you, please give us a star!

[⭐ Star on GitHub](https://github.com/kongusen/loom-agent)

</div>
