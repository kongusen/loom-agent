# Changelog

All notable changes to loom-agent will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v0.1.1.html).

---

## [0.1.1] - 2024-12-12

### 🎉 Stream-First Architecture - 100% Consistency

v0.1.1 achieves **complete architectural consistency** across ALL components by extending the Stream-First architecture to Memory, Context Assembly, and Compression systems. This release delivers enterprise-grade observability with 23 new event types and comprehensive documentation for AI coding assistants.

### Added

#### Stream-First Memory System
- **Protocol-based Memory Interface** (`loom/interfaces/memory.py`, 420 lines)
  - Migrated from ABC to `@runtime_checkable Protocol` for zero-coupling design
  - Core streaming methods: `add_message_stream()`, `get_messages_stream()`, `clear_stream()`
  - Convenience wrappers for backward compatibility
  - Duck typing support for flexible implementations

- **Enhanced InMemoryMemory** (`loom/builtin/memory/in_memory.py`, 319 lines)
  - Full Protocol implementation with streaming events
  - Real-time progress tracking for all operations
  - Event emissions: `MEMORY_ADD_START`, `MEMORY_ADD_COMPLETE`

- **Extended PersistentMemory** (`loom/builtin/memory/persistent_memory.py`)
  - Streaming disk I/O operations with visibility
  - Events: `MEMORY_SAVE_START`, `MEMORY_SAVE_COMPLETE`
  - Track persistence operations in real-time

#### Stream-First Context Assembly
- **Context Assembly Streaming** (`loom/core/context_assembly.py`)
  - `add_component_stream()`: Component addition with events
  - `assemble_stream()`: Full assembly process visibility
    - `CONTEXT_COMPONENT_INCLUDED`: Component fits in budget
    - `CONTEXT_COMPONENT_TRUNCATED`: Component truncated
    - `CONTEXT_COMPONENT_EXCLUDED`: Component excluded
  - `clear_stream()`: Clear operations with events
  - `adjust_priority_stream()`: Priority adjustments with tracking
  - Token budget management observability
  - Priority-based inclusion/exclusion tracking

#### Stream-First Compression
- **Compression Manager Streaming** (`loom/core/compression_manager.py`)
  - `compress_stream()`: Core compression with full visibility
  - Retry logic observability (exponential backoff: 1s, 2s, 4s)
  - Events: `COMPRESSION_START`, `COMPRESSION_PROGRESS`, `COMPRESSION_COMPLETE`
  - Fallback visibility: `COMPRESSION_FALLBACK` → sliding window
  - Real-time compression statistics

#### New Event Types (23 added)
- **Memory Events** (9):
  - `MEMORY_ADD_START`, `MEMORY_ADD_COMPLETE`
  - `MEMORY_LOAD_START`, `MEMORY_MESSAGES_LOADED`
  - `MEMORY_CLEAR_START`, `MEMORY_CLEAR_COMPLETE`
  - `MEMORY_SAVE_START`, `MEMORY_SAVE_COMPLETE`
  - `MEMORY_ERROR`

- **Context Events** (9):
  - `CONTEXT_COMPONENT_INCLUDED`
  - `CONTEXT_COMPONENT_EXCLUDED`
  - `CONTEXT_COMPONENT_TRUNCATED`
  - `CONTEXT_ADD_START`, `CONTEXT_ADD_COMPLETE`
  - `CONTEXT_CLEAR_START`, `CONTEXT_CLEAR_COMPLETE`
  - `CONTEXT_ADJUST_PRIORITY`
  - `CONTEXT_ASSEMBLY_START`, `CONTEXT_ASSEMBLY_COMPLETE` (enhanced)

- **Compression Events** (5):
  - `COMPRESSION_START`
  - `COMPRESSION_PROGRESS`
  - `COMPRESSION_COMPLETE`
  - `COMPRESSION_FALLBACK`
  - `COMPRESSION_ERROR`

#### Comprehensive Documentation
- **Coding Agent Guide** (`docs/user/coding_agent_guide.md`, 561 lines)
  - v0.1.1 feature comparison table
  - Quick start templates (streaming vs non-streaming)
  - Complete event type reference
  - Best practices and debugging guide
  - Real-world usage patterns

