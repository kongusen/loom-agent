# 🎉 loom-agent v0.1.0 - Major Architecture Overhaul

**Release Date**: December 10, 2024

> ⚠️ **IMPORTANT: This is a major breaking release with significant architectural changes**
>
> v0.1.0 includes a complete redesign of the LLM interface and Agent API for better simplicity and consistency. Please read the [Migration Guide](docs/MIGRATION_GUIDE_V0_1.md) before upgrading.
>
> **Key Breaking Changes:**
> - LLM interface: 4 methods → 1 unified `stream()` method
> - Agent API: Multiple streaming methods → single `execute()` method
> - Event system: `StreamEvent` removed → unified `LLMEvent` + `AgentEvent`
> - LLM implementation: ABC inheritance → Protocol-based (no inheritance needed)

We're thrilled to announce **loom-agent v0.1.0**, a groundbreaking release featuring:

1. **🏗️ Core Architecture Redesign** - Simplified, unified APIs for LLM and Agent interfaces
2. **🤝 Multi-Agent Collaboration** - Enterprise-grade Crew system competing with CrewAI and AutoGen
3. **🔌 Tool Plugin Ecosystem** - Extensible plugin architecture for custom tools

This release maintains our unique **event sourcing** and **crash recovery** advantages while dramatically improving developer experience.

---

## 🚀 What's New

### 🤝 Crew Multi-Agent Collaboration System

Build production-ready multi-agent teams with ease:

```python
from loom.crew import Crew, Role, Task, OrchestrationPlan, OrchestrationMode

# Define roles
roles = [
    Role(name="researcher", goal="Gather information", tools=["read_file", "grep"]),
    Role(name="developer", goal="Write code", tools=["write_file", "edit_file"]),
    Role(name="qa_engineer", goal="Test code", tools=["bash", "read_file"]),
]

# Create crew
crew = Crew(roles=roles, llm=llm)

# Define tasks
tasks = [
    Task(id="research", assigned_role="researcher", prompt="Research OAuth 2.0 best practices"),
    Task(id="implement", assigned_role="developer", dependencies=["research"], prompt="Implement OAuth"),
    Task(id="test", assigned_role="qa_engineer", dependencies=["implement"], prompt="Test OAuth implementation"),
]

# Execute with orchestration
plan = OrchestrationPlan(tasks=tasks, mode=OrchestrationMode.SEQUENTIAL)
results = await crew.kickoff(plan)
```

**Features**:
- ✅ **6 Built-in Roles**: manager, researcher, developer, qa_engineer, analyst, writer
- ✅ **4 Orchestration Modes**: Sequential, Parallel, Conditional, Hierarchical
- ✅ **Inter-Agent Communication**: MessageBus + SharedState for coordination
- ✅ **Task Delegation**: Manager agents can delegate to team members
- ✅ **Dependency Management**: Automatic topological sorting
- ✅ **106 Tests**: Comprehensive test coverage with 100% pass rate

### 🔌 Tool Plugin System

Extend loom-agent with custom tools using a simple plugin architecture:

```python
from loom.plugins import ToolPluginManager

# Install plugin
manager = ToolPluginManager()
await manager.install_from_file("my_plugin.py", enable=True)

# Use tool
tool = manager.get_tool("my_tool")
result = await tool.run(param="value")
```

**Create plugins in minutes**:

```python
from pydantic import BaseModel, Field
from loom.interfaces.tool import BaseTool
from loom.plugins import ToolPluginMetadata

# Define metadata
PLUGIN_METADATA = ToolPluginMetadata(
    name="my-plugin",
    version="1.0.0",
    author="Your Name",
    description="My custom plugin"
)

# Define tool
class MyTool(BaseTool):
    name = "my_tool"
    description = "My custom tool"

    async def run(self, param: str, **kwargs) -> str:
        return f"Processed: {param}"
```

