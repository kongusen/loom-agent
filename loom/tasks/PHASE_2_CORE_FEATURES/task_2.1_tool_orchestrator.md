# Task 2.1: Implement ToolOrchestrator

**Status**: 🔄 In Progress
**Priority**: P0 (Critical)
**Estimated Time**: 2-3 days
**Started**: 2025-10-25
**Dependencies**: Task 1.1, 1.2, 1.3

---

## 📋 Overview

### Objective

Implement intelligent tool orchestration that distinguishes between read-only and write tools, executing them in parallel or sequentially to prevent race conditions and improve safety.

### Current Problem

```python
# Loom 1.0 - All tools execute in parallel
await asyncio.gather(*[tool.execute() for tool in tool_calls])

# Problem scenarios:
# 1. ReadTool and EditTool on same file → race condition
# 2. Multiple EditTools on same file → data corruption
# 3. No consideration for tool side effects
```

**Real Bug Example**:
```python
# User asks: "Read config.json and update the version field"
# LLM generates:
tool_calls = [
    ToolCall(name="Read", arguments={"path": "config.json"}),
    ToolCall(name="Edit", arguments={"path": "config.json", ...})
]

# Current behavior: Both execute in parallel
# Result: Edit might start before Read completes → race condition!
```

### Solution

```python
# Loom 2.0 - Intelligent orchestration
class ToolOrchestrator:
    async def execute_batch(self, tool_calls: List[ToolCall]):
        # 1. Categorize tools
        read_only = [tc for tc in tool_calls if tools[tc.name].is_read_only]
        write_tools = [tc for tc in tool_calls if not tools[tc.name].is_read_only]

        # 2. Execute read-only tools in parallel (safe)
        if read_only:
            async for result in self.execute_parallel(read_only):
                yield result

        # 3. Execute write tools sequentially (safe)
        for tc in write_tools:
            result = await self.execute_one(tc)
            yield result
```

---

## 🎯 Goals

1. **Safety**: Prevent race conditions between tools
2. **Performance**: Parallel execution for safe operations
3. **Flexibility**: Easy to classify new tools
4. **Observability**: Yield AgentEvent for each execution phase

---

## 🏗️ Architecture

### Component Diagram

```
┌─────────────────────────────────────────────────────┐
│                  AgentExecutor                      │
│                                                     │
│  ┌───────────────────────────────────────────────┐ │
│  │           ToolOrchestrator                    │ │
│  │                                               │ │
│  │  1. Categorize tools (read-only vs write)    │ │
│  │  2. Execute parallel/sequential               │ │
│  │  3. Yield AgentEvent for each phase           │ │
│  │                                               │ │
│  │  ┌─────────────┐    ┌──────────────┐         │ │
│  │  │ Read-Only   │    │ Write Tools  │         │ │
│  │  │ (Parallel)  │    │ (Sequential) │         │ │
│  │  │             │    │              │         │ │
│  │  │ • ReadTool  │    │ • EditTool   │         │ │
│  │  │ • GrepTool  │    │ • WriteTool  │         │ │
│  │  │ • GlobTool  │    │ • BashTool   │         │ │
│  │  └─────────────┘    └──────────────┘         │ │
│  └───────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

### Class Design

```python
# loom/core/tool_orchestrator.py

from enum import Enum
from typing import AsyncGenerator, Dict, List
from loom.core.types import ToolCall, ToolResult
from loom.core.events import AgentEvent, AgentEventType
from loom.interfaces.tool import BaseTool


class ToolCategory(str, Enum):
    """Tool execution categories for safety classification."""
    READ_ONLY = "read_only"      # Safe to parallelize
    WRITE = "write"                # Must execute sequentially
    NETWORK = "network"            # May need rate limiting (future)
    DESTRUCTIVE = "destructive"    # Requires extra validation (future)