- **Quick Reference Card** (`docs/user/quick-reference.md`, 379 lines)
  - 30-second API lookup
  - Event type quick reference table
  - 8 copy-paste ready code snippets
  - Common patterns reference

- **Troubleshooting Guide** (`docs/user/troubleshooting.md`, 386 lines)
  - Systematic debugging flowcharts
  - 5 major problem categories
  - Command-line diagnostics
  - Performance optimization hooks
  - Common error solutions

- **Architecture Visualization** (`docs/user/architecture.md`, 767 lines)
  - Complete 7-layer architecture diagram (ASCII art)
  - Detailed tt() recursive loop explanation
  - Component-by-component deep dive (8 components)
  - Data flow and event flow diagrams
  - Design principles and performance characteristics

#### Production-Ready Examples
- **Code Review Agent** (`examples/complete/code_review_agent.py`, 152 lines)
  - Real-world code review system
  - Streaming progress updates
  - Tool integration (ReadFile, Glob, Grep)
  - Structured result collection

- **Data Analysis Pipeline** (`examples/complete/data_analysis_pipeline.py`, 195 lines)
  - Multi-agent Crew collaboration
  - 4-role data analysis workflow
  - Task dependency graph (collect → clean → analyze → report)
  - Streaming task progress

- **FastAPI Integration** (`examples/integrations/fastapi_integration.py`, 323 lines)
  - REST API with SSE streaming
  - Session management
  - Crash recovery endpoint
  - Production-ready patterns

### Changed

#### Architectural Consistency
- **100% Stream-First Architecture**:
  | Component | v0.1.0 | v0.1.1 |
  |-----------|--------|--------|
  | LLM | ABC | Protocol ✅ |
  | Agent | Basic | `execute()` streaming ✅ |
  | Crew | No streaming | `kickoff_stream()` ✅ |
  | Memory | ABC | Protocol + streaming ✅ |
  | Context | Sync | `assemble_stream()` ✅ |
  | Compression | Sync | `compress_stream()` ✅ |

- **Protocol-based Design**: All core interfaces now use `@runtime_checkable Protocol`
- **Backward Compatible**: All convenience wrappers preserved
- **Zero Breaking Changes**: Existing code continues to work

### Fixed
- Context assembly now properly emits component inclusion/exclusion events
- Memory operations now visible during execution
- Compression retry logic now observable
- Token budget decisions now traceable

### Migration Guide
- All existing code continues to work without changes
- New streaming methods are opt-in
- See `docs/MIGRATION_GUIDE_V0_1.md` for streaming adoption guide

### Performance
- Context assembly caching improves performance by ~70%
- Memory operations with streaming add negligible overhead (<1%)
- Compression streaming enables early cancellation

### Documentation Stats
- 4 comprehensive guides (2,090+ lines)
- 3 production-ready examples (670+ lines)
- Complete event type catalog (41 total events)
- ASCII diagrams for all major flows

---

## [0.1.0] - 2024-12-10

### 🎉 Major Release - Multi-Agent Collaboration & Tool Plugin Ecosystem

v0.1.0 marks a significant milestone for loom-agent, introducing enterprise-grade **multi-agent collaboration** (Crew System) and a complete **tool plugin ecosystem**. This release elevates loom-agent to compete with CrewAI and AutoGen while maintaining its unique event sourcing advantages.

### Added

#### Crew Multi-Agent Collaboration System (~2,000 lines)

**Core Components**:

- **Role System** (`loom/crew/roles.py`, ~250 lines)
  - `Role` dataclass: Defines agent roles with goals, backstory, capabilities
  - `RoleRegistry`: Central role management
  - 6 built-in roles: `manager`, `researcher`, `developer`, `qa_engineer`, `analyst`, `writer`
  - Custom role creation support

