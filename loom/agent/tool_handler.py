"""
ToolHandlerMixin - 工具管理

处理工具注册、执行、列表构建等功能。

从 core.py 拆分，遵循单一职责原则。
"""

from typing import TYPE_CHECKING, Any

from loom.exceptions import PermissionDenied

if TYPE_CHECKING:
    from loom.tools.sandbox_manager import SandboxToolManager


class ToolHandlerMixin:
    """
    工具处理混入类

    提供工具相关的所有功能：
    - 工具列表构建
    - 工具执行
    - 动态工具管理
    - Ephemeral 消息处理
    """

    # 类型提示（由 Agent 类提供）
    tools: list[dict[str, Any]]
    all_tools: list[dict[str, Any]]
    tool_registry: Any
    sandbox_manager: "SandboxToolManager | None"
    tool_policy: Any
    config: Any
    _context_tool_executor: Any
    _dynamic_tool_executor: Any
    _pending_tool_callables: list[Any]

    def _get_available_tools(self) -> list[dict[str, Any]]:
        """
        获取当前可用的工具列表（动态）

        来源：
        1. 基础工具（self.tools）
        2. 已激活 Skills 绑定的工具（通过 sandbox_manager）
        3. 额外配置的工具（config.extra_tools）

        排除：
        - config.disabled_tools 中的工具
        """
        available = []
        tool_names_seen: set[str] = set()

        # 1. 基础工具
        for tool in self.tools:
            if not isinstance(tool, dict):
                continue
            tool_name = tool.get("function", {}).get("name")
            if tool_name and tool_name not in tool_names_seen:
                available.append(tool)
                tool_names_seen.add(tool_name)

        # 2. 额外配置的工具（从 tool_registry）
        if self.tool_registry and self.config.extra_tools:
            for tool_name in self.config.extra_tools:
                if tool_name not in tool_names_seen:
                    tool_def = self.tool_registry.get_definition(tool_name)
                    if tool_def:
                        available.append(
                            {
                                "type": "function",
                                "function": {
                                    "name": tool_def.name,
                                    "description": tool_def.description,
                                    "parameters": tool_def.input_schema,
                                },
                            }
                        )
                        tool_names_seen.add(tool_name)

        # 3. 沙盒工具
        if self.sandbox_manager:
            for mcp_def in self.sandbox_manager.list_tools():
                if mcp_def.name not in tool_names_seen:
                    tool_names_seen.add(mcp_def.name)
                    available.append(
                        {
                            "type": "function",
                            "function": {
                                "name": mcp_def.name,
                                "description": mcp_def.description,
                                "parameters": mcp_def.input_schema,
                            },
                        }
                    )

        # 过滤禁用的工具
        if self.config.disabled_tools:
            available = [
                tool
                for tool in available
                if isinstance(tool, dict)
                and tool.get("function", {}).get("name") not in self.config.disabled_tools
            ]

        return available

    async def _execute_single_tool(self, tool_name: str, tool_args: dict | str) -> str:
        """
        执行单个工具

        Args:
            tool_name: 工具名称
            tool_args: 工具参数（可能是dict或JSON字符串）

        Returns:
            工具执行结果
        """
        import json

        from loom.security import ToolContext
        from loom.tools.tool_creation import ToolCreationError

        # 权限检查
        if self.tool_policy:
            # 解析参数用于权限检查
            if isinstance(tool_args, str):
                try:
                    check_args = json.loads(tool_args)
                except json.JSONDecodeError:
                    check_args = {}
            elif isinstance(tool_args, dict):
                check_args = tool_args
            else:
                check_args = {}

            context = ToolContext(tool_name=tool_name, tool_args=check_args)
            if not self.tool_policy.is_allowed(context):
                reason = self.tool_policy.get_denial_reason(context)
                raise PermissionDenied(tool_name=tool_name, reason=reason)

        # 解析参数
        if isinstance(tool_args, str):
            try:
                parsed_args: dict[str, Any] = json.loads(tool_args)
            except json.JSONDecodeError:
                return f"错误：无法解析工具参数 - {tool_args}"
        elif isinstance(tool_args, dict):
            parsed_args = tool_args
        else:
            parsed_args = {}

        # 工具创建调用
        if tool_name == "create_tool" and self._dynamic_tool_executor:
            try:
                result = await self._dynamic_tool_executor.create_tool(
                    tool_name=parsed_args.get("tool_name", ""),
                    description=parsed_args.get("description", ""),
                    parameters=parsed_args.get("parameters", {}),
                    implementation=parsed_args.get("implementation", ""),
                )
                self.all_tools = self._build_tool_list()
                return str(result)
            except ToolCreationError as e:
                return f"工具创建失败: {str(e)}"
            except Exception as e:
                return f"工具创建错误: {str(e)}"

        # 动态创建的工具
        if self._dynamic_tool_executor and tool_name in self._dynamic_tool_executor.created_tools:
            try:
                result = await self._dynamic_tool_executor.execute_tool(tool_name, **parsed_args)
                return str(result)
            except Exception as e:
                return f"动态工具执行错误: {str(e)}"

        # 上下文查询工具
        context_tool_names = {
            "query_l1_memory",
            "query_l2_memory",
            "query_l3_memory",
            "query_l4_memory",
            "query_events_by_action",
            "query_events_by_node",
            "query_events_by_target",
            "query_recent_events",
            "query_thinking_process",
        }
        if tool_name in context_tool_names and self._context_tool_executor:
            try:
                result = await self._context_tool_executor.execute(tool_name, parsed_args)
                return json.dumps(result, ensure_ascii=False, default=str)
            except Exception as e:
                return f"错误：上下文工具执行失败 - {str(e)}"

        # 沙盒工具
        if self.sandbox_manager and tool_name in self.sandbox_manager:
            try:
                result = await self.sandbox_manager.execute_tool(tool_name, parsed_args)
                return str(result)
            except Exception as e:
                return f"错误：沙盒工具执行失败 - {str(e)}"

        # 注册表工具
        if self.tool_registry is None:
            return f"错误：工具 '{tool_name}' 未找到（工具注册表未初始化）"

        tool_func = self.tool_registry.get_callable(tool_name)
        if tool_func is None:
            return f"错误：工具 '{tool_name}' 未找到"

        try:
            result = await tool_func(**parsed_args)
            return str(result)
        except Exception as e:
            return f"错误：工具执行失败 - {str(e)}"

    def _build_tool_list(self) -> list[dict[str, Any]]:
        """构建完整工具列表（普通工具 + 元工具）"""
        from loom.agent.delegator import create_delegate_task_tool
        from loom.agent.planner import create_plan_tool
        from loom.tools.context_tools import create_all_context_tools
        from loom.tools.tool_creation import create_tool_creation_tool

        tools = self._get_available_tools()

        # 规划元工具
        tools.append(create_plan_tool())

        # 委派元工具
        tools.append(create_delegate_task_tool())

        # 上下文查询工具
        if self._context_tool_executor:
            tools.extend(create_all_context_tools())

        # 工具创建元工具
        tools.append(create_tool_creation_tool())
        tools.extend(self._dynamic_tool_executor.get_tool_definitions())

        return tools
