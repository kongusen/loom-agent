"""
Crew Role - 角色定义和配置 (Loom Agent v0.1.6)

支持为 Crew 中的每个角色定义：
- 使用的工具 (tools)
- 加载的记忆 (memory)
- 配置的知识库 (knowledge base)
- 系统提示 (system prompt)
- LLM 配置
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

from loom.core.base_agent import BaseAgent
from loom.interfaces.llm import BaseLLM
from loom.interfaces.tool import BaseTool
from loom.interfaces.memory import BaseMemory


@dataclass
class CrewRole:
    """
    Crew 角色定义

    定义一个角色的能力、工具、记忆等配置

    Example:
        role = CrewRole(
            name="researcher",
            goal="Research and gather information",
            tools=[search_tool, read_file_tool],
            memory=InMemoryMemory(),
            knowledge_base={"domain": "AI", "expertise": "research"},
            system_prompt="You are an expert researcher..."
        )
    """

    # 基本信息
    name: str
    goal: str
    description: str = ""

    # Agent 配置
    system_prompt: Optional[str] = None
    llm: Optional[BaseLLM] = None

    # 工具配置
    tools: List[BaseTool] = field(default_factory=list)

    # 记忆配置
    memory: Optional[BaseMemory] = None
    memory_config: Dict[str, Any] = field(default_factory=dict)

    # 知识库配置
    knowledge_base: Optional[Dict[str, Any]] = None
    knowledge_base_path: Optional[str] = None

    # 高级配置
    max_iterations: int = 10
    allow_delegation: bool = False
    verbose: bool = False

    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """验证配置"""
        if not self.name:
            raise ValueError("Role name is required")
        if not self.goal:
            raise ValueError("Role goal is required")

        # 生成默认 system_prompt
        if self.system_prompt is None:
            self.system_prompt = self._generate_default_prompt()

    def _generate_default_prompt(self) -> str:
        """生成默认系统提示"""
        prompt_parts = [f"You are {self.name}."]

        if self.description:
            prompt_parts.append(self.description)

        prompt_parts.append(f"Your goal: {self.goal}")

        if self.tools:
            tool_names = ", ".join([t.name for t in self.tools])
            prompt_parts.append(f"You have access to these tools: {tool_names}")

        if self.knowledge_base:
            prompt_parts.append(
                f"You have knowledge about: {', '.join(self.knowledge_base.keys())}"
            )

        return " ".join(prompt_parts)

    def create_agent(
        self,
        llm: Optional[BaseLLM] = None,
        agent_class=None,
    ) -> BaseAgent:
        """
        基于角色配置创建 Agent

        Args:
            llm: LLM 实例（覆盖角色配置的 LLM）
            agent_class: Agent 类（默认使用 Agent，有工具时启用 react_mode）

        Returns:
            配置好的 Agent 实例
        """
        # 确定使用的 LLM
        agent_llm = llm or self.llm
        if agent_llm is None:
            raise ValueError(f"LLM is required for role '{self.name}'")

        # 确定使用的 Agent 类和模式
        if agent_class is None:
            from loom.agents import Agent
            agent_class = Agent

        # 构建 Agent 参数
        agent_kwargs = {
            "name": self.name,
            "llm": agent_llm,
            "system_prompt": self.system_prompt,
        }

        # 添加工具（如果有）
        if self.tools:
            agent_kwargs["tools"] = self.tools
            # 有工具时自动启用 ReAct 模式（如果没有显式指定）
            if "react_mode" not in agent_kwargs:
                agent_kwargs["react_mode"] = True

        # 添加记忆（如果 Agent 支持）
        if self.memory:
            if "memory" in inspect.signature(agent_class.__init__).parameters:
                agent_kwargs["memory"] = self.memory

        # 添加其他配置
        if "max_iterations" in inspect.signature(agent_class.__init__).parameters:
            agent_kwargs["max_iterations"] = self.max_iterations

        # 创建 Agent
        agent = agent_class(**agent_kwargs)

        # 附加知识库（如果有）
        if self.knowledge_base:
            # 将知识库存储为 Agent 的属性
            agent._knowledge_base = self.knowledge_base

        if self.knowledge_base_path:
            agent._knowledge_base_path = self.knowledge_base_path

        return agent

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "name": self.name,
            "goal": self.goal,
            "description": self.description,
            "system_prompt": self.system_prompt,
            "tools": [t.name for t in self.tools],
            "has_memory": self.memory is not None,
            "knowledge_base": self.knowledge_base,
            "max_iterations": self.max_iterations,
            "metadata": self.metadata,
        }

    def __repr__(self) -> str:
        tools_str = f", tools={len(self.tools)}" if self.tools else ""
        memory_str = ", memory=✓" if self.memory else ""
        kb_str = ", kb=✓" if self.knowledge_base else ""
        return f"CrewRole(name={self.name}{tools_str}{memory_str}{kb_str})"


# ===== 预定义角色模板 =====


def create_researcher_role(
    name: str = "researcher",
    tools: Optional[List[BaseTool]] = None,
    **kwargs,
) -> CrewRole:
    """创建研究员角色"""
    return CrewRole(
        name=name,
        goal="Research and gather comprehensive information on given topics",
        description="An expert researcher skilled at finding and analyzing information.",
        tools=tools or [],
        **kwargs,
    )


def create_writer_role(
    name: str = "writer",
    **kwargs,
) -> CrewRole:
    """创建写作者角色"""
    return CrewRole(
        name=name,
        goal="Write clear, engaging, and well-structured content",
        description="A professional writer with excellent communication skills.",
        **kwargs,
    )


def create_reviewer_role(
    name: str = "reviewer",
    **kwargs,
) -> CrewRole:
    """创建审阅者角色"""
    return CrewRole(
        name=name,
        goal="Review and improve content quality, clarity, and accuracy",
        description="An experienced editor and quality assurance specialist.",
        **kwargs,
    )


def create_analyst_role(
    name: str = "analyst",
    domain: str = "general",
    **kwargs,
) -> CrewRole:
    """创建分析师角色"""
    return CrewRole(
        name=name,
        goal=f"Analyze {domain} topics and provide insights",
        description=f"An expert {domain} analyst with deep domain knowledge.",
        knowledge_base={"domain": domain},
        **kwargs,
    )


def create_developer_role(
    name: str = "developer",
    tools: Optional[List[BaseTool]] = None,
    **kwargs,
) -> CrewRole:
    """创建开发者角色"""
    return CrewRole(
        name=name,
        goal="Write, review, and improve code",
        description="A skilled software developer with expertise in multiple programming languages.",
        tools=tools or [],
        **kwargs,
    )
