"""
Skill 基类

Skill = Tool + Prompt + Memory Config
提供可复用的能力封装。
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from loom.node.agent import AgentNode
from loom.node.tool import ToolNode


class Skill(ABC):
    """
    技能基类。

    技能是工具、提示词和配置的组合，可以注册到 Agent 上。
    """

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    @abstractmethod
    def get_tools(self) -> List[ToolNode]:
        """
        返回此技能提供的工具列表。

        Returns:
            工具节点列表
        """
        pass

    def get_system_prompt(self) -> Optional[str]:
        """
        返回此技能的系统提示词（可选）。

        Returns:
            系统提示词，如果不需要则返回 None
        """
        return None

    def get_memory_config(self) -> Optional[Dict[str, Any]]:
        """
        返回此技能的记忆配置（可选）。

        Returns:
            记忆配置字典，如果不需要则返回 None
        """
        return None

    def register(self, agent: AgentNode):
        """
        将此技能注册到 Agent。

        Args:
            agent: 要注册到的 Agent
        """
        # 添加工具到 known_tools 字典
        tools = self.get_tools()
        if tools:
            for tool in tools:
                agent.known_tools[tool.tool_def.name] = tool

        # 更新系统提示词
        prompt = self.get_system_prompt()
        if prompt:
            if agent.system_prompt:
                agent.system_prompt += f"\n\n{prompt}"
            else:
                agent.system_prompt = prompt

        # 应用记忆配置
        memory_config = self.get_memory_config()
        if memory_config:
            # TODO: 应用记忆配置
            pass