class ToolOrchestrator:
    """
    Intelligent tool execution orchestrator.

    Features:
    - Categorize tools by safety (read-only vs write)
    - Execute read-only tools in parallel
    - Execute write tools sequentially
    - Yield AgentEvent for observability
    - Integration with permission system

    Example:
        ```python
        orchestrator = ToolOrchestrator(
            tools={"Read": ReadTool(), "Edit": EditTool()},
            permission_manager=pm
        )

        tool_calls = [
            ToolCall(name="Read", arguments={"path": "a.txt"}),
            ToolCall(name="Read", arguments={"path": "b.txt"}),
            ToolCall(name="Edit", arguments={"path": "c.txt"})
        ]

        async for event in orchestrator.execute_batch(tool_calls):
            if event.type == AgentEventType.TOOL_RESULT:
                print(event.tool_result.content)
        ```
    """

    def __init__(
        self,
        tools: Dict[str, BaseTool],
        permission_manager: Optional[PermissionManager] = None,
        max_parallel: int = 5
    ):
        self.tools = tools
        self.permission_manager = permission_manager
        self.max_parallel = max_parallel

    async def execute_batch(
        self,
        tool_calls: List[ToolCall]
    ) -> AsyncGenerator[AgentEvent, None]:
        """
        Execute a batch of tool calls with intelligent orchestration.

        Strategy:
        1. Categorize tools (read-only vs write)
        2. Execute read-only in parallel (up to max_parallel)
        3. Execute write tools sequentially
        4. Yield AgentEvent for each execution phase

        Args:
            tool_calls: List of tool calls to execute

        Yields:
            AgentEvent: Execution progress events
        """
        ...

    def categorize_tools(
        self,
        tool_calls: List[ToolCall]
    ) -> tuple[List[ToolCall], List[ToolCall]]:
        """
        Categorize tool calls into read-only and write.

        Returns:
            (read_only_calls, write_calls)
        """
        ...

    async def execute_parallel(
        self,
        tool_calls: List[ToolCall]
    ) -> AsyncGenerator[AgentEvent, None]:
        """Execute read-only tools in parallel."""
        ...

    async def execute_sequential(
        self,
        tool_calls: List[ToolCall]
    ) -> AsyncGenerator[AgentEvent, None]:
        """Execute write tools sequentially."""
        ...

    async def execute_one(
        self,
        tool_call: ToolCall
    ) -> AgentEvent:
        """Execute a single tool call."""
        ...
```

---

## 📝 Implementation Steps

### Step 1: Modify BaseTool Interface

**File**: `loom/interfaces/tool.py`

```python
# Add to BaseTool
class BaseTool(ABC):
    name: str
    description: str
    args_schema: Type[BaseModel]

    # 🆕 New attributes for orchestration
    is_read_only: bool = False
    """Whether this tool only reads data (safe to parallelize)."""

    category: str = "general"
    """Tool category: general, destructive, network."""

    requires_confirmation: bool = False
    """Whether this tool requires user confirmation (future)."""
```

**Changes**:
- Add `is_read_only` boolean attribute
- Add `category` string attribute
- Add `requires_confirmation` for future use
- Update docstrings

### Step 2: Classify Built-in Tools

**Files to modify**:
- `loom/builtin/tools/read.py`
- `loom/builtin/tools/edit.py`
- `loom/builtin/tools/write.py`
- `loom/builtin/tools/grep.py`
- `loom/builtin/tools/glob.py`
- `loom/builtin/tools/bash.py`
- Any other tools in `loom/builtin/tools/`

**Classification**:

| Tool | is_read_only | category | Rationale |
|------|--------------|----------|-----------|
| ReadTool | ✅ True | general | Only reads files |
| GrepTool | ✅ True | general | Only searches content |
| GlobTool | ✅ True | general | Only lists files |
| EditTool | ❌ False | destructive | Modifies files |
| WriteTool | ❌ False | destructive | Creates/overwrites files |
| BashTool | ❌ False | general | May have side effects |

**Example**:
```python
# loom/builtin/tools/read.py
class ReadTool(BaseTool):
    name = "Read"
    description = "Read file contents"
    is_read_only = True  # 🆕
    category = "general"  # 🆕

    async def run(self, path: str) -> str:
        ...
