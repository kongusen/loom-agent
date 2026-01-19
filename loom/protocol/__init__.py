"""
A1: 统一接口公理 (Uniform Interface Axiom)

公理陈述：∀x ∈ System: x implements NodeProtocol

本模块定义了框架的核心协议，确保所有节点实现统一的接口。
符合Google A2A协议标准。

导出内容：
- NodeProtocol: 节点统一接口协议
- AgentCard: A2A能力声明卡片
- AgentCapability: 代理能力枚举（基于A6四范式）
- Task: A2A任务模型
- TaskStatus: 任务状态枚举
- MemoryOperation: 记忆操作类型枚举
- MemoryRequest: 记忆操作请求
- MemoryResponse: 记忆操作响应
- MCP协议: MCP工具和资源协议
"""

from loom.protocol.agent_card import AgentCapability, AgentCard
from loom.protocol.mcp import (
    MCPClient,
    MCPPrompt,
    MCPResource,
    MCPServer,
    MCPToolCall,
    MCPToolDefinition,
    MCPToolResult,
)
from loom.protocol.memory_ops import MemoryOperation, MemoryRequest, MemoryResponse
from loom.protocol.node import NodeProtocol
from loom.protocol.task import Task, TaskStatus

__all__ = [
    "NodeProtocol",
    "AgentCard",
    "AgentCapability",
    "Task",
    "TaskStatus",
    "MemoryOperation",
    "MemoryRequest",
    "MemoryResponse",
    # MCP Protocol
    "MCPToolDefinition",
    "MCPResource",
    "MCPPrompt",
    "MCPToolCall",
    "MCPToolResult",
    "MCPServer",
    "MCPClient",
]
