# loom-agent v0.0.8 - Recursive State Machine 🎉

Major architectural upgrade from "implicit recursion framework" to production-ready **Recursive State Machine (RSM)**.

## 🌟 Key Features

- 🎬 **Event Sourcing** - Complete execution history with crash recovery
- 🪝 **Lifecycle Hooks** - 9 interception points for elegant control flow
- 🛡️ **HITL Support** - Human-in-the-Loop for dangerous operations
- 🔄 **Crash Recovery** - Resume from any interruption
- 🐛 **Context Debugger** - Transparent context management decisions
- 📊 **Execution Visualizer** - Flame graph visualization of recursive execution
- 🎯 **Strategy Upgrade** - Replay old events with new strategies (unique capability!)

## 📊 vs LangGraph

loom-agent v0.0.8 offers unique advantages over LangGraph:

| Capability | LangGraph | loom-agent 0.0.8 | Advantage |
|------------|-----------|------------------|-----------|
| **Persistence** | Static snapshots | Event Sourcing | 🟢 **loom** |
| **Strategy Upgrade** | ❌ Not supported | ✅ Replay with new strategy | 🟢 **loom (unique)** |
| **HITL** | `interrupt_before` API | LifecycleHooks + InterruptException | 🟢 **loom** |
| **Context Governance** | Simple dict | Context Fabric + ContextDebugger | 🟢 **loom (unique)** |
| **Visualization** | DAG flowchart | Flame graph (time+depth) | 🟡 Different strengths |
| **Code Simplicity** | Explicit graph edges | Hook injection | 🟢 **loom** |

## 📦 Installation

```bash
pip install loom-agent==0.0.8
```

## 📚 Documentation

- [Quick Start Guide](docs/QUICKSTART_v0_0_8.md)
- [API Reference](docs/API_REFERENCE_v0_0_8.md)
- [Architecture Details](docs/ARCHITECTURE_REFACTOR.md)
- [Complete Changelog](CHANGELOG.md)

## 🚀 What's New

### Core Components (~3,500 lines)

- **ExecutionFrame** - Immutable execution stack frame with parent-child linking
- **EventJournal** - Append-only event log for complete execution history
- **StateReconstructor** - Time travel debugging and state reconstruction
- **LifecycleHooks** - 9 hook points for elegant control flow
- **ContextDebugger** - Transparent context management decisions
- **ExecutionVisualizer** - CLI visualization as flame graph/timeline

### High-Level API

```python
from loom import agent
from loom.core.lifecycle_hooks import LoggingHook, MetricsHook, HITLHook
from pathlib import Path

# Enable persistence and hooks
my_agent = agent(
    provider="openai",
    model="gpt-4",
    tools=tools,
    enable_persistence=True,  # 🆕 Auto-enable event journal
    journal_path=Path("./logs"),  # 🆕 Custom storage path
    hooks=[  # 🆕 Lifecycle hooks
        LoggingHook(verbose=True),
        MetricsHook(),
        HITLHook(dangerous_tools=["delete_file"])
    ],
)

# Crash recovery
from loom.core import AgentExecutor, EventJournal

executor = AgentExecutor(
    llm=llm,
    tools=tools,
    event_journal=EventJournal(Path("./logs"))
)

# Resume from crash
async for event in executor.resume(thread_id="user-123"):
    if event.type == AgentEventType.AGENT_FINISH:
        print(f"✅ Recovered: {event.content}")
```

## 🔗 Links

- **PyPI**: https://pypi.org/project/loom-agent/0.0.8/
- **GitHub**: https://github.com/kongusen/loom-agent
- **Examples**: [Integration Example](examples/integration_example.py)

## 📝 Full Changelog

See [CHANGELOG.md](CHANGELOG.md) for complete details.

---

**Full Changelog**: https://github.com/kongusen/loom-agent/compare/v0.0.7...v0.0.8

