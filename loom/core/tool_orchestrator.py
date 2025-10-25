"""
Tool Orchestrator Module

Intelligent tool execution orchestration with parallel/sequential execution
based on tool safety characteristics.

This module prevents race conditions by distinguishing between read-only
and write tools, executing them appropriately.
"""

from __future__ import annotations

import asyncio
from enum import Enum
from typing import AsyncGenerator, Dict, List, Optional, Tuple

from loom.core.types import ToolCall, ToolResult
from loom.core.events import AgentEvent, AgentEventType, ToolCall as EventToolCall, ToolResult as EventToolResult
from loom.interfaces.tool import BaseTool
from loom.core.permissions import PermissionManager, PermissionAction
from loom.core.errors import PermissionDeniedError

# 🆕 Loom 2.0 - Security validation
try:
    from loom.security import SecurityValidator
except ImportError:
    SecurityValidator = None  # type: ignore


class ToolCategory(str, Enum):
    """
    Tool execution categories for safety classification.

    Categories:
        READ_ONLY: Safe to parallelize (no side effects)
        WRITE: Must execute sequentially (has side effects)
        NETWORK: May need rate limiting (future enhancement)
        DESTRUCTIVE: Requires extra validation (future enhancement)
    """
    READ_ONLY = "read_only"
    WRITE = "write"
    NETWORK = "network"
    DESTRUCTIVE = "destructive"


