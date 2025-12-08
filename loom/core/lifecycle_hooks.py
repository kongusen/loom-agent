"""
Lifecycle Hooks: Elegant Interception Points for tt Recursion

This module provides a hook-based system for intercepting and modifying
execution flow WITHOUT explicit graph connections.

Design Philosophy:
- Keep loom-agent's linear/recursive beauty
- Add control points via middleware pattern
- No "add_edge()" - use Python decorators and callbacks

Comparison with LangGraph:
- LangGraph: graph.add_conditional_edges("node", router_function)
- loom-agent: agent.use_hook(MyHook()) - simpler, more Pythonic

Key Use Cases:
    1. Human-in-the-Loop (HITL) - Pause before dangerous operations
    2. Logging & Monitoring - Track execution without changing logic
    3. Dynamic Routing - Influence decisions based on state
    4. Context Injection - Add context at specific phases
    5. Error Handling - Custom recovery strategies

Example:
    ```python
    # Define a HITL hook
    class DangerousToolHook(LifecycleHook):
        async def before_tool_execution(self, frame, tool_call):
            if tool_call["name"] in ["delete_file", "send_email"]:
                confirmed = await self.ask_user(
                    f"Allow {tool_call['name']}?"
                )
                if not confirmed:
                    raise InterruptException("User rejected")
            return tool_call

    # Use it
    agent = agent(
        llm=llm,
        tools=tools,
        hooks=[DangerousToolHook()]
    )
    ```
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Protocol, Optional, List, Dict, Any, runtime_checkable
from dataclasses import dataclass

from .execution_frame import ExecutionFrame, ExecutionPhase
from .events import AgentEvent


# ===== Exceptions =====


class InterruptException(Exception):
    """
    Raised to interrupt execution and wait for external input.

    When a hook raises this exception, the executor:
    1. Saves current frame as checkpoint
    2. Yields EXECUTION_INTERRUPTED event
    3. Waits for resume signal

    Attributes:
        reason: Human-readable reason for interruption
        requires_user_input: Whether waiting for user
        frame_id: ID of interrupted frame
    """

    def __init__(
        self,
        reason: str,
        requires_user_input: bool = True,
        frame_id: Optional[str] = None
    ):
        self.reason = reason
        self.requires_user_input = requires_user_input
        self.frame_id = frame_id
        super().__init__(reason)


class SkipToolException(Exception):
    """
    Raised to skip a specific tool execution.

    The executor will:
    1. Not execute the tool
    2. Inject a synthetic "skipped" result
    3. Continue with other tools
    """

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


# ===== Hook Interface =====


@runtime_checkable
class LifecycleHook(Protocol):
    """
    Protocol for lifecycle hooks.

    Hooks are called at specific points in the tt recursion loop.
    All methods are optional - implement only what you need.

    Hook Execution Order (one tt iteration):
        1. before_iteration_start(frame)
        2. before_context_assembly(frame)
        3. after_context_assembly(frame, context)
        4. before_llm_call(frame, messages)
        5. after_llm_response(frame, response, tool_calls)
        6. before_tool_execution(frame, tool_call) - per tool
        7. after_tool_execution(frame, tool_result) - per tool
        8. before_recursion(frame, next_frame)
        9. after_iteration_end(frame)

    Return Values:
        - Most hooks can return modified data (or None to keep original)
        - Returning None means "no change"
        - Raising InterruptException pauses execution

    Example:
        ```python
        class LoggingHook:
            async def before_llm_call(self, frame, messages):
                print(f"Calling LLM at depth {frame.depth}")
                return messages  # Can modify messages

            async def after_tool_execution(self, frame, tool_result):
                print(f"Tool {tool_result['tool_name']} completed")
                return tool_result
        ```
    """

    async def before_iteration_start(
        self,
        frame: ExecutionFrame
    ) -> Optional[ExecutionFrame]:
        """
        Called at the start of each tt iteration.

        Args:
            frame: Current execution frame

        Returns:
            Optional[ExecutionFrame]: Modified frame or None

        Use Cases:
            - Check recursion limits
            - Inject metadata
            - Pre-flight validation
        """
        return None

    async def before_context_assembly(
        self,
        frame: ExecutionFrame
    ) -> Optional[ExecutionFrame]:
        """
        Called before Phase 1 (Context Assembly).

        Args:
            frame: Current frame (before context assembly)

        Returns:
            Optional[ExecutionFrame]: Modified frame or None

        Use Cases:
            - Inject additional context
            - Adjust token budgets
            - Pre-process messages
        """
        return None

    async def after_context_assembly(
        self,
        frame: ExecutionFrame,
        context_snapshot: Dict[str, Any],
        context_metadata: Dict[str, Any]
    ) -> Optional[tuple[Dict[str, Any], Dict[str, Any]]]:
        """
        Called after Phase 1 (Context Assembly).

        Args:
            frame: Current frame
            context_snapshot: Assembled context
            context_metadata: Context assembly metadata

        Returns:
            Optional tuple of (context_snapshot, context_metadata) or None

        Use Cases:
            - Inspect context decisions
            - Override context components
            - Log token usage
        """
        return None

    async def before_llm_call(
        self,
        frame: ExecutionFrame,
        messages: List[Dict[str, Any]]
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Called before Phase 2 (LLM Call).

        Args:
            frame: Current frame
            messages: Messages to send to LLM

        Returns:
            Optional[List[Dict]]: Modified messages or None

        Use Cases:
            - Log prompts
            - Inject system messages
            - Modify user queries
            - Budget control
        """
        return None

    async def after_llm_response(
        self,
        frame: ExecutionFrame,
        response: str,
        tool_calls: List[Dict[str, Any]]
    ) -> Optional[tuple[str, List[Dict[str, Any]]]]:
        """
        Called after Phase 2 (LLM Call) completes.

        Args:
            frame: Current frame
            response: LLM's text response
            tool_calls: LLM's requested tool calls

        Returns:
            Optional tuple of (response, tool_calls) or None

        Use Cases:
            - Analyze LLM decisions
            - Filter/modify tool calls
            - Log responses
        """
        return None

    async def before_tool_execution(
        self,
        frame: ExecutionFrame,
        tool_call: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Called before Phase 4 (Tool Execution) for EACH tool.

        This is the key hook for Human-in-the-Loop!

        Args:
            frame: Current frame
            tool_call: Tool call to execute

        Returns:
            Optional[Dict]: Modified tool_call or None

        Raises:
            InterruptException: To pause and wait for user
            SkipToolException: To skip this specific tool

        Use Cases:
            - Human-in-the-Loop confirmation
            - Permission checks
            - Rate limiting
            - Modify tool arguments

        Example:
            ```python
            async def before_tool_execution(self, frame, tool_call):
                if tool_call["name"] == "delete_file":
                    # Interrupt execution, wait for user
                    raise InterruptException("Confirm file deletion")
                return tool_call
            ```
        """
        return None

    async def after_tool_execution(
        self,
        frame: ExecutionFrame,
        tool_result: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Called after Phase 4 (Tool Execution) for EACH tool.

        Args:
            frame: Current frame
            tool_result: Tool execution result

        Returns:
            Optional[Dict]: Modified tool_result or None

        Use Cases:
            - Post-process results
            - Error recovery
            - Result caching
            - Metrics collection
        """
        return None

    async def before_recursion(
        self,
        current_frame: ExecutionFrame,
        next_frame: ExecutionFrame
    ) -> Optional[ExecutionFrame]:
        """
        Called before Phase 5 (Recursion) - before diving deeper.

        Args:
            current_frame: Current frame
            next_frame: Next frame about to be created

        Returns:
            Optional[ExecutionFrame]: Modified next_frame or None

        Use Cases:
            - Decide whether to continue recursion
            - Modify next iteration's state
            - Inject guidance for next turn
        """
        return None

    async def after_iteration_end(
        self,
        frame: ExecutionFrame
    ) -> Optional[ExecutionFrame]:
        """
        Called at the end of each tt iteration.

        Args:
            frame: Current frame (after all processing)

        Returns:
            Optional[ExecutionFrame]: Modified frame or None

        Use Cases:
            - Cleanup resources
            - Collect metrics
            - Save checkpoints
        """
        return None


# ===== Hook Manager =====


class HookManager:
    """
    Manages multiple lifecycle hooks and coordinates their execution.

    Features:
    - Executes hooks in order
    - Handles exceptions
    - Collects results
    - Provides hook chaining

    Example:
        ```python
        manager = HookManager([
            LoggingHook(),
            HITLHook(),
            MetricsHook()
        ])

        # Execute before_llm_call on all hooks
        messages = await manager.before_llm_call(frame, messages)
        ```
    """

    def __init__(self, hooks: List[LifecycleHook]):
        """
        Initialize hook manager.

        Args:
            hooks: List of hooks (executed in order)
        """
        self.hooks = hooks

    async def before_iteration_start(
        self,
        frame: ExecutionFrame
    ) -> ExecutionFrame:
        """Execute all before_iteration_start hooks."""
        for hook in self.hooks:
            if hasattr(hook, "before_iteration_start"):
                result = await hook.before_iteration_start(frame)
                if result is not None:
                    frame = result
        return frame

    async def before_context_assembly(
        self,
        frame: ExecutionFrame
    ) -> ExecutionFrame:
        """Execute all before_context_assembly hooks."""
        for hook in self.hooks:
            if hasattr(hook, "before_context_assembly"):
                result = await hook.before_context_assembly(frame)
                if result is not None:
                    frame = result
        return frame

    async def after_context_assembly(
        self,
        frame: ExecutionFrame,
        context_snapshot: Dict[str, Any],
        context_metadata: Dict[str, Any]
    ) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """Execute all after_context_assembly hooks."""
        for hook in self.hooks:
            if hasattr(hook, "after_context_assembly"):
                result = await hook.after_context_assembly(
                    frame, context_snapshot, context_metadata
                )
                if result is not None:
                    context_snapshot, context_metadata = result
        return context_snapshot, context_metadata

    async def before_llm_call(
        self,
        frame: ExecutionFrame,
        messages: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Execute all before_llm_call hooks."""
        for hook in self.hooks:
            if hasattr(hook, "before_llm_call"):
                result = await hook.before_llm_call(frame, messages)
                if result is not None:
                    messages = result
        return messages

    async def after_llm_response(
        self,
        frame: ExecutionFrame,
        response: str,
        tool_calls: List[Dict[str, Any]]
    ) -> tuple[str, List[Dict[str, Any]]]:
        """Execute all after_llm_response hooks."""
        for hook in self.hooks:
            if hasattr(hook, "after_llm_response"):
                result = await hook.after_llm_response(frame, response, tool_calls)
                if result is not None:
                    response, tool_calls = result
        return response, tool_calls

    async def before_tool_execution(
        self,
        frame: ExecutionFrame,
        tool_call: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute all before_tool_execution hooks.

        Raises:
            InterruptException: If any hook requests interruption
            SkipToolException: If any hook requests skipping
        """
        for hook in self.hooks:
            if hasattr(hook, "before_tool_execution"):
                # This can raise InterruptException or SkipToolException
                result = await hook.before_tool_execution(frame, tool_call)
                if result is not None:
                    tool_call = result
        return tool_call

    async def after_tool_execution(
        self,
        frame: ExecutionFrame,
        tool_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute all after_tool_execution hooks."""
        for hook in self.hooks:
            if hasattr(hook, "after_tool_execution"):
                result = await hook.after_tool_execution(frame, tool_result)
                if result is not None:
                    tool_result = result
        return tool_result

    async def before_recursion(
        self,
        current_frame: ExecutionFrame,
        next_frame: ExecutionFrame
    ) -> ExecutionFrame:
        """Execute all before_recursion hooks."""
        for hook in self.hooks:
            if hasattr(hook, "before_recursion"):
                result = await hook.before_recursion(current_frame, next_frame)
                if result is not None:
                    next_frame = result
        return next_frame

    async def after_iteration_end(
        self,
        frame: ExecutionFrame
    ) -> ExecutionFrame:
        """Execute all after_iteration_end hooks."""
        for hook in self.hooks:
            if hasattr(hook, "after_iteration_end"):
                result = await hook.after_iteration_end(frame)
                if result is not None:
                    frame = result
        return frame


# ===== Built-in Hooks =====


class LoggingHook:
    """
    Simple logging hook for debugging.

    Logs key events during execution.
    """

    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    async def before_iteration_start(self, frame):
        print(f"[Iteration {frame.depth}] Starting")
        return None

    async def before_llm_call(self, frame, messages):
        print(f"[Iteration {frame.depth}] Calling LLM with {len(messages)} messages")
        if self.verbose:
            print(f"  Last message: {messages[-1]['content'][:100]}...")
        return None

    async def before_tool_execution(self, frame, tool_call):
        print(f"[Iteration {frame.depth}] Executing tool: {tool_call['name']}")
        if self.verbose:
            print(f"  Arguments: {tool_call['arguments']}")
        return None


class HITLHook:
    """
    Human-in-the-Loop hook.

    Pauses execution before dangerous operations and asks for user confirmation.
    """

    def __init__(
        self,
        dangerous_tools: List[str],
        ask_user_callback: Optional[callable] = None
    ):
        """
        Initialize HITL hook.

        Args:
            dangerous_tools: List of tool names that require confirmation
            ask_user_callback: Function to ask user (returns bool)
        """
        self.dangerous_tools = dangerous_tools
        self.ask_user_callback = ask_user_callback or self._default_ask_user

    def _default_ask_user(self, message: str) -> bool:
        """Default implementation using input()."""
        response = input(f"{message} (y/n): ")
        return response.lower() in ("y", "yes")

    async def before_tool_execution(self, frame, tool_call):
        tool_name = tool_call["name"]

        if tool_name in self.dangerous_tools:
            # Ask user for confirmation
            confirmed = self.ask_user_callback(
                f"Allow execution of '{tool_name}'?"
            )

            if not confirmed:
                # Interrupt execution
                raise InterruptException(
                    f"User rejected tool execution: {tool_name}",
                    requires_user_input=True,
                    frame_id=frame.frame_id
                )

        return tool_call


class MetricsHook:
    """
    Collects execution metrics.

    Tracks iteration counts, tool usage, errors, etc.
    """

    def __init__(self):
        self.metrics = {
            "iterations": 0,
            "llm_calls": 0,
            "tool_executions": {},
            "errors": 0
        }

    async def before_iteration_start(self, frame):
        self.metrics["iterations"] += 1
        return None

    async def before_llm_call(self, frame, messages):
        self.metrics["llm_calls"] += 1
        return None

    async def after_tool_execution(self, frame, tool_result):
        tool_name = tool_result["tool_name"]
        self.metrics["tool_executions"][tool_name] = \
            self.metrics["tool_executions"].get(tool_name, 0) + 1

        if tool_result.get("is_error"):
            self.metrics["errors"] += 1

        return None

    def get_metrics(self) -> Dict[str, Any]:
        """Get collected metrics."""
        return self.metrics.copy()
