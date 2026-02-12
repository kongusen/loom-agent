"""
CapabilityRegistry - 统一的能力管理门面

基于优化方案（OPTIMIZATION_PLAN.md）第2.4节设计

核心原则：
1. 门面模式 - 不创建新系统，作为现有系统的统一门面
2. 复用现有组件 - 内部使用 SandboxToolManager + SkillRegistry + SkillActivator
3. 统一发现 - 提供统一的能力发现接口
4. 依赖验证 - 验证 Skill 的工具依赖（新增功能）

职责：
- 统一的能力发现接口
- 依赖验证（新增功能）
- 内部复用现有组件
"""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from loom.tools.core.converters import FunctionToMCP
from loom.tools.mcp_types import MCPToolDefinition


@dataclass
class CapabilitySet:
    """
    能力集合

    包含相关的 Tools 和 Skills
    """

    tools: list[dict[str, Any]] = field(default_factory=list)
    skill_ids: list[str] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.tools) + len(self.skill_ids)

    def is_empty(self) -> bool:
        return len(self.tools) == 0 and len(self.skill_ids) == 0


@dataclass
class ValidationResult:
    """
    依赖验证结果

    用于验证 Skill 的工具依赖是否满足
    """

    is_valid: bool
    missing_tools: list[str] = field(default_factory=list)
    error: str = ""
    can_autofix: bool = False

    def __bool__(self) -> bool:
        return self.is_valid