```

### Step 3: Implement ToolOrchestrator

**File**: `loom/core/tool_orchestrator.py` (new file)

**Implementation outline**:

```python
class ToolOrchestrator:
    def __init__(self, tools, permission_manager, max_parallel=5):
        self.tools = tools
        self.permission_manager = permission_manager
        self.max_parallel = max_parallel

    async def execute_batch(self, tool_calls):
        """Main orchestration logic."""
        # Emit start event
        yield AgentEvent(
            type=AgentEventType.TOOL_CALLS_START,
            metadata={"total_tools": len(tool_calls)}
        )

        # Categorize
        read_only, write_tools = self.categorize_tools(tool_calls)

        # Execute read-only in parallel
        if read_only:
            yield AgentEvent(
                type=AgentEventType.TOOL_ORCHESTRATION,
                metadata={
                    "phase": "parallel",
                    "count": len(read_only)
                }
            )
            async for event in self.execute_parallel(read_only):
                yield event

        # Execute write sequentially
        if write_tools:
            yield AgentEvent(
                type=AgentEventType.TOOL_ORCHESTRATION,
                metadata={
                    "phase": "sequential",
                    "count": len(write_tools)
                }
            )
            async for event in self.execute_sequential(write_tools):
                yield event

    def categorize_tools(self, tool_calls):
        """Split into read-only and write."""
        read_only = []
        write_tools = []

        for tc in tool_calls:
            tool = self.tools.get(tc.name)
            if tool and tool.is_read_only:
                read_only.append(tc)
            else:
                write_tools.append(tc)

        return read_only, write_tools

    async def execute_parallel(self, tool_calls):
        """Execute read-only tools in parallel."""
        import asyncio

        # Use semaphore to limit concurrency
        semaphore = asyncio.Semaphore(self.max_parallel)

        async def execute_with_semaphore(tc):
            async with semaphore:
                return await self.execute_one(tc)

        # Execute all in parallel
        tasks = [execute_with_semaphore(tc) for tc in tool_calls]

        for coro in asyncio.as_completed(tasks):
            event = await coro
            yield event

    async def execute_sequential(self, tool_calls):
        """Execute write tools sequentially."""
        for tc in tool_calls:
            event = await self.execute_one(tc)
            yield event

    async def execute_one(self, tool_call):
        """Execute a single tool."""
        # Emit start event
        yield AgentEvent(
            type=AgentEventType.TOOL_EXECUTION_START,
            tool_call=EventToolCall(
                id=tool_call.id,
                name=tool_call.name,
                arguments=tool_call.arguments
            )
        )

        try:
            # Check permissions
            if self.permission_manager:
                allowed = await self.permission_manager.check_tool(
                    tool_call.name,
                    tool_call.arguments
                )
                if not allowed:
                    raise PermissionError(f"Tool {tool_call.name} not allowed")

            # Execute tool
            tool = self.tools[tool_call.name]
            result_content = await tool.run(**tool_call.arguments)

            # Create result
            result = ToolResult(
                tool_call_id=tool_call.id,
                tool_name=tool_call.name,
                content=result_content,
                is_error=False
            )

            # Emit result event
            yield AgentEvent.tool_result(result)

        except Exception as e:
            # Handle error
            result = ToolResult(
                tool_call_id=tool_call.id,
                tool_name=tool_call.name,
                content=str(e),
                is_error=True
            )

            yield AgentEvent(
                type=AgentEventType.TOOL_ERROR,
                tool_result=result,
                error=e
            )
```

### Step 4: Integrate into AgentExecutor

**File**: `loom/core/agent_executor.py`

**Changes**:
1. Add ToolOrchestrator import
2. Initialize in `__init__`
3. Replace existing tool execution with orchestrator

```python
# In __init__
self.tool_orchestrator = ToolOrchestrator(
    tools=self.tools,
    permission_manager=self.permission_manager,
    max_parallel=5
)

