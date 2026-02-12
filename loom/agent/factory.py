"""
AgentFactory - Agent 工厂

从 Agent.core 提取的创建逻辑。
负责配置规范化、组件组装、参数合并。
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from loom.config.context import ContextConfig
from loom.config.memory import MemoryConfig
from loom.config.tool import ToolConfig
from loom.events.event_bus import EventBus
from loom.memory.compaction import CompactionConfig
from loom.runtime.session_lane import SessionIsolationMode
from loom.security.tool_policy import ToolPolicy
from loom.tools.skills.registry import skill_market

if TYPE_CHECKING:
    from loom.agent.core import Agent
    from loom.providers.llm.interface import LLMProvider


class AgentFactory:
    """
    Agent 工厂

    将 Agent.create() 的配置规范化逻辑提取为独立类：
    - EventBus 自动创建
    - ToolConfig / ContextConfig 规范化
    - Capabilities 提取
    - Skills 目录 / Loader 处理
    - SandboxToolManager 自动创建
    - node_id 生成
    """

    @staticmethod
    def create(
        llm: LLMProvider,
        *,
        system_prompt: str = "",
        tools: list[dict[str, Any]] | None = None,
        skills: list[str] | None = None,
        capabilities: Any | None = None,
        node_id: str | None = None,
        parent_node_id: str | None = None,
        agent_role: str | None = None,
        event_bus: Any | None = None,
        knowledge_base: Any | None = None,
        max_context_tokens: int = 4000,
        max_iterations: int = 10,
        tool_policy: ToolPolicy | None = None,
        tool_config: ToolConfig | dict[str, Any] | None = None,
        context_config: ContextConfig | dict[str, Any] | None = None,
        skills_dir: str | Path | list[str | Path] | None = None,
        skill_loaders: list[Any] | None = None,
        memory_config: MemoryConfig | dict[str, Any] | None = None,
        context_budget_config: Any | None = None,
        session_isolation: SessionIsolationMode | str | None = None,
        compaction_config: CompactionConfig | dict[str, Any] | None = None,
        shared_pool: Any | None = None,
        **kwargs: Any,
    ) -> Agent:
        """
        创建 Agent 的推荐方式（一步到位）。

        v0.5.1: 支持渐进式披露的聚合配置

        Args:
            llm: LLM 提供者
            system_prompt: 系统提示词
            tools: 工具列表（简单用法，或使用 tool_config）
            skills: 技能 ID 列表（简单用法，或使用 tool_config）
            capabilities: CapabilityRegistry 实例（高级配置）
            node_id: 节点 ID（可选，默认自动生成）
            parent_node_id: 父节点ID（用于结构化命名）
            agent_role: Agent角色（用于SSE识别）
            event_bus: 事件总线（可选，未传入时自动创建）
            knowledge_base: 知识库提供者（可选）
            max_context_tokens: 最大上下文 token 数
            max_iterations: 最大迭代次数
            tool_policy: 工具权限策略（可选）
            tool_config: 工具聚合配置（ToolConfig 或 dict）
            context_config: 上下文聚合配置（ContextConfig 或 dict）
            **kwargs: 其他参数传递给 Agent.__init__

        Returns:
            Agent 实例
        """
        from loom.agent.core import Agent

        # 未传 event_bus 时自动创建
        if event_bus is None:
            event_bus = EventBus()

        # 处理 tool_config（聚合配置）
        tools, skills, skills_dir, skill_loaders = AgentFactory._normalize_tool_config(
            tool_config,
            tools,
            skills,
            skills_dir,
            skill_loaders,
        )

        # 处理 capabilities 参数（高级配置）
        AgentFactory._extract_capabilities(capabilities, kwargs)

        # 处理 Skills 目录 / Loader
        AgentFactory._setup_skill_loaders(skills_dir, skill_loaders, kwargs)

        # 处理 skills 参数（简单配置）
        AgentFactory._setup_skills(skills, kwargs)

        # 处理上下文配置（聚合入口）
        memory_config, context_budget_config, compaction_config, session_isolation = (
            AgentFactory._normalize_context_config(
                context_config,
                memory_config,
                context_budget_config,
                compaction_config,
                session_isolation,
            )
        )

        if session_isolation is None:
            session_isolation = SessionIsolationMode.STRICT

        # 显式参数合并到 kwargs
        if memory_config is not None:
            kwargs["memory_config"] = memory_config
        if context_budget_config is not None:
            kwargs["context_budget_config"] = context_budget_config
        if session_isolation is not None:
            kwargs["session_isolation"] = session_isolation
        if compaction_config is not None:
            kwargs["compaction_config"] = compaction_config
        if tool_policy is not None:
            kwargs["tool_policy"] = tool_policy
        if shared_pool is not None:
            kwargs["shared_pool"] = shared_pool

        # 自动创建 SandboxToolManager（tools 含可调用对象时）
        tools = AgentFactory._setup_sandbox(tools, event_bus, kwargs)

        # 生成 node_id
        effective_node_id = AgentFactory._resolve_node_id(
            node_id,
            parent_node_id,
            agent_role,
        )

        return Agent(
            node_id=effective_node_id,
            llm_provider=llm,
            system_prompt=system_prompt,
            tools=tools,
            event_bus=event_bus,
            knowledge_base=knowledge_base,
            max_context_tokens=max_context_tokens,
            max_iterations=max_iterations,
            **kwargs,
        )

    # ==================== 内部规范化方法 ====================

    @staticmethod
    def _normalize_tool_config(
        tool_config: ToolConfig | dict[str, Any] | None,
        tools: list[dict[str, Any]] | None,
        skills: list[str] | None,
        skills_dir: str | Path | list[str | Path] | None,
        skill_loaders: list[Any] | None,
    ) -> tuple[
        list[dict[str, Any]] | None,
        list[str] | None,
        str | Path | list[str | Path] | None,
        list[Any] | None,
    ]:
        if tool_config is None:
            return tools, skills, skills_dir, skill_loaders

        if isinstance(tool_config, dict):
            tool_config = ToolConfig(**tool_config)
        elif not isinstance(tool_config, ToolConfig):
            raise TypeError("tool_config must be ToolConfig or dict")

        if tools is None and tool_config.tools is not None:
            tools = tool_config.tools
        if skills is None and tool_config.skills is not None:
            skills = tool_config.skills
        if skills_dir is None and tool_config.skills_dir is not None:
            skills_dir = tool_config.skills_dir
        if skill_loaders is None and tool_config.skill_loaders is not None:
            skill_loaders = tool_config.skill_loaders

        return tools, skills, skills_dir, skill_loaders

    @staticmethod
    def _extract_capabilities(capabilities: Any | None, kwargs: dict[str, Any]) -> None:
        if capabilities is None:
            return
        if "sandbox_manager" not in kwargs and hasattr(capabilities, "tool_manager"):
            kwargs["sandbox_manager"] = capabilities.tool_manager
        if "skill_registry" not in kwargs and hasattr(capabilities, "skill_registry"):
            kwargs["skill_registry"] = capabilities.skill_registry
        if "skill_activator" not in kwargs and hasattr(capabilities, "skill_activator"):
            kwargs["skill_activator"] = capabilities.skill_activator

    @staticmethod
    def _setup_skill_loaders(
        skills_dir: str | Path | list[str | Path] | None,
        skill_loaders: list[Any] | None,
        kwargs: dict[str, Any],
    ) -> None:
        if skills_dir is None and not skill_loaders:
            return

        from loom.tools.skills.filesystem_loader import FilesystemSkillLoader

        if "skill_registry" not in kwargs:
            kwargs["skill_registry"] = skill_market
        registry = kwargs["skill_registry"]

        if skills_dir is not None:
            dirs = skills_dir if isinstance(skills_dir, list | tuple | set) else [skills_dir]
            for skills_path in dirs:
                registry.register_loader(FilesystemSkillLoader(skills_path))

        if skill_loaders:
            for loader in skill_loaders:
                registry.register_loader(loader)

    @staticmethod
    def _setup_skills(skills: list[str] | None, kwargs: dict[str, Any]) -> None:
        if skills is None:
            return

        if "skill_registry" not in kwargs:
            kwargs["skill_registry"] = skill_market

        if "config" not in kwargs:
            from loom.config.agent import AgentConfig

            kwargs["config"] = AgentConfig(enabled_skills=set(skills))
        else:
            kwargs["config"].enabled_skills = set(skills)

    @staticmethod
    def _normalize_context_config(
        context_config: ContextConfig | dict[str, Any] | None,
        memory_config: MemoryConfig | dict[str, Any] | None,
        context_budget_config: Any | None,
        compaction_config: CompactionConfig | dict[str, Any] | None,
        session_isolation: SessionIsolationMode | str | None,
    ) -> tuple[Any, Any, Any, Any]:
        if context_config is None:
            return memory_config, context_budget_config, compaction_config, session_isolation

        if isinstance(context_config, dict):
            context_config = ContextConfig(**context_config)
        elif not isinstance(context_config, ContextConfig):
            raise TypeError("context_config must be ContextConfig or dict")

        if memory_config is None and context_config.memory is not None:
            memory_config = context_config.memory
        if context_budget_config is None and context_config.budget is not None:
            context_budget_config = context_config.budget
        if compaction_config is None and context_config.compaction is not None:
            compaction_config = context_config.compaction
        if session_isolation is None:
            session_isolation = context_config.session_isolation

        return memory_config, context_budget_config, compaction_config, session_isolation

    @staticmethod
    def _setup_sandbox(
        tools: list[Any] | None,
        event_bus: Any,
        kwargs: dict[str, Any],
    ) -> list[Any] | None:
        tools_list = tools or []
        tools_dicts = [t for t in tools_list if isinstance(t, dict)]
        tools_callables = [t for t in tools_list if callable(t)]
        sandbox_manager_in = kwargs.get("sandbox_manager")

        if tools_callables and sandbox_manager_in is None:
            import tempfile

            from loom.tools.core.sandbox import Sandbox
            from loom.tools.core.sandbox_manager import SandboxToolManager

            sandbox_path = tempfile.mkdtemp(prefix="loom_agent_")
            sandbox = Sandbox(sandbox_path, auto_create=True)
            manager = SandboxToolManager(sandbox, event_bus=event_bus)
            kwargs["sandbox_manager"] = manager
            kwargs["_pending_tool_callables"] = tools_callables
            tools = tools_dicts

        return tools

    @staticmethod
    def _resolve_node_id(
        node_id: str | None,
        parent_node_id: str | None,
        agent_role: str | None,
    ) -> str:
        if node_id is not None:
            return node_id
        if parent_node_id and agent_role:
            return f"{parent_node_id}:{agent_role}"
        if parent_node_id:
            return f"{parent_node_id}:{str(uuid4())[:8]}"
        if agent_role:
            return f"{agent_role}:{str(uuid4())[:8]}"
        return str(uuid4())