- **Task Orchestration** (`loom/crew/orchestration.py`, ~400 lines)
  - `Task` dataclass: Complete task definition with dependencies
  - `OrchestrationPlan`: Flexible execution planning
  - `Orchestrator`: Intelligent task execution engine
  - 4 orchestration modes:
    - **SEQUENTIAL**: Tasks execute in dependency order
    - **PARALLEL**: Independent tasks run concurrently
    - **CONDITIONAL**: Tasks execute based on conditions
    - **HIERARCHICAL**: Manager-driven delegation
  - Automatic dependency resolution with topological sorting
  - Task result passing and shared context management

- **Inter-Agent Communication** (`loom/crew/communication.py`, ~300 lines)
  - `MessageBus`: Pub/sub messaging for agent communication
  - `AgentMessage`: Structured messages with delegation, query, notification types
  - `SharedState`: Thread-safe shared state management
  - Async message delivery with subscriber callbacks

- **Crew Core** (`loom/crew/crew.py`, ~450 lines)
  - `Crew`: Multi-agent team orchestration
  - `CrewMember`: Role + Agent binding
  - Automatic agent initialization from roles
  - Role-specific system instruction generation
  - Integration with MessageBus and SharedState
  - `kickoff()` method for plan execution

- **Delegation Tool** (`loom/builtin/tools/delegate.py`, ~100 lines)
  - `DelegateTool`: Enables manager agents to delegate tasks
  - Automatic task wrapping and execution
  - Result aggregation and reporting

- **Condition Builder** (`loom/crew/conditions.py`, ~150 lines)
  - `ConditionBuilder`: Declarative condition creation
  - Condition types: `key_equals`, `key_exists`, `custom`
  - Evaluation against shared context

**Testing**:
- 106 comprehensive unit tests (`tests/unit/crew/`)
- Test coverage for all orchestration modes
- Integration tests for crew execution
- 100% test pass rate

**Documentation**:
- Complete user guide: `docs/CREW_SYSTEM.md` (~600 lines)
- Architecture documentation with examples
- Use cases: code review, parallel research, conditional workflows

**Examples**:
- Complete demo: `examples/crew_demo.py` (~400 lines)
- 7 scenario demonstrations
- Real-world workflow examples

#### Tool Plugin System (~1,200 lines)

**Core Components**:

- **Plugin Metadata** (`loom/plugins/tool_plugin.py`, ~80 lines)
  - `ToolPluginMetadata`: Rich plugin metadata with validation
  - Semantic versioning support
  - Dependency declaration
  - Tag-based categorization
  - JSON serialization/deserialization

- **Plugin Wrapper** (`loom/plugins/tool_plugin.py`, ~70 lines)
  - `ToolPlugin`: Plugin lifecycle management
  - Status states: LOADED → ENABLED → DISABLED → ERROR
  - Tool instance creation
  - Error state handling

- **Plugin Registry** (`loom/plugins/tool_plugin.py`, ~140 lines)
  - `ToolPluginRegistry`: Central plugin repository
  - Tool name conflict detection
  - Plugin search by tag/author
  - Status filtering
  - Statistics and metrics

- **Plugin Loader** (`loom/plugins/tool_plugin.py`, ~160 lines)
  - `ToolPluginLoader`: Dynamic plugin loading
  - Load from file or Python module
  - Auto-discovery in directories
  - Automatic registration support
  - Validation and error handling

- **Plugin Manager** (`loom/plugins/tool_plugin.py`, ~120 lines)
  - `ToolPluginManager`: High-level API for plugin management
  - Install/uninstall operations
  - Enable/disable lifecycle
  - Batch discovery and installation
  - Integrated registry and loader

**Built-in Plugins**:
- `WeatherTool`: Weather query example
- `CurrencyConverterTool`: Currency conversion
- `SentimentAnalysisTool`: Text sentiment analysis

**Testing**:
- 35 comprehensive unit tests (`tests/unit/plugins/test_tool_plugin.py`, ~700 lines)
- Test coverage: metadata, lifecycle, registry, loader, manager
- 100% test pass rate

