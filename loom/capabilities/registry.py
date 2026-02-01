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

from dataclasses import dataclass, field
from typing import Any


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

    def find_relevant_capabilities(
        self,
        task_description: str,
        context: dict[str, Any] | None = None,
    ) -> CapabilitySet:
        """
        统一的能力发现接口

        根据任务描述，发现相关的 Tools 和 Skills

        Args:
            task_description: 任务描述
            context: 可选的上下文信息

        Returns:
            CapabilitySet: 包含相关 Tools 和 Skills 的能力集合
        """
        capabilities = CapabilitySet()

        # 1. 从 SandboxToolManager 获取相关工具
        if self._tool_manager:
            try:
                # 获取所有可用工具（返回 MCPToolDefinition 列表）
                tool_definitions = self._tool_manager.list_tools()
                # 转换为 dict 格式
                capabilities.tools = [
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "input_schema": tool.inputSchema,
                    }
                    for tool in tool_definitions
                ]
            except Exception:
                # 如果获取失败，返回空列表
                capabilities.tools = []

        # 2. 从 SkillRegistry 获取相关 Skills
        if self._skill_registry:
            try:
                # 获取所有已注册的 Skill IDs
                all_skill_ids = self._skill_registry.list_skills()
                # TODO: 实现基于任务描述的 Skill 过滤逻辑
                # 目前返回所有 Skills
                capabilities.skill_ids = all_skill_ids
            except Exception:
                # 如果获取失败，返回空列表
                capabilities.skill_ids = []

        return capabilities

    def validate_skill_dependencies(
        self,
        skill_id: str,
    ) -> ValidationResult:
        """
        验证 Skill 的工具依赖

        检查 Skill 所需的工具是否都可用（新增功能）

        Args:
            skill_id: Skill ID

        Returns:
            ValidationResult: 验证结果
        """
        # 1. 检查 skill_registry 是否可用
        if not self._skill_registry:
            return ValidationResult(
                is_valid=False,
                error="SkillRegistry not available",
            )

        # 2. 获取 Skill 定义
        try:
            skill_def = self._skill_registry.get_skill(skill_id)
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

        # 3. 提取 Skill 的工具依赖
        # Skill 定义是 dict 格式，metadata 存储在 _metadata 字段
        required_tools: list[str] = []
        if isinstance(skill_def, dict) and "_metadata" in skill_def:
            metadata = skill_def["_metadata"]
            if isinstance(metadata, dict):
                required_tools = metadata.get("required_tools", [])

        # 如果没有工具依赖，直接返回成功
        if not required_tools:
            return ValidationResult(is_valid=True)

        # 4. 检查工具是否可用
        if not self._tool_manager:
            return ValidationResult(
                is_valid=False,
                missing_tools=required_tools,
                error="ToolManager not available",
            )

        # 5. 获取可用工具列表
        try:
            tool_definitions = self._tool_manager.list_tools()
            available_tool_names = {tool.name for tool in tool_definitions}
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                missing_tools=required_tools,
                error=f"Failed to get available tools: {e}",
            )

        # 6. 检查缺失的工具
        missing_tools = [tool for tool in required_tools if tool not in available_tool_names]

        if missing_tools:
            return ValidationResult(
                is_valid=False,
                missing_tools=missing_tools,
                error=f"Missing required tools: {', '.join(missing_tools)}",
                can_autofix=False,  # TODO: 实现自动安装逻辑
            )

        return ValidationResult(is_valid=True)
