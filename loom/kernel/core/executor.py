"""
Tool Execution Engine.
Handles parallel execution of read-only tools and sequential execution of side-effect tools.
"""

import asyncio
import hashlib
import json
import re
import time
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Any

from loom.config.execution import ExecutionConfig


@dataclass
class ToolExecutionResult:
    index: int
    name: str
    result: Any
    error: bool = False

class ToolExecutor:
    """
    Orchestrates the execution of multiple tool calls.
    Updates AgentNode logic to support barrier-based parallelism.
    """

    def __init__(
        self,
        config: ExecutionConfig,
        read_only_check: Callable[[str], bool] | None = None
    ):
        self.config = config
        self.custom_read_only_check = read_only_check

        # Heuristic patterns for read-only tools
        self.read_only_patterns = [
            r"^read_", r"^get_", r"^list_", r"^ls", r"^grep", r"^find",
            r"^search", r"^query", r"^fetch", r"^view"
        ]

        # Tool result caching
        self.result_cache: dict[str, Any] = {}
        self.cache_timestamps: dict[str, float] = {}
        self.cache_ttl: float = 300.0  # 5 minutes default
        self.enable_cache: bool = True

    def is_read_only(self, tool_name: str) -> bool:
        """Determine if a tool is safe to execute in parallel."""
        # Use custom check if provided
        if self.custom_read_only_check:
            return self.custom_read_only_check(tool_name)

        # Fallback to patterns
        for pattern in self.read_only_patterns:
            if re.match(pattern, tool_name, re.IGNORECASE):
                return True
        return False

    def _deduplicate_calls(
        self,
        tool_calls: list[dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], dict[int, int]]:
        """
        Remove duplicate tool calls, return unique calls and index mapping.

        Args:
            tool_calls: List of tool call dicts

        Returns:
            Tuple of (unique_calls, index_map) where index_map maps
            original_idx -> unique_idx
        """
        seen = {}
        unique_calls = []
        index_map = {}  # original_idx -> unique_idx

        for idx, call in enumerate(tool_calls):
            name = call.get("name", "")
            args = call.get("arguments", {})

            # Create hashable key from name and args
            try:
                args_items = tuple(sorted(args.items())) if args else ()
                key = (name, args_items)
            except (TypeError, AttributeError):
                # If args not hashable, treat as unique
                key = (name, id(args))

            if key in seen:
                # Duplicate found, map to existing unique index
                index_map[idx] = seen[key]
            else:
                # New unique call
                unique_idx = len(unique_calls)
                seen[key] = unique_idx
                index_map[idx] = unique_idx
                unique_calls.append(call)

        return unique_calls, index_map

    async def execute_batch(
        self,
        tool_calls: list[dict[str, Any]],
        executor_func: Callable[[str, dict], Coroutine[Any, Any, Any]]
    ) -> list[ToolExecutionResult]:
        """
        Execute a batch of tool calls respecting read/write barriers.

        Args:
            tool_calls: List of dicts with 'name' and 'arguments'.
            executor_func: Async function (name, args) -> result.

        Returns:
            List of results mapped back to original order.
        """
        if not tool_calls:
            return []

        # 0. Deduplicate tool calls
        unique_calls, index_map = self._deduplicate_calls(tool_calls)
        has_duplicates = len(unique_calls) < len(tool_calls)

        # Work with unique calls for execution
        calls_to_execute = unique_calls

        # 1. Group tasks into Barriers
        # e.g. [R1, R2, W1, R3, R4] -> [[R1, R2], [W1], [R3, R4]]
        groups: list[list[tuple[int, dict]]] = []
        current_group: list[tuple[int, dict]] = []
        is_current_read = None

        for idx, call in enumerate(calls_to_execute):
            name = call.get("name", "")
            is_read = self.is_read_only(name)

            # If parallel execution is disabled, everything is sequential (effectively separate groups or one big sequential loop)
            # But the logic here specifically groups "parallelizable" vs "must-be-isolated"
            # Actually, to be safe: Reads can be grouped. Writes must be isolated (sequential).

            if not self.config.parallel_execution:
                # Treat everything as isolated
                groups.append([(idx, call)])
                continue

            if is_read:
                # It's a read tool.
                if current_group and not is_current_read:
                    # Current group was Write, close it.
                    groups.append(current_group)
                    current_group = []

                # Add to (or start) Read group
                current_group.append((idx, call))
                is_current_read = True
            else:
                # It's a write tool.
                if current_group:
                    # Close previous group (whether Read or Write)
                    groups.append(current_group)
                    current_group = []

                # Write tools must be isolated (sequential barrier)
                # But actually, if we have [W1, W2], can they run together? No. Side effects order matters.
                # So W1 is its own group.
                groups.append([(idx, call)])
                is_current_read = False # Reset

        if current_group:
            groups.append(current_group)

        # 2. Execute Groups
        results_map: dict[int, Any] = {}

        for group in groups:
            # Check if group is parallelizable (Read group with >1 items)
            # Actually if it's a Read group, even size 1, we can use gather (no harm).
            # Write groups are size 1.

            first_idx, first_call = group[0]
            first_name = first_call.get("name", "")
            is_read_group = self.is_read_only(first_name) if self.config.parallel_execution else False

            if is_read_group and len(group) > 0:
                # Parallel Execution
                tasks = []
                for idx, call in group:
                    tasks.append(self._safe_execute(idx, call, executor_func))

                group_results = await asyncio.gather(*tasks)
                for res in group_results:
                     results_map[res.index] = res
            else:
                # Sequential Execution
                for idx, call in group:
                    res = await self._safe_execute(idx, call, executor_func)
                    results_map[res.index] = res

        # 3. Reconstruct Result List
        final_results = []

        if has_duplicates:
            # Map unique results back to original indices
            for orig_idx in range(len(tool_calls)):
                unique_idx = index_map[orig_idx]
                if unique_idx in results_map:
                    unique_result = results_map[unique_idx]
                    # Create result with original index
                    final_results.append(ToolExecutionResult(
                        orig_idx,
                        unique_result.name,
                        unique_result.result,
                        unique_result.error
                    ))
                else:
                    final_results.append(ToolExecutionResult(orig_idx, "unknown", "Error: Missing Result", True))
        else:
            # No duplicates, return results as-is
            for idx in range(len(tool_calls)):
                if idx in results_map:
                    final_results.append(results_map[idx])
                else:
                    final_results.append(ToolExecutionResult(idx, "unknown", "Error: Missing Result", True))

        return final_results

    def _generate_cache_key(self, tool_name: str, args: dict[str, Any]) -> str:
        """Generate a cache key from tool name and arguments."""
        try:
            # Sort args for consistent hashing
            args_str = json.dumps(args, sort_keys=True)
            key_str = f"{tool_name}:{args_str}"
            return hashlib.md5(key_str.encode()).hexdigest()
        except Exception:
            # Fallback if args not serializable
            return f"{tool_name}:{str(args)}"

    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached result is still valid (within TTL)."""
        if cache_key not in self.cache_timestamps:
            return False
        age = time.time() - self.cache_timestamps[cache_key]
        return age < self.cache_ttl

    def _clear_expired_cache(self):
        """Remove expired entries from cache."""
        current_time = time.time()
        expired_keys = [
            key for key, timestamp in self.cache_timestamps.items()
            if current_time - timestamp >= self.cache_ttl
        ]
        for key in expired_keys:
            self.result_cache.pop(key, None)
            self.cache_timestamps.pop(key, None)

    async def _safe_execute_with_retry(
        self,
        index: int,
        call: dict,
        executor_func: Callable,
        max_retries: int = 2
    ) -> ToolExecutionResult:
        """
        Execute tool with automatic retry and error recovery.

        Args:
            index: Tool call index
            call: Tool call dict with name and arguments
            executor_func: Function to execute the tool
            max_retries: Maximum number of retry attempts

        Returns:
            ToolExecutionResult
        """
        import os

        for attempt in range(max_retries + 1):
            try:
                # Execute using the standard method
                result = await self._safe_execute(index, call, executor_func)

                # If no error, return immediately
                if not result.error:
                    return result

                # If error and no more retries, return error result
                if attempt >= max_retries:
                    return result

            except FileNotFoundError:
                if attempt < max_retries:
                    # Try with absolute path
                    if "arguments" in call and "path" in call["arguments"]:
                        original_path = call["arguments"]["path"]
                        call["arguments"]["path"] = os.path.abspath(original_path)
                        continue
                raise

            except PermissionError:
                # Don't retry permission errors
                raise

            except Exception:
                if attempt < max_retries:
                    # Exponential backoff
                    await asyncio.sleep(0.5 * (attempt + 1))
                    continue
                raise

        # Should not reach here, but return error result as fallback
        return ToolExecutionResult(index, call.get("name", "unknown"),
                                   "Max retries exceeded", error=True)

    async def _safe_execute(
        self,
        index: int,
        call: dict,
        executor_func: Callable
    ) -> ToolExecutionResult:
        name = call.get("name")
        args = call.get("arguments") or {}

        # Check cache for read-only tools
        if self.enable_cache and self.is_read_only(name):
            cache_key = self._generate_cache_key(name, args)

            # Check if cached result is valid
            if self._is_cache_valid(cache_key):
                cached_result = self.result_cache.get(cache_key)
                if cached_result is not None:
                    return ToolExecutionResult(index, name, cached_result, error=False)

        # Execute tool
        try:
            val = await executor_func(name, args)

            # Cache result for read-only tools
            if self.enable_cache and self.is_read_only(name):
                cache_key = self._generate_cache_key(name, args)
                self.result_cache[cache_key] = val
                self.cache_timestamps[cache_key] = time.time()

                # Periodically clear expired cache
                if len(self.result_cache) % 50 == 0:
                    self._clear_expired_cache()

            return ToolExecutionResult(index, name, val, error=False)
        except Exception as e:
            # Fallback if executor_func raises unhandled exception
            return ToolExecutionResult(index, name, f"Executor Error: {e}", error=True)