**Features**:
- ✅ **Dynamic Loading**: Load plugins from files or modules
- ✅ **Lifecycle Management**: LOADED → ENABLED → DISABLED states
- ✅ **Version Control**: Semantic versioning and dependency management
- ✅ **Search & Discovery**: Find plugins by tag, author, or name
- ✅ **35 Tests**: Complete test coverage

### 📚 Comprehensive Documentation

- **Bilingual README**: Complete documentation in both Chinese and English (3,000+ lines total)
- **Crew System Guide**: `docs/CREW_SYSTEM.md` with examples and best practices
- **Plugin System Guide**: `docs/TOOL_PLUGIN_SYSTEM.md` with tutorials
- **40+ Code Examples**: Progressive learning path (30s → 5min → 10min)

---

## 🎯 Key Features

### Core Framework (from v0.0.8)

- ✅ **Event Sourcing**: Complete execution history with event replay
- ✅ **Crash Recovery**: Resume from any breakpoint automatically
- ✅ **Lifecycle Hooks**: 9 hook points for custom logic injection
- ✅ **HITL Support**: Human-in-the-Loop for dangerous operations
- ✅ **Context Debugging**: Understand context inclusion/exclusion decisions
- ✅ **Recursive State Machine**: Natural tt() recursion pattern

### New in v0.1.0

- ✅ **Multi-Agent Crews**: CrewAI/AutoGen-level collaboration
- ✅ **Tool Plugins**: Extensible plugin ecosystem
- ✅ **4 Orchestration Modes**: Flexible task execution patterns
- ✅ **Inter-Agent Communication**: MessageBus and SharedState
- ✅ **Task Delegation**: Manager-driven workflows
- ✅ **Complete Tests**: 141 total tests (106 crew + 35 plugins)

---

## 📊 Framework Comparison

| Feature | LangGraph | AutoGen | CrewAI | **loom-agent v0.1.0** |
|---------|-----------|---------|--------|----------------------|
| **Event Sourcing** | ❌ | ❌ | ❌ | ✅ Complete |
| **Crash Recovery** | ⚠️ Checkpointing | ❌ | ❌ | ✅ Event replay |
| **Multi-Agent** | ❌ | ✅ | ✅ | ✅ Crew system |
| **Orchestration Modes** | Basic | Basic | Basic | ✅ 4 modes |
| **Tool Plugins** | ❌ | ❌ | ❌ | ✅ Complete system |
| **HITL** | interrupt_before | ❌ | ❌ | ✅ Lifecycle hooks |
| **Context Debugging** | ❌ | ❌ | ❌ | ✅ ContextDebugger |
| **Plugin Ecosystem** | ❌ | ❌ | ❌ | ✅ Dynamic loading |

---

## 📦 Installation

### Basic Installation

```bash
pip install loom-agent==0.1.0
```

### With OpenAI Support

```bash
pip install loom-agent[openai]==0.1.0
```

### Full Installation

```bash
pip install loom-agent[all]==0.1.0
```

---

## 🚀 Quick Start

### 30 Seconds - Basic Agent

```python
import asyncio
from loom import agent

async def main():
    my_agent = agent(
        provider="openai",
        model="gpt-4",
        system_instructions="You are a helpful assistant."
    )

    result = await my_agent.run("What is the weather in San Francisco?")
    print(result)

asyncio.run(main())
```

### 5 Minutes - Agent with Tools

```python
from loom import agent
from loom.builtin.tools import ReadFileTool, GlobTool, GrepTool

code_agent = agent(
    provider="openai",
    model="gpt-4",
    tools=[ReadFileTool(), GlobTool(), GrepTool()],
    system_instructions="You are a code analysis expert."
)

result = await code_agent.run(
    "Find all TODO comments in Python files and summarize them"
)
print(result)
```

### 10 Minutes - Production Setup with HITL

