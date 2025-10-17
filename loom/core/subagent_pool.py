"""SubAgentPool: I2A isolated sub-agent architecture (US3)

Spawns isolated sub-agents with independent tool permissions, message histories,
and fault boundaries. Enables concurrent execution via Python 3.11 TaskGroups.

Features:
- Fault isolation (1 sub-agent failure doesn't affect others)
- Tool whitelist enforcement (independent permissions)
- Separate message histories (no cross-contamination)
- Execution depth limits (max 3 levels, prevent infinite recursion)
- Timeout and max_iterations enforcement
- Concurrent sub-agent execution via asyncio.TaskGroup

Architecture:
- Each sub-agent is a fully isolated Agent instance
- SubAgentPool manages lifecycle and resource limits
- Uses cancel_token (US1) for timeout enforcement
- Compatible with CompressionManager (US2)
"""

from __future__ import annotations

import asyncio
from typing import Dict, List, Optional
from uuid import uuid4

from loom.components.agent import Agent
from loom.core.types import Message
from loom.interfaces.llm import BaseLLM
from loom.interfaces.memory import BaseMemory
from loom.interfaces.tool import BaseTool


class MaxDepthError(Exception):
    """Raised when sub-agent execution depth exceeds maximum."""
    pass


class SubAgentPool:
    """Manages isolated sub-agent spawning and execution.

    Example:
        pool = SubAgentPool(max_depth=3)

        # Spawn sub-agent with tool whitelist
        result = await pool.spawn(
            llm=llm,
            prompt="Analyze dependencies",
            tool_whitelist=["read_file", "glob"],  # Only these tools
            timeout_seconds=60,
        )
    """

    def __init__(
        self,
        max_depth: int = 3,
        default_timeout: float = 300.0,  # 5 minutes
        default_max_iterations: int = 50,
    ):
        """Initialize SubAgentPool.

        Args:
            max_depth: Maximum execution depth (prevent infinite recursion)
            default_timeout: Default timeout in seconds for sub-agents
            default_max_iterations: Default max iterations for sub-agents
        """
        self.max_depth = max_depth
        self.default_timeout = default_timeout
        self.default_max_iterations = default_max_iterations
        self._active_subagents: Dict[str, Agent] = {}

    async def spawn(
        self,
        llm: BaseLLM,
        prompt: str,
        tools: Optional[List[BaseTool]] = None,
        tool_whitelist: Optional[List[str]] = None,
        memory: Optional[BaseMemory] = None,
        execution_depth: int = 1,
        timeout_seconds: Optional[float] = None,
        max_iterations: Optional[int] = None,
        system_instructions: Optional[str] = None,
    ) -> str:
        """Spawn an isolated sub-agent and execute task.

        Args:
            llm: LLM instance for sub-agent
            prompt: Task prompt for sub-agent
            tools: Available tools (will be filtered by whitelist)
            tool_whitelist: List of allowed tool names (None = all tools)
            memory: Memory instance (if None, sub-agent gets fresh memory)
            execution_depth: Current execution depth (for depth limit)
            timeout_seconds: Timeout in seconds (None = default)
            max_iterations: Max iterations (None = default)
            system_instructions: System instructions for sub-agent

        Returns:
            Final response from sub-agent

        Raises:
            MaxDepthError: If execution_depth > max_depth
            asyncio.TimeoutError: If sub-agent exceeds timeout
        """
        # Check depth limit
        if execution_depth > self.max_depth:
            raise MaxDepthError(
                f"Execution depth {execution_depth} exceeds maximum {self.max_depth}"
            )

        # Filter tools by whitelist
        filtered_tools = self._apply_tool_whitelist(tools, tool_whitelist)

        # Create isolated sub-agent (compression always enabled in v4.0.0)
        subagent_id = str(uuid4())
        subagent = Agent(
            llm=llm,
            tools=filtered_tools,
            memory=memory,  # Separate memory instance
            max_iterations=max_iterations or self.default_max_iterations,
            system_instructions=system_instructions,
        )

        # Register active sub-agent
        self._active_subagents[subagent_id] = subagent

        try:
            # Create cancel token for timeout enforcement
            cancel_token = asyncio.Event()
            timeout = timeout_seconds or self.default_timeout

            # Execute sub-agent with timeout
            task = asyncio.create_task(
                subagent.run(prompt, cancel_token=cancel_token, correlation_id=subagent_id)
            )

            # Wait with timeout
            result = await asyncio.wait_for(task, timeout=timeout)

            return result

        except asyncio.TimeoutError:
            # Cancel sub-agent on timeout
            cancel_token.set()
            raise

        finally:
            # Cleanup: Remove from active pool
            self._active_subagents.pop(subagent_id, None)

    def _apply_tool_whitelist(
        self,
        tools: Optional[List[BaseTool]],
        whitelist: Optional[List[str]],
    ) -> Optional[List[BaseTool]]:
        """Filter tools by whitelist.

        Args:
            tools: All available tools
            whitelist: List of allowed tool names (None = all tools)

        Returns:
            Filtered list of tools
        """
        if tools is None or whitelist is None:
            return tools

        # Filter tools to only whitelisted ones
        filtered = [tool for tool in tools if tool.name in whitelist]

        return filtered if filtered else None

    async def spawn_many(
        self,
        llm: BaseLLM,
        prompts: List[str],
        tools: Optional[List[BaseTool]] = None,
        tool_whitelist: Optional[List[str]] = None,
        timeout_seconds: Optional[float] = None,
        return_exceptions: bool = True,
    ) -> List[str]:
        """Spawn multiple sub-agents concurrently.

        Args:
            llm: LLM instance (shared across sub-agents)
            prompts: List of task prompts
            tools: Available tools
            tool_whitelist: Tool whitelist (applied to all sub-agents)
            timeout_seconds: Timeout per sub-agent
            return_exceptions: If True, return exceptions instead of raising

        Returns:
            List of results (or exceptions if return_exceptions=True)

        Example:
            prompts = ["Analyze file1.py", "Analyze file2.py", "Analyze file3.py"]
            results = await pool.spawn_many(llm, prompts, tools=tools)
        """
        tasks = [
            self.spawn(
                llm=llm,
                prompt=prompt,
                tools=tools,
                tool_whitelist=tool_whitelist,
                timeout_seconds=timeout_seconds,
            )
            for prompt in prompts
        ]

        results = await asyncio.gather(*tasks, return_exceptions=return_exceptions)

        return results

    def get_active_count(self) -> int:
        """Get number of currently active sub-agents."""
        return len(self._active_subagents)

    async def cancel_all(self) -> None:
        """Cancel all active sub-agents.

        Note: This is a best-effort cancellation. Sub-agents may not
        respond immediately to cancellation signals.
        """
        for subagent_id, subagent in list(self._active_subagents.items()):
            # Set cancel token (if sub-agent supports steering)
            if hasattr(subagent.executor, "steering_control"):
                subagent.executor.steering_control.abort()

        # Wait a moment for cancellations to propagate
        await asyncio.sleep(0.1)

        # Clear active pool
        self._active_subagents.clear()