class CapabilityRegistry:
    """
    能力注册表 - 门面模式

    职责：
    1. 统一的能力发现接口
    2. 依赖验证（新增功能）
    3. 内部复用现有组件

    不负责：
    - 工具执行（由 ToolExecutor 负责）
    - Skill 实例化（由 Skill.instantiate() 负责）
    """

    def __init__(
        self,
        sandbox_manager: Any = None,  # SandboxToolManager
        skill_registry: Any = None,  # SkillRegistry
        skill_activator: Any = None,  # SkillActivator
    ):
        """
        初始化能力注册表

        Args:
            sandbox_manager: SandboxToolManager 实例（复用现有）
            skill_registry: SkillRegistry 实例（复用现有）
            skill_activator: SkillActivator 实例（复用现有）
        """
        # 复用现有组件，不创建新的
        self._tool_manager = sandbox_manager
        self._skill_registry = skill_registry
        self._skill_activator = skill_activator

    @property
    def tool_manager(self) -> Any:
        """获取工具管理器（SandboxToolManager）"""
        return self._tool_manager

    @property
    def skill_registry(self) -> Any:
        """获取技能注册表（SkillRegistry）"""
        return self._skill_registry

    @property
    def skill_activator(self) -> Any:
        """获取技能激活器（SkillActivator）"""
        return self._skill_activator

    async def find_relevant_capabilities(
        self,
        task_description: str,
    ) -> CapabilitySet:
        """
        统一的能力发现接口（支持 Loader + 运行时 Skill）

        根据任务描述，发现相关的 Tools 和 Skills。

        Args:
            task_description: 任务描述

        Returns:
            CapabilitySet: 包含相关 Tools 和 Skills 的能力集合
        """
        capabilities = CapabilitySet()

        # 提取任务描述中的关键词（用于相关性过滤）
        keywords = set(task_description.lower().split()) if task_description else set()

        # 1. 从 SandboxToolManager 获取相关工具
        if self._tool_manager:
            try:
                tool_definitions = self._tool_manager.list_tools()
                for tool in tool_definitions:
                    # 如果没有关键词，返回所有工具；否则按相关性过滤
                    if not keywords or self._is_relevant(tool.name, tool.description, keywords):
                        capabilities.tools.append(
                            {
                                "name": tool.name,
                                "description": tool.description,
                                "input_schema": tool.input_schema,
                            }
                        )
            except Exception:
                capabilities.tools = []

        # 2. 从 SkillRegistry 获取 Skill IDs（统一：运行时 + Loaders）
        if self._skill_registry:
            try:
                if hasattr(self._skill_registry, "list_skills_async"):
                    capabilities.skill_ids = await self._skill_registry.list_skills_async()
                else:
                    capabilities.skill_ids = self._skill_registry.list_skills()
            except Exception:
                capabilities.skill_ids = []

        return capabilities

    def _is_relevant(self, name: str, description: str, keywords: set[str]) -> bool:
        """
        判断工具是否与关键词相关

        Args:
            name: 工具名称
            description: 工具描述
            keywords: 关键词集合

        Returns:
            是否相关
        """
        text = f"{name} {description}".lower()
        # 任意关键词匹配即认为相关（长度 > 2 的词）
        return any(kw in text for kw in keywords if len(kw) > 2)

    async def validate_skill_dependencies(
        self,
        skill_id: str,
    ) -> ValidationResult:
        """
        验证 Skill 的工具依赖（统一 SkillRegistry：Loader 或运行时 dict）

        检查 Skill 所需的工具是否都可用。

        Args:
            skill_id: Skill ID

        Returns:
            ValidationResult: 验证结果
        """
        if not self._skill_registry:
            return ValidationResult(
                is_valid=False,
                error="SkillRegistry not available",
            )

        # 获取 Skill 定义（统一：async get_skill 支持 Loader + 运行时）
        try:
            get_skill_fn = getattr(self._skill_registry, "get_skill", None)
            if get_skill_fn and asyncio.iscoroutinefunction(get_skill_fn):
                skill_def = await get_skill_fn(skill_id)
            elif hasattr(self._skill_registry, "get_skill_sync"):
                skill_def = self._skill_registry.get_skill_sync(skill_id)
            else:
                skill_def = get_skill_fn(skill_id) if get_skill_fn else None
            if not skill_def:
                return ValidationResult(
                    is_valid=False,
                    error=f"Skill '{skill_id}' not found",
                )
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                error=f"Failed to get skill: {e}",
            )

        # 提取工具依赖：SkillDefinition 或 dict（_metadata.required_tools）
        required_tools: list[str] = []
        if hasattr(skill_def, "required_tools"):
            required_tools = list(skill_def.required_tools)
        elif isinstance(skill_def, dict) and isinstance(skill_def.get("_metadata"), dict):
            required_tools = skill_def["_metadata"].get("required_tools", [])

        if not required_tools:
            return ValidationResult(is_valid=True)

        if not self._tool_manager:
            return ValidationResult(
                is_valid=False,
                missing_tools=required_tools,
                error="ToolManager not available",
            )

        try:
            tool_definitions = self._tool_manager.list_tools()
            available_tool_names = {tool.name for tool in tool_definitions}
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                missing_tools=required_tools,
                error=f"Failed to get available tools: {e}",
            )

        missing_tools = [t for t in required_tools if t not in available_tool_names]
        if missing_tools:
            return ValidationResult(
                is_valid=False,
                missing_tools=missing_tools,
                error=f"Missing required tools: {', '.join(missing_tools)}",
                can_autofix=False,
            )
        return ValidationResult(is_valid=True)

    async def inject_skills(
        self,
        skill_ids: list[str],
        system_prompt: str,
    ) -> str:
        """
        将 Skills 注入到 system_prompt

        这是简化后的激活方法，替代原有的 SkillActivator。
        只支持 INJECTION 模式。

        Args:
            skill_ids: 要注入的 Skill ID 列表
            system_prompt: 原始 system_prompt

        Returns:
            注入 Skills 后的 system_prompt
        """
        if not self._skill_registry:
            return system_prompt

        injected_prompt = system_prompt
        for skill_id in skill_ids:
            try:
                # 获取 Skill 定义
                get_skill_fn = getattr(self._skill_registry, "get_skill", None)
                if get_skill_fn and asyncio.iscoroutinefunction(get_skill_fn):
                    skill_def = await get_skill_fn(skill_id)
                else:
                    skill_def = get_skill_fn(skill_id) if get_skill_fn else None

                if skill_def:
                    # 使用 get_injection_content 方法获取注入内容
                    if hasattr(skill_def, "get_injection_content"):
                        content = skill_def.get_injection_content()
                    elif hasattr(skill_def, "get_full_instructions"):
                        content = skill_def.get_full_instructions()
                    else:
                        continue

                    injected_prompt += f"\n\n{content}"
            except Exception:
                # 静默跳过失败的 Skill
                continue

        return injected_prompt


# ==================== ToolRegistry (兼容旧 API) ====================


class ToolRegistry:
    """
    工具注册表

    管理所有可用工具的定义和可调用对象。
    """

    def __init__(self):
        """初始化工具注册表"""
        self._tools: dict[str, Callable] = {}
        self._definitions: dict[str, MCPToolDefinition] = {}

    def register_function(self, func: Callable, name: str | None = None) -> MCPToolDefinition:
        """
        注册Python函数为工具

        Args:
            func: Python函数
            name: 工具名称（可选，默认使用函数名）

        Returns:
            MCP工具定义
        """
        tool_name = name or func.__name__
        definition = FunctionToMCP.convert(func, name=tool_name)
        self._tools[tool_name] = func
        self._definitions[tool_name] = definition
        return definition

    def get_definition(self, name: str) -> MCPToolDefinition | None:
        """获取工具定义"""
        return self._definitions.get(name)

    def get_callable(self, name: str) -> Callable | None:
        """获取工具的可调用对象"""
        return self._tools.get(name)

    def has(self, name: str) -> bool:
        """检查工具是否存在"""
        return name in self._tools

    @property
    def definitions(self) -> list[MCPToolDefinition]:
        """获取所有工具定义"""
        return list(self._definitions.values())

    @property
    def tool_names(self) -> list[str]:
        """获取所有工具名称"""
        return list(self._tools.keys())