```python
from pathlib import Path
from loom import agent
from loom.core.lifecycle_hooks import HITLHook, LoggingHook
from loom.builtin.tools import WriteFileTool, BashTool

hitl_hook = HITLHook(
    dangerous_tools=["bash", "write_file"],
    ask_user_callback=lambda msg: input(f"⚠️  {msg}\nAllow? (y/n): ") == "y"
)

production_agent = agent(
    provider="openai",
    model="gpt-4",
    tools=[WriteFileTool(), BashTool()],
    enable_persistence=True,
    journal_path=Path("./logs"),
    hooks=[hitl_hook, LoggingHook()],
    thread_id="user-session-123"
)

result = await production_agent.run("Create a backup script and test it")
```

---

## 🆙 Upgrade Guide

### From v0.0.9 to v0.1.0

**No Breaking Changes** - v0.1.0 is fully backward compatible. All new features are opt-in.

**Existing code continues to work**:

```python
# Your existing code works unchanged
from loom import agent

my_agent = agent(provider="openai", model="gpt-4")
result = await my_agent.run("Hello")
```

**To use new Crew features**:

```python
from loom.crew import Crew, Role, Task, OrchestrationPlan, OrchestrationMode

# See examples above
```

**To use Plugin system**:

```python
from loom.plugins import ToolPluginManager

# See examples above
```

---

## 📈 Statistics

- **New Code**: ~3,200 lines (Crew: ~2,000, Plugins: ~1,200)
- **Test Code**: ~1,200 lines (141 tests total)
- **Documentation**: ~3,500 lines
- **Examples**: ~1,200 lines
- **Total Addition**: ~9,100 lines of production-ready code

---

## 📚 Documentation

- **Chinese README**: [README.md](https://github.com/kongusen/loom-agent/blob/main/README.md)
- **English README**: [README_EN.md](https://github.com/kongusen/loom-agent/blob/main/README_EN.md)
- **Crew System Guide**: [docs/CREW_SYSTEM.md](https://github.com/kongusen/loom-agent/blob/main/docs/CREW_SYSTEM.md)
- **Plugin System Guide**: [docs/TOOL_PLUGIN_SYSTEM.md](https://github.com/kongusen/loom-agent/blob/main/docs/TOOL_PLUGIN_SYSTEM.md)
- **Architecture**: [docs/ARCHITECTURE_REFACTOR.md](https://github.com/kongusen/loom-agent/blob/main/docs/ARCHITECTURE_REFACTOR.md)
- **Full Changelog**: [CHANGELOG.md](https://github.com/kongusen/loom-agent/blob/main/CHANGELOG.md)

---

## 🎓 Examples

- **Integration Example**: [examples/integration_example.py](https://github.com/kongusen/loom-agent/blob/main/examples/integration_example.py)
- **Crew Demo**: [examples/crew_demo.py](https://github.com/kongusen/loom-agent/blob/main/examples/crew_demo.py)
- **Plugin Demo**: [examples/plugin_demo.py](https://github.com/kongusen/loom-agent/blob/main/examples/plugin_demo.py)
- **Example Plugins**: [examples/tool_plugins/](https://github.com/kongusen/loom-agent/tree/main/examples/tool_plugins)

---

## 🔗 Links

- **GitHub**: https://github.com/kongusen/loom-agent
- **PyPI**: https://pypi.org/project/loom-agent/
- **Issues**: https://github.com/kongusen/loom-agent/issues
- **Discussions**: https://github.com/kongusen/loom-agent/discussions

---

## 🙏 Contributors

- **kongusen** - Framework architecture and implementation
- **Community** - Feature requests, testing, and feedback

---

## 🗺️ What's Next (v0.2.0)

- 📊 Web UI for real-time monitoring
- 🎨 Enhanced visualization (execution tree, flame graphs)
- 🌐 Distributed execution support
- 💾 Multi-backend storage (PostgreSQL, Redis)
- 📈 Performance benchmarking

---

## ⭐ Star Us!

If loom-agent helps your project, please give us a star! ⭐

**Built with ❤️ for reliable, stateful AI Agents**

---

**Event Sourcing** | **Lifecycle Hooks** | **HITL** | **Crash Recovery** | **Context Debugger** | **Crew System** | **Plugin System**
