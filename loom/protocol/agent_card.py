"""
Agent Card - A2A协议能力声明

基于Google A2A协议的Agent Card规范，用于声明节点的能力。

参考：
- A2A Protocol Specification (2025)
- 符合公理A1（统一接口）和A6（四范式工作）
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AgentCapability(str, Enum):
    """
    代理能力枚举

    基于公理A6（四范式工作公理）：
    - REFLECTION: 反思能力
    - TOOL_USE: 工具使用能力
    - PLANNING: 规划能力
    - MULTI_AGENT: 多代理协作能力
    """

    REFLECTION = "reflection"
    TOOL_USE = "tool_use"
    PLANNING = "planning"
    MULTI_AGENT = "multi_agent"


@dataclass
class AgentCard:
    """
    Agent Card - 代理能力声明卡片

    符合A2A协议规范的JSON格式能力声明。

    属性：
        agent_id: 代理唯一标识
        name: 代理名称
        description: 代理描述
        version: 代理版本
        capabilities: 支持的能力列表（基于A6四范式）
        metadata: 额外元数据
    """

    agent_id: str
    name: str
    description: str
    version: str = "1.0.0"
    capabilities: list[AgentCapability] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转换为A2A协议标准的JSON格式"""
        return {
            "agentId": self.agent_id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "capabilities": [cap.value for cap in self.capabilities],
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentCard":
        """从A2A协议JSON格式创建Agent Card"""
        return cls(
            agent_id=data["agentId"],
            name=data["name"],
            description=data["description"],
            version=data.get("version", "1.0.0"),
            capabilities=[AgentCapability(cap) for cap in data.get("capabilities", [])],
            metadata=data.get("metadata", {}),
        )
