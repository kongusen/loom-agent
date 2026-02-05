"""
AgentBuilder - 链式构建器

提供流畅的链式API风格创建Agent。

从 core.py 拆分，遵循单一职责原则。
"""

from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from loom.config.context import ContextConfig
    from loom.config.memory import MemoryConfig
    from loom.config.tool import ToolConfig
    from loom.memory.compaction import CompactionConfig
    from loom.providers.llm.interface import LLMProvider
    from loom.runtime.session_lane import SessionIsolationMode
    from loom.security.tool_policy import ToolPolicy

    from .core import Agent


class AgentBuilder:
    """
    Agent构建器 - 支持流畅的链式调用

    提供类似llama-index的流畅API风格。

    Examples:
        >>> agent = (Agent.builder(llm)
        ...     .with_system_prompt("你是一个AI助手")
        ...     .with_tools([...])
        ...     .with_memory(max_tokens=4000)
        ...     .build())
    """

    def __init__(self, llm: "LLMProvider"):
        """初始化构建器"""
        self.llm = llm
        self.config: dict[str, Any] = {}

    def with_system_prompt(self, prompt: str) -> "AgentBuilder":
        """设置系统提示词"""
        self.config["system_prompt"] = prompt
        return self

    def with_tools(self, tools: list[dict[str, Any]]) -> "AgentBuilder":
        """设置工具列表"""
        self.config["tools"] = tools
        return self

    def with_memory(self, max_tokens: int = 4000) -> "AgentBuilder":
        """配置上下文窗口（token上限）"""
        self.config["max_context_tokens"] = max_tokens
        return self

    def with_context_window(self, max_tokens: int = 4000) -> "AgentBuilder":
        """配置上下文窗口（别名）"""
        return self.with_memory(max_tokens)

    def with_memory_config(self, memory_config: "MemoryConfig | dict[str, Any]") -> "AgentBuilder":
        """配置记忆系统（MemoryConfig 或 dict）"""
        self.config["memory_config"] = memory_config
        return self

    def with_context_budget(self, budget_config: Any) -> "AgentBuilder":
        """配置上下文预算（BudgetConfig 或 dict）"""
        self.config["context_budget_config"] = budget_config
        return self

    def with_context_config(
        self, context_config: "ContextConfig | dict[str, Any]"
    ) -> "AgentBuilder":
        """配置上下文流动（ContextConfig 或 dict）"""
        self.config["context_config"] = context_config
        return self

    def with_knowledge_base(self, knowledge_base: Any) -> "AgentBuilder":
        """设置知识库"""
        self.config["knowledge_base"] = knowledge_base
        return self

    def with_event_bus(self, event_bus: Any) -> "AgentBuilder":
        """设置事件总线"""
        self.config["event_bus"] = event_bus
        return self

    def with_iterations(self, max_iterations: int) -> "AgentBuilder":
        """设置最大迭代次数"""
        self.config["max_iterations"] = max_iterations
        return self

    def with_session_isolation(self, mode: "SessionIsolationMode | str") -> "AgentBuilder":
        """设置 Session 隔离模式（strict/advisory/none）"""
        self.config["session_isolation"] = mode
        return self

    def with_compaction(
        self, compaction_config: "CompactionConfig | dict[str, Any]"
    ) -> "AgentBuilder":
        """设置记忆压缩配置"""
        self.config["compaction_config"] = compaction_config
        return self

    def with_tool_policy(self, tool_policy: "ToolPolicy") -> "AgentBuilder":
        """设置工具权限策略"""
        self.config["tool_policy"] = tool_policy
        return self

    def with_skills(self, skills: list[str]) -> "AgentBuilder":
        """设置技能列表"""
        self.config["skills"] = skills
        return self

    def with_skills_dir(self, skills_dir: str | Path | list[str | Path]) -> "AgentBuilder":
        """设置 Skills 目录（SKILL.md 包）"""
        self.config["skills_dir"] = skills_dir
        return self

    def with_skill_loaders(self, skill_loaders: list[Any]) -> "AgentBuilder":
        """设置 Skills 加载器列表"""
        self.config["skill_loaders"] = skill_loaders
        return self

    def with_tool_config(self, tool_config: "ToolConfig | dict[str, Any]") -> "AgentBuilder":
        """设置工具聚合配置（v0.5.1 渐进式披露）"""
        self.config["tool_config"] = tool_config
        return self

    def with_capabilities(self, capabilities: Any) -> "AgentBuilder":
        """设置能力注册表（CapabilityRegistry）"""
        self.config["capabilities"] = capabilities
        return self

    def with_knowledge_config(
        self, max_items: int = 3, relevance_threshold: float = 0.7
    ) -> "AgentBuilder":
        """配置知识库查询参数"""
        self.config["knowledge_max_items"] = max_items
        self.config["knowledge_relevance_threshold"] = relevance_threshold
        return self

    def with_done_tool(self, require: bool = True) -> "AgentBuilder":
        """设置是否要求显式调用done工具"""
        self.config["require_done_tool"] = require
        return self

    def build(self) -> "Agent":
        """构建Agent实例"""
        from .core import Agent

        return Agent.create(self.llm, **self.config)