# In execute_stream (replace tool execution section)
if tool_calls:
    # Use orchestrator instead of direct execution
    async for event in self.tool_orchestrator.execute_batch(tc_models):
        yield event

        # Update history with results
        if event.type == AgentEventType.TOOL_RESULT:
            tool_msg = Message(
                role="tool",
                content=event.tool_result.content,
                tool_call_id=event.tool_result.tool_call_id
            )
            history.append(tool_msg)
```

### Step 5: Add New Event Types (if needed)

**File**: `loom/core/events.py`

```python
# Add to AgentEventType
class AgentEventType(str, Enum):
    # ... existing events ...

    # 🆕 Orchestration events
    TOOL_ORCHESTRATION = "tool_orchestration"
    """Tool orchestration phase (parallel/sequential)."""
```

---

## 🧪 Testing Requirements

### Unit Tests

**File**: `tests/unit/test_tool_orchestrator.py`

**Test cases** (target 25-30 tests):

```python
class TestToolOrchestrator:
    """Test ToolOrchestrator class."""

    def test_init(self):
        """Test initialization."""
        ...

    def test_categorize_read_only_tools(self):
        """Test categorization of read-only tools."""
        ...

    def test_categorize_write_tools(self):
        """Test categorization of write tools."""
        ...

    def test_categorize_mixed_tools(self):
        """Test categorization of mixed tool calls."""
        ...

    async def test_execute_parallel_read_only(self):
        """Test parallel execution of read-only tools."""
        ...

    async def test_execute_sequential_write(self):
        """Test sequential execution of write tools."""
        ...

    async def test_execute_batch_mixed(self):
        """Test batch execution with mixed tools."""
        ...

    async def test_parallel_respects_max_parallel(self):
        """Test max_parallel limit is respected."""
        ...

    async def test_execute_one_success(self):
        """Test single tool execution success."""
        ...

    async def test_execute_one_error(self):
        """Test single tool execution error handling."""
        ...

    async def test_permission_check_integration(self):
        """Test integration with permission manager."""
        ...

    async def test_event_emission(self):
        """Test AgentEvent emission during execution."""
        ...

    async def test_parallel_execution_order_independent(self):
        """Test parallel tools can complete in any order."""
        ...

    async def test_sequential_execution_order(self):
        """Test sequential tools execute in order."""
        ...


class TestToolCategorization:
    """Test tool categorization logic."""

    def test_read_tool_is_read_only(self):
        """Verify ReadTool is classified as read-only."""
        ...

    def test_grep_tool_is_read_only(self):
        """Verify GrepTool is classified as read-only."""
        ...

    def test_edit_tool_is_write(self):
        """Verify EditTool is classified as write."""
        ...

    def test_bash_tool_is_write(self):
        """Verify BashTool is classified as write."""
        ...


class TestRaceConditionPrevention:
    """Test race condition prevention."""

    async def test_read_and_edit_same_file(self):
        """Test Read and Edit on same file execute safely."""
        # Read should complete before Edit starts
        ...

    async def test_multiple_edits_same_file(self):
        """Test multiple Edits on same file are sequential."""
        ...

    async def test_multiple_reads_same_file(self):
        """Test multiple Reads on same file can be parallel."""
        ...


class TestPerformance:
    """Test performance improvements."""

    async def test_parallel_faster_than_sequential(self):
        """Test parallel execution is faster for read-only tools."""
        ...

    async def test_max_parallel_limiting(self):
        """Test max_parallel limits concurrent execution."""
        ...
```

### Integration Tests

**File**: `tests/integration/test_tool_orchestration.py`

```python
class TestOrchestrationIntegration:
    """Test orchestration in full agent context."""

    async def test_agent_with_mixed_tool_calls(self):
        """Test agent executing mixed read/write tools."""
        ...

    async def test_orchestration_with_rag(self):
        """Test orchestration with RAG context."""
        ...

    async def test_orchestration_events(self):
        """Test AgentEvent emission during orchestration."""
        ...