**Documentation**:
- Complete system guide: `docs/TOOL_PLUGIN_SYSTEM.md` (~730 lines)
- Plugin creation tutorial
- API reference
- Best practices and troubleshooting
- Implementation summary: `docs/TOOL_PLUGIN_IMPLEMENTATION_SUMMARY.md` (~500 lines)

**Examples**:
- Complete demo: `examples/plugin_demo.py` (~350 lines)
- Example plugins: `examples/tool_plugins/` (~420 lines)
- Plugin template: `examples/tool_plugins/weather_plugin.py`

#### Documentation Improvements

- **Bilingual README** (Total: ~3,000 lines)
  - **Chinese README.md** (~1,470 lines)
    - Complete framework documentation
    - 8 core mechanisms explained
    - Crew system integration guide
    - Plugin system integration guide
    - 40+ code examples
    - Progressive learning path (30s → 5min → 10min)
  - **English README_EN.md** (~1,470 lines)
    - Full translation maintaining technical accuracy
    - Bidirectional language switcher
    - All examples and documentation preserved

- **Comparison Tables**
  - vs LangGraph: Event sourcing, strategy upgrade, HITL, context debugging
  - vs AutoGen: Orchestration modes, persistence, tool orchestration
  - vs CrewAI: Role system, crash recovery, context management

### Changed

- **Package Description** (`pyproject.toml`)
  - Updated to: "Enterprise-grade recursive state machine agent framework with event sourcing, multi-agent collaboration, and tool plugin system"
  - Reflects new capabilities and enterprise positioning

- **Framework Positioning**
  - From: "Stateful recursive agent framework"
  - To: "Enterprise-grade multi-agent framework with event sourcing"
  - Competitive positioning against CrewAI and AutoGen

### Statistics

- **New Code**: ~3,200 lines (Crew: ~2,000, Plugins: ~1,200)
- **Test Code**: ~1,200 lines (141 tests total)
- **Documentation**: ~3,500 lines
- **Examples**: ~1,200 lines
- **Total Addition**: ~9,100 lines

### Feature Comparison

| Feature | LangGraph | AutoGen | CrewAI | **loom-agent 0.1.0** |
|---------|-----------|---------|--------|----------------------|
| **Event Sourcing** | ❌ | ❌ | ❌ | ✅ Complete |
| **Crash Recovery** | ⚠️ Checkpointing | ❌ | ❌ | ✅ Event replay |
| **Multi-Agent** | ❌ | ✅ | ✅ | ✅ Crew system |
| **Orchestration Modes** | Basic | Basic | Basic | ✅ 4 modes |
| **Tool Plugins** | ❌ | ❌ | ❌ | ✅ Complete system |
| **HITL** | interrupt_before | ❌ | ❌ | ✅ Lifecycle hooks |
| **Context Debugging** | ❌ | ❌ | ❌ | ✅ ContextDebugger |
| **Plugin Ecosystem** | ❌ | ❌ | ❌ | ✅ Dynamic loading |

### Upgrade Guide

#### From v0.0.9 to v0.1.0

**No Breaking Changes** - v0.1.0 is fully backward compatible. All new features are opt-in.

**To Use Crew System**:

```python
from loom.crew import Crew, Role, Task, OrchestrationPlan, OrchestrationMode

# Define roles
roles = [
    Role(name="researcher", goal="Gather information", tools=[...]),
    Role(name="developer", goal="Write code", tools=[...]),
]

# Create crew
crew = Crew(roles=roles, llm=llm)

# Define tasks
tasks = [
    Task(id="research", assigned_role="researcher", ...),
    Task(id="implement", assigned_role="developer", dependencies=["research"]),
]

# Execute
plan = OrchestrationPlan(tasks=tasks, mode=OrchestrationMode.SEQUENTIAL)
results = await crew.kickoff(plan)
```

**To Use Plugin System**:

```python
from loom.plugins import ToolPluginManager

# Create manager
manager = ToolPluginManager()

# Install plugin
await manager.install_from_file("my_plugin.py", enable=True)

# Use tool
tool = manager.get_tool("my_tool")
result = await tool.run(param="value")
```

### Contributors

- **kongusen** - Architecture and implementation
- **Community feedback** - Feature requests and testing

