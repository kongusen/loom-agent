"""
NodeProtocol - 统一接口协议（A2A兼容）

基于公理A1（统一接口公理）：
∀x ∈ System: x implements NodeProtocol

符合Google A2A协议标准，支持：
- Agent Card能力声明
- 基于任务的通信
- JSON-RPC 2.0兼容

设计原则：
1. 最小但完整 - 只包含必需的方法
2. 协议优先 - 使用Protocol实现结构化子类型
3. 异步优先 - 所有方法都是async
4. A2A兼容 - 符合Google A2A协议标准
"""

from typing import Protocol

from loom.protocol.agent_card import AgentCard
from loom.protocol.task import Task


class NodeProtocol(Protocol):
    """
    节点协议 - 所有节点必须实现的统一接口（A2A兼容）

    属性：
        node_id: 节点唯一标识
        source_uri: 节点URI（格式：node://{node_id}）
        agent_card: Agent Card能力声明（A2A协议）

    方法：
        execute_task: 执行A2A任务（符合A2A协议）
        get_capabilities: 获取能力声明（A2A协议）
    """

    node_id: str
    source_uri: str
    agent_card: AgentCard

    async def execute_task(self, task: Task) -> Task:
        """
        执行A2A任务

        符合Google A2A协议的任务执行接口。
        任务有明确的生命周期：pending -> running -> completed/failed

        Args:
            task: A2A任务对象

        Returns:
            更新后的任务对象（包含结果或错误）
        """
        ...

    def get_capabilities(self) -> AgentCard:
        """
        获取Agent Card能力声明

        符合A2A协议的能力发现机制。

        Returns:
            Agent Card对象
        """
        ...