```

---

## ✅ Acceptance Criteria

- [ ] `BaseTool` interface has `is_read_only` and `category` attributes
- [ ] All built-in tools are classified (read-only vs write)
- [ ] `ToolOrchestrator` class implemented
  - [ ] `categorize_tools()` correctly splits tools
  - [ ] `execute_parallel()` executes read-only tools concurrently
  - [ ] `execute_sequential()` executes write tools in order
  - [ ] `max_parallel` limit is respected
- [ ] Integration with `AgentExecutor`
  - [ ] `execute_stream()` uses orchestrator
  - [ ] `execute()` uses orchestrator
  - [ ] `stream()` uses orchestrator
- [ ] Test coverage ≥ 80%
  - [ ] 25-30 unit tests
  - [ ] All tests pass
- [ ] No race conditions in concurrent execution
- [ ] Performance: Parallel execution faster than sequential for read-only
- [ ] Events emitted correctly
- [ ] Backward compatible (existing tests still pass)

---

## 📦 Deliverables

1. **Core Implementation**
   - [ ] `loom/core/tool_orchestrator.py` (~300-400 lines)
   - [ ] Modified `loom/interfaces/tool.py`
   - [ ] Modified `loom/core/agent_executor.py`

2. **Tool Classification**
   - [ ] All tools in `loom/builtin/tools/` classified
   - [ ] Documentation for each classification

3. **Tests**
   - [ ] `tests/unit/test_tool_orchestrator.py` (25-30 tests)
   - [ ] `tests/integration/test_tool_orchestration.py` (3-5 tests)
   - [ ] All tests passing

4. **Documentation**
   - [ ] Code docstrings complete
   - [ ] Example usage in docstrings
   - [ ] `examples/tool_orchestration_demo.py`
   - [ ] `docs/TASK_2.1_COMPLETION_SUMMARY.md`

5. **Validation**
   - [ ] Run full test suite: `pytest tests/ -v`
   - [ ] Coverage report: `pytest --cov=loom --cov-report=html`
   - [ ] Performance benchmark (parallel vs sequential)

---

## 📚 References

### Claude Code Inspiration

From `cc分析/Tools.md`:
- Intelligent tool parallelization
- Safety-first execution model
- Read-only vs write distinction

### Design Principles

1. **Safety First**: Prevent race conditions by default
2. **Performance**: Parallelize when safe
3. **Observability**: Emit events for all phases
4. **Flexibility**: Easy to add new tools
5. **Backward Compatibility**: Don't break existing code

---

## 🔍 Testing Checklist

Before marking as complete:

- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] All existing tests still pass (no regressions)
- [ ] Code coverage ≥ 80%
- [ ] Type checking passes: `mypy loom/`
- [ ] Linting passes: `ruff check loom/`
- [ ] Performance test shows parallel is faster
- [ ] Manual testing with real agent
- [ ] Example code runs successfully
- [ ] Documentation reviewed

---

## 🎓 Learning Notes

### Key Concepts

1. **Read-only Tools**: Can execute in parallel safely
   - ReadTool, GrepTool, GlobTool
   - No side effects
   - No file modifications

2. **Write Tools**: Must execute sequentially
   - EditTool, WriteTool, BashTool
   - Have side effects
   - May modify files/system state

3. **Race Condition Example**:
   ```python
   # Dangerous: Read and Write same file in parallel
   await asyncio.gather(
       read_tool.run("config.json"),
       edit_tool.run("config.json", ...)
   )
   # Result: undefined behavior!
   ```

4. **Safe Orchestration**:
   ```python
   # Safe: Execute sequentially
   content = await read_tool.run("config.json")
   await edit_tool.run("config.json", ...)
   ```

### Implementation Tips

1. Use `asyncio.Semaphore` for parallel execution limiting
2. Use `asyncio.as_completed` for result streaming
3. Always emit events for observability
4. Handle tool errors gracefully
5. Test with actual file I/O for race conditions

---

**Created**: 2025-10-25
**Last Updated**: 2025-10-25
**Status**: 🔄 In Progress
