"""
Agent Card - A2A协议能力声明

基于Google A2A协议的Agent Card规范，用于声明节点的能力。
"""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from loom.runtime import Task


class AgentCapability(StrEnum):
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


class NodeProtocol(Protocol):
    """
    节点协议 - 所有节点必须实现的统一接口（A2A兼容）

    属性：
        node_id: 节点唯一标识
        source_uri: 节点URI
        agent_card: Agent Card能力声明
    """

    node_id: str
    source_uri: str
    agent_card: AgentCard

    async def execute_task(self, task: "Task") -> "Task":
        """执行A2A任务"""
        ...

    def get_capabilities(self) -> AgentCard:
        """获取能力声明"""
        ...
