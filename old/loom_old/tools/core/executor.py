"""
Tool Executor - 工具执行引擎

基于第一性原理简化的工具执行引擎。

简化原则：
1. 移除去重机制（增加复杂度，收益有限）
2. 移除缓存机制（增加复杂度，收益有限）
3. 简化Barrier分组逻辑
4. 保留只读判断和并行/串行执行
5. 支持沙盒工具管理器（SandboxedExecutor）
"""

import asyncio
import re
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Any

# Optional import for SandboxToolManager
try:
    from loom.tools.core.sandbox_manager import SandboxToolManager, ToolScope
except ImportError:
    SandboxToolManager = None  # type: ignore
    ToolScope = None  # type: ignore


@dataclass
class ToolExecutionResult:
    """工具执行结果"""

    index: int
    name: str
    result: Any
    error: bool = False


class ToolExecutor:
    """
    工具执行引擎

    功能：
    - 判断工具是否只读
    - 并行执行只读工具
    - 串行执行有副作用的工具
    """

    def __init__(self, parallel_execution: bool = True):
        """
        初始化工具执行引擎

        Args:
            parallel_execution: 是否启用并行执行
        """
        self.parallel_execution = parallel_execution

        # 只读工具的正则模式
        self.read_only_patterns = [
            r"^read_",
            r"^get_",
            r"^list_",
            r"^ls",
            r"^grep",
            r"^find",
            r"^search",
            r"^query",
            r"^fetch",
            r"^view",
        ]

    def is_read_only(self, tool_name: str) -> bool:
        """
        判断工具是否只读

        Args:
            tool_name: 工具名称

        Returns:
            是否只读
        """
        for pattern in self.read_only_patterns:
            if re.match(pattern, tool_name, re.IGNORECASE):
                return True
        return False

    async def execute_batch(
        self,
        tool_calls: list[dict[str, Any]],
        executor_func: Callable[[str, dict], Coroutine[Any, Any, Any]],
    ) -> list[ToolExecutionResult]:
        """
        批量执行工具调用

        Args:
            tool_calls: 工具调用列表，每个元素包含'name'和'arguments'
            executor_func: 执行函数，接收(name, args)返回结果

        Returns:
            执行结果列表
        """
        if not tool_calls:
            return []

        # 1. 分组：将工具分为只读组和写入组
        groups: list[list[tuple[int, dict]]] = []
        current_group: list[tuple[int, dict]] = []
        is_current_read = None

        for idx, call in enumerate(tool_calls):
            name = call.get("name", "")
            is_read = self.is_read_only(name)

            # 如果禁用并行执行，每个工具单独一组
            if not self.parallel_execution:
                groups.append([(idx, call)])
                continue

            # 根据只读/写入分组
            if is_read:
                # 只读工具
                if current_group and not is_current_read:
                    # 当前组是写入组，关闭它
                    groups.append(current_group)
                    current_group = []

                current_group.append((idx, call))
                is_current_read = True
            else:
                # 写入工具
                if current_group:
                    # 关闭当前组
                    groups.append(current_group)
                    current_group = []

                # 写入工具单独一组（串行执行）
                groups.append([(idx, call)])
                is_current_read = False

        if current_group:
            groups.append(current_group)

        # 2. 执行各组
        results_map: dict[int, ToolExecutionResult] = {}

        for group in groups:
            # 判断是否可以并行执行
            first_idx, first_call = group[0]
            first_name = first_call.get("name", "")
            is_read_group = self.is_read_only(first_name) and self.parallel_execution

            if is_read_group and len(group) > 1:
                # 并行执行只读组
                tasks = [self._safe_execute(idx, call, executor_func) for idx, call in group]
                group_results = await asyncio.gather(*tasks)
                for result in group_results:
                    results_map[result.index] = result
            else:
                # 串行执行
                for idx, call in group:
                    result = await self._safe_execute(idx, call, executor_func)
                    results_map[result.index] = result

        # 3. 按原始顺序返回结果
        return [results_map[i] for i in range(len(tool_calls))]

    async def _safe_execute(
        self,
        idx: int,
        call: dict[str, Any],
        executor_func: Callable[[str, dict], Coroutine[Any, Any, Any]],
    ) -> ToolExecutionResult:
        """
        安全执行单个工具调用

        Args:
            idx: 工具调用索引
            call: 工具调用字典
            executor_func: 执行函数

        Returns:
            工具执行结果
        """
        name = call.get("name", "")
        args = call.get("arguments", {})

        try:
            result = await executor_func(name, args)
            return ToolExecutionResult(
                index=idx,
                name=name,
                result=result,
                error=False,
            )
        except Exception as e:
            return ToolExecutionResult(
                index=idx,
                name=name,
                result=str(e),
                error=True,
            )


class SandboxedExecutor:
    """
    沙盒感知的工具执行器

    使用 SandboxToolManager 来执行工具，自动根据工具作用域应用安全策略。

    功能：
    - 自动注入沙盒到 SANDBOXED 作用域的工具
    - 通过 MCP 适配器执行 MCP 工具
    - 直接执行 SYSTEM 和 CONTEXT 工具
    - 发布工具执行事件
    """

    def __init__(
        self,
        manager: "SandboxToolManager",
        parallel_execution: bool = True,
    ):
        """
        初始化沙盒执行器

        Args:
            manager: 沙盒工具管理器实例
            parallel_execution: 是否启用并行执行
        """
        if SandboxToolManager is None:
            raise ImportError("SandboxToolManager is not available")

        self.manager = manager
        self.parallel_execution = parallel_execution
        self._tool_executor = ToolExecutor(parallel_execution=parallel_execution)

    async def execute(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """
        执行单个工具

        Args:
            tool_name: 工具名称
            arguments: 工具参数

        Returns:
            工具执行结果

        Raises:
            ValueError: 工具不存在
        """
        # 检查工具是否存在于管理器中
        if tool_name not in self.manager:
            raise ValueError(f"Tool not found: {tool_name}")

        # 通过管理器执行工具
        return await self.manager.execute_tool(tool_name, arguments)

    async def execute_batch(
        self,
        tool_calls: list[dict[str, Any]],
    ) -> list[ToolExecutionResult]:
        """
        批量执行工具调用

        Args:
            tool_calls: 工具调用列表，每个元素包含'name'和'arguments'

        Returns:
            执行结果列表
        """
        if not tool_calls:
            return []

        # 使用内部 ToolExecutor 进行批量执行
        # 但执行函数委托给 manager.execute_tool
        async def executor_func(name: str, args: dict) -> Any:
            return await self.manager.execute_tool(name, args)

        return await self._tool_executor.execute_batch(tool_calls, executor_func)

    def list_tools(self) -> list[Any]:
        """
        列出所有已注册的工具

        Returns:
            工具定义列表
        """
        return self.manager.list_tools()

    def list_tool_names(self) -> list[str]:
        """
        列出所有已注册的工具名称

        Returns:
            工具名称列表
        """
        return self.manager.list_tool_names()

    def get_tools_by_scope(self, scope: "ToolScope") -> list[Any]:
        """
        按作用域获取工具

        Args:
            scope: 工具作用域

        Returns:
            该作用域下的所有工具
        """
        return self.manager.get_tools_by_scope(scope)