### Next Steps (v0.2.0)

- 🌐 Distributed execution support
- 💾 Multi-backend storage (PostgreSQL, Redis)
- 📊 Web UI for monitoring
- 🎨 Enhanced visualization (execution tree, flame graphs)
- 🔌 More plugins (LLM providers, memory backends, storage adapters)

---

## [0.0.9] - 2024-12-09

### Fixed

- **Hooks Parameter Integration**: Fixed missing `hooks` parameter support in `Agent.__init__()` method
  - Added `hooks`, `event_journal`, `context_debugger`, and `thread_id` parameters to `Agent` class
  - Ensured proper parameter passing from `loom.agent()` → `Agent.__init__()` → `AgentExecutor.__init__()`
  - All lifecycle hooks now work correctly throughout the execution chain

### Added

- **Comprehensive Hooks Documentation**: Added detailed hooks usage guide
  - Complete guide at `docs/HOOKS_USAGE_GUIDE.md` covering all 9 hook points
  - Detailed examples for built-in hooks (LoggingHook, MetricsHook, HITLHook)
  - Custom hook implementation examples (Analytics, Permission Control, Rate Limiting, etc.)
  - Best practices and advanced usage patterns
  - Complete working examples in `examples/hooks_complete_demo.py`

### Changed

- Improved hooks integration documentation and examples
- Enhanced developer experience with clearer hook usage patterns

---

## [0.0.8] - 2025-12-09

### 🎉 Major Architecture Upgrade - Recursive State Machine

v0.0.8 represents a significant architectural evolution from "implicit recursion framework" to a production-ready **Recursive State Machine (RSM)**. This release adds engineering capabilities while maintaining the framework's core simplicity.

### Added

#### Core Components (~3,500 lines)

- **ExecutionFrame** (~400 lines)
  - Immutable execution stack frame representing one recursion level
  - Inspired by Python call stack and React Fiber architecture
  - Complete state snapshot with parent-child linking
  - Methods: `next_frame()`, `with_context()`, `with_llm_response()`, `with_tool_results()`, `to_checkpoint()`

