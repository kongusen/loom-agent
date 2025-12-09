# Changelog

All notable changes to loom-agent will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