class ToolOrchestrator:
    """
    Intelligent tool execution orchestrator.

    Features:
    - Categorize tools by safety (read-only vs write)
    - Execute read-only tools in parallel (up to max_parallel)
    - Execute write tools sequentially
    - Yield AgentEvent for observability
    - Integration with permission system

    Example:
        ```python
        orchestrator = ToolOrchestrator(
            tools={"Read": ReadTool(), "Edit": EditTool()},
            permission_manager=pm,
            max_parallel=5
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

    Attributes:
        tools: Dictionary of available tools
        permission_manager: Optional permission manager
        max_parallel: Maximum number of parallel executions
    """

    def __init__(
        self,
        tools: Dict[str, BaseTool],
        permission_manager: Optional[PermissionManager] = None,
        security_validator: Optional["SecurityValidator"] = None,  # 🆕 Loom 2.0
        max_parallel: int = 5
    ):
        """
        Initialize the orchestrator.

        Args:
            tools: Dictionary mapping tool names to tool instances
            permission_manager: Optional permission manager for access control
            security_validator: Optional security validator (🆕 Loom 2.0)
            max_parallel: Maximum number of tools to execute in parallel (default: 5)
        """
        self.tools = tools
        self.permission_manager = permission_manager
        self.security_validator = security_validator  # 🆕 Loom 2.0
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
        if not tool_calls:
            return

        # Emit batch start event
        yield AgentEvent(
            type=AgentEventType.TOOL_CALLS_START,
            metadata={
                "total_tools": len(tool_calls),
                "max_parallel": self.max_parallel
            }
        )

        # Categorize tools
        read_only_calls, write_calls = self.categorize_tools(tool_calls)

        # Execute read-only in parallel
        if read_only_calls:
            yield AgentEvent(
                type=AgentEventType.PHASE_START,
                metadata={
                    "phase": "parallel_read_only",
                    "count": len(read_only_calls),
                    "tool_names": [tc.name for tc in read_only_calls]
                }
            )

            async for event in self.execute_parallel(read_only_calls):
                yield event

            yield AgentEvent(
                type=AgentEventType.PHASE_END,
                metadata={
                    "phase": "parallel_read_only",
                    "count": len(read_only_calls)
                }
            )

        # Execute write tools sequentially
        if write_calls:
            yield AgentEvent(
                type=AgentEventType.PHASE_START,
                metadata={
                    "phase": "sequential_write",
                    "count": len(write_calls),
                    "tool_names": [tc.name for tc in write_calls]
                }
            )

            async for event in self.execute_sequential(write_calls):
                yield event

            yield AgentEvent(
                type=AgentEventType.PHASE_END,
                metadata={
                    "phase": "sequential_write",
                    "count": len(write_calls)
                }
            )

    def categorize_tools(
        self,
        tool_calls: List[ToolCall]
    ) -> Tuple[List[ToolCall], List[ToolCall]]:
        """
        Categorize tool calls into read-only and write.

        Args:
            tool_calls: List of tool calls to categorize

        Returns:
            Tuple of (read_only_calls, write_calls)
        """
        read_only_calls: List[ToolCall] = []
        write_calls: List[ToolCall] = []

        for tc in tool_calls:
            tool = self.tools.get(tc.name)
            if tool and getattr(tool, "is_read_only", False):
                read_only_calls.append(tc)
            else:
                # Default to write (safer)
                write_calls.append(tc)

        return read_only_calls, write_calls

    async def execute_parallel(
        self,
        tool_calls: List[ToolCall]
    ) -> AsyncGenerator[AgentEvent, None]:
        """
        Execute read-only tools in parallel with concurrency limiting.

        Uses asyncio.Semaphore to limit concurrent executions to max_parallel.

        Args:
            tool_calls: List of read-only tool calls

        Yields:
            AgentEvent: Execution events (start, result, error)
        """
        if not tool_calls:
            return

        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(self.max_parallel)

        async def execute_with_semaphore(tc: ToolCall) -> AsyncGenerator[AgentEvent, None]:
            """Execute a single tool with semaphore control."""
            async with semaphore:
                async for event in self.execute_one(tc):
                    yield event

        # Create tasks for all tools
        tasks = []
        for tc in tool_calls:
            task = execute_with_semaphore(tc)
            tasks.append(task)

        # Execute and yield results as they complete
        # Use asyncio.gather to run all in parallel
        async def collect_events():
            for task in tasks:
                async for event in task:
                    yield event

        async for event in collect_events():
            yield event

    async def execute_sequential(
        self,
        tool_calls: List[ToolCall]
    ) -> AsyncGenerator[AgentEvent, None]:
        """
        Execute write tools sequentially (one after another).

        Args:
            tool_calls: List of write tool calls

        Yields:
            AgentEvent: Execution events (start, result, error)
        """
        for tc in tool_calls:
            async for event in self.execute_one(tc):
                yield event

    async def execute_one(
        self,
        tool_call: ToolCall
    ) -> AsyncGenerator[AgentEvent, None]:
        """
        Execute a single tool call.

        Phases:
        1. Permission check
        2. Tool execution
        3. Result formatting

        Args:
            tool_call: Tool call to execute

        Yields:
            AgentEvent: Execution events
        """
        # Create event tool call
        event_tool_call = EventToolCall(
            id=tool_call.id,
            name=tool_call.name,
            arguments=tool_call.arguments
        )

        # Emit start event
        yield AgentEvent(
            type=AgentEventType.TOOL_EXECUTION_START,
            tool_call=event_tool_call
        )

        try:
            # Phase 1: Security validation (🆕 Loom 2.0 - Multi-layer security)
            if self.security_validator:
                tool = self.tools.get(tool_call.name)
                if tool:
                    decision = await self.security_validator.validate(
                        tool_call=tool_call,
                        tool=tool,
                        context={}
                    )

                    if not decision.allow:
                        raise PermissionDeniedError(
                            f"Security validation failed: {decision.reason}"
                        )

            # Fallback: Permission check (backward compatibility)
            elif self.permission_manager:
                action = self.permission_manager.check(tool_call.name, tool_call.arguments)
                if action == PermissionAction.DENY:
                    raise PermissionDeniedError(f"Tool {tool_call.name} not allowed")
                if action == PermissionAction.ASK:
                    # TODO: Implement user confirmation flow
                    # For now, treat as DENY
                    raise PermissionDeniedError(f"Tool {tool_call.name} requires confirmation")

            # Phase 2: Tool execution
            tool = self.tools.get(tool_call.name)
            if not tool:
                raise ValueError(f"Tool {tool_call.name} not found")

            result_content = await tool.run(**tool_call.arguments)

            # Phase 3: Create result
            result = EventToolResult(
                tool_call_id=tool_call.id,
                tool_name=tool_call.name,
                content=str(result_content) if result_content is not None else "",
                is_error=False
            )

            # Emit result event
            yield AgentEvent.tool_result(result)

        except Exception as e:
            # Handle error
            result = EventToolResult(
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

    def get_orchestration_summary(self, tool_calls: List[ToolCall]) -> Dict:
        """
        Get a summary of how tools will be orchestrated.

        Useful for debugging and understanding execution plans.

        Args:
            tool_calls: List of tool calls to analyze

        Returns:
            Dictionary with orchestration details
        """
        read_only, write = self.categorize_tools(tool_calls)

        return {
            "total_tools": len(tool_calls),
            "read_only_count": len(read_only),
            "write_count": len(write),
            "read_only_tools": [tc.name for tc in read_only],
            "write_tools": [tc.name for tc in write],
            "execution_mode": {
                "read_only": "parallel" if read_only else "none",
                "write": "sequential" if write else "none"
            },
            "max_parallel": self.max_parallel,
            "estimated_phases": (1 if read_only else 0) + (1 if write else 0)
        }