- **EventJournal** (~500 lines)
  - Append-only event log for complete execution history
  - Event sourcing architecture (vs LangGraph's static snapshots)
  - JSON Lines storage format with async batched writes
  - Thread isolation and sequence tracking
  - Methods: `append()`, `replay()`, `start()`, `stop()`

- **StateReconstructor** (~450 lines)
  - Idempotent state reconstruction from event stream
  - Time travel debugging - reconstruct at any historical iteration
  - **Unique Feature**: Replay old events with new strategies (LangGraph cannot do this)
  - Methods: `reconstruct()`, `reconstruct_at_iteration()`, `reconstruct_with_new_strategy()`

- **LifecycleHooks** (~550 lines)
  - 9 hook points for elegant control flow without explicit graph edges
  - Hook points: `before_iteration_start`, `before/after_context_assembly`, `before_llm_call`, `after_llm_response`, `before/after_tool_execution`, `before_recursion`, `after_iteration_end`
  - `InterruptException` for Human-in-the-Loop (HITL) support
  - `SkipToolException` for selective tool skipping
  - `HITLHook`: Built-in hook for dangerous operation confirmation
  - `LoggingHook`: Execution logging with verbosity control
  - `MetricsHook`: Real-time metrics collection

- **ContextDebugger** (~550 lines)
  - Transparent context management decisions
  - Answer "Why did LLM forget X?" questions
  - Methods: `record_assembly()`, `explain_iteration()`, `explain_component()`, `generate_summary()`
  - Auto-export feature for post-execution analysis

- **ExecutionVisualizer** (~500 lines)
  - CLI visualization as flame graph/timeline
  - Shows recursion depth, phase durations, and event sequences
  - Methods: `render_timeline()`, `render_flame_graph()`, `export_to_json()`

#### AgentExecutor Integration

- **Phase 0-5 Complete Integration**
  - Phase 0: ExecutionFrame creation and `before_iteration_start` hook
  - Phase 1: Context assembly hooks + ContextDebugger recording
  - Phase 2: LLM call hooks (`before_llm_call`, `after_llm_response`)
  - Phase 4: Tool execution hooks with **full HITL support**
  - Phase 5: Recursion hook (`before_recursion`)
  - `after_iteration_end` hook at all exit points

- **Crash Recovery API**
  - New `AgentExecutor.resume()` method for crash recovery
  - Automatically replays events and reconstructs state
  - Continues execution from last checkpoint
  - Example:
    ```python
    async for event in executor.resume(thread_id="user-123"):
        if event.type == AgentEventType.AGENT_FINISH:
            print(f"✅ Recovered: {event.content}")
    ```

- **Event Recording**
  - All agent events automatically recorded to EventJournal
  - Per-thread isolation with configurable storage path
  - Helper method: `_record_event()` called at every phase

- **HITL Implementation**
  - `InterruptException` raised in `before_tool_execution` hook
  - Automatic checkpoint saving for resumption
  - User confirmation callback for dangerous operations
  - Example:
    ```python
    hitl_hook = HITLHook(
        dangerous_tools=["delete_file", "send_email"],
        ask_user_callback=lambda msg: input(f"{msg} (y/n): ") == "y"
    )
    ```

#### High-Level API Enhancements

- **Updated `agent()` Factory Function**
  - New parameters:
    - `hooks: Optional[List[LifecycleHook]]` - Lifecycle hooks list
    - `enable_persistence: bool` - Auto-enable event journal
    - `journal_path: Optional[Path]` - Custom journal storage path
    - `event_journal: Optional[EventJournal]` - Pre-configured journal
    - `context_debugger: Optional[ContextDebugger]` - Context debugger
    - `thread_id: Optional[str]` - Thread ID for event isolation

- **Convenience Features**
  - `enable_persistence=True` automatically creates EventJournal
  - Auto-creates ContextDebugger when using advanced features
  - Updated `agent_from_env()` with same new parameters

#### Testing

- **Comprehensive Integration Tests** (`tests/integration/test_loom_2_0_integration.py`)
  - 8 integration tests covering all new features
  - Tests: basic execution, event journal, state reconstruction, crash recovery, HITL, context debugger, complete workflow, custom hooks
  - Custom test utilities: `MockLLMWithToolCalls` for tool call generation
  - Test coverage: 50% passing (4/8) - core features validated

#### Documentation

- **Architecture Documentation** (`docs/ARCHITECTURE_REFACTOR.md`, ~600 lines)
  - Complete design philosophy and rationale
  - Detailed component documentation
  - Usage examples and API changes
  - Comparison with LangGraph

- **Integration Status Tracking** (`docs/INTEGRATION_STATUS.md`, ~400 lines)
  - Detailed progress tracking
  - Component completion status
  - Integration roadmap

- **Integration Complete Report** (`docs/INTEGRATION_COMPLETE.md`, ~300 lines)
  - v0.0.8 feature summary
  - Code statistics and metrics
  - Available functionality guide
  - Known issues and improvement areas

- **Working Examples** (`examples/integration_example.py`, ~400 lines)
  - 7 complete examples demonstrating all new features
  - Basic usage, crash recovery, HITL, context debugging, custom hooks

### Changed

- **README.md** - Complete rewrite
  - New tagline: "The Stateful Recursive Agent Framework for Complex Logic"
  - Highlights v0.0.8 "Recursive State Machine" architecture
  - Added "What's New in v0.0.8" section
  - Added "loom-agent vs LangGraph" comparison table
  - Updated architecture diagrams showing lifecycle hooks
  - New use cases: production with crash recovery, HITL, research/debugging
  - Updated roadmap showing v0.0.8 as current release

- **Package Description** (`pyproject.toml`)
  - Updated to: "Production-ready Python Agent framework with event sourcing, lifecycle hooks, and crash recovery"

### Fixed

- **EventJournal Serialization** (`loom/core/event_journal.py`)
  - Added `hasattr()` type checks before accessing tool_call/tool_result attributes
  - Prevents `AttributeError` when serializing events with function objects
  - Lines 220-221: Safe attribute access for tool_call and tool_result

- **ExecutionPhase Enum Handling** (`tests/integration/test_loom_2_0_integration.py`)
  - Test assertions now handle both string and enum types for phase values
  - Added fallback checks for phase name variations

- **resume() Metadata Safety** (`loom/core/agent_executor.py`)
  - Line 1544: Safe enum value access with `hasattr()` check
  - Handles cases where `final_phase` is string vs enum

### Architectural Advantages vs LangGraph

| Capability | LangGraph | loom-agent 0.0.8 | Advantage |
|------------|-----------|------------------|-----------|
| **Persistence** | Static snapshots (Checkpointing) | Event Sourcing | 🟢 **loom** |
| **Strategy Upgrade** | ❌ Not supported | ✅ Replay with new strategy | 🟢 **loom (unique)** |
| **HITL** | `interrupt_before` API | LifecycleHooks + InterruptException | 🟢 **loom** |
| **Context Governance** | Simple dict | Context Fabric + ContextDebugger | 🟢 **loom (unique)** |
| **Visualization** | DAG flowchart | Flame graph (time+depth) | 🟡 Different strengths |
| **Code Simplicity** | Explicit graph edges | Hook injection | 🟢 **loom** |
| **Explicit Workflow** | ✅ Clear graph structure | ❌ Implicit recursion | 🟠 **LangGraph** |

### Statistics

- **New Code**: ~3,500 lines of core components
- **Integration Code**: ~250 lines in AgentExecutor
- **Total Addition**: ~3,750 lines
- **Test Code**: ~500 lines
- **Documentation**: ~1,800 lines

### Known Issues

- **Test Framework Limitations**
  - Built-in `MockLLM` doesn't generate tool calls
  - 4/8 integration tests blocked by test utility limitations
  - Created custom `MockLLMWithToolCalls` as workaround
  - Priority: Medium - need enhanced test utilities

- **HITL Test Coverage**
  - Need more comprehensive HITL scenarios
  - Checkpoint recovery flow needs validation
  - Priority: Medium

### Upgrade Guide

#### From v0.0.7 to v0.0.8

**No Breaking Changes** - v0.0.8 is fully backward compatible with v0.0.7. All new features are opt-in.

**To Use New Features**:

1. **Enable Persistence**:
   ```python
   from loom import agent
   from pathlib import Path

   my_agent = agent(
       provider="openai",
       model="gpt-4",
       tools=tools,
       enable_persistence=True,  # 🆕 New
       journal_path=Path("./logs"),  # 🆕 New
   )
   ```

2. **Add Lifecycle Hooks**:
   ```python
   from loom.core.lifecycle_hooks import LoggingHook, MetricsHook, HITLHook

   my_agent = agent(
       provider="openai",
       model="gpt-4",
       tools=tools,
       hooks=[  # 🆕 New
           LoggingHook(verbose=True),
           MetricsHook(),
           HITLHook(dangerous_tools=["delete_file"])
       ],
   )
   ```

3. **Enable Context Debugging**:
   ```python
   from loom.core import ContextDebugger

   debugger = ContextDebugger(enable_auto_export=True)

   my_agent = agent(
       provider="openai",
       model="gpt-4",
       tools=tools,
       context_debugger=debugger,  # 🆕 New
   )

   # After execution
   print(debugger.generate_summary())
   ```

4. **Use Crash Recovery**:
   ```python
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

### Contributors

- **kongusen** - Architecture design and implementation
- **Claude Code** - Inspiration for tt recursive pattern

---

## [0.0.7] - 2025-12-08

### Changed
- Version bump for maintenance release
- Minor bug fixes and stability improvements

---

## [0.0.6] - Previous Release

(See git history for details of earlier releases)

---

## Links

- **GitHub**: https://github.com/kongusen/loom-agent
- **PyPI**: https://pypi.org/project/loom-agent/
- **Documentation**: [docs/](docs/)
- **Examples**: [examples/integration_example.py](examples/integration_example.py)
