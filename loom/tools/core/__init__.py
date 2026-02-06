"""
Core - 工具系统核心基础设施

包含：
- CapabilityRegistry: 统一能力发现和管理门面
- Sandbox: 沙盒执行环境
- SandboxToolManager: 工具注册和执行
- ToolExecutor: 工具执行器
- MCPAdapter: MCP 协议适配器
- FunctionToMCP: 函数转 MCP 工具
"""

from .converters import FunctionToMCP
from .executor import ToolExecutor
from .mcp_adapter import MCPAdapter
from .registry import CapabilityRegistry, CapabilitySet, ValidationResult
from .sandbox import Sandbox, SandboxViolation
from .sandbox_manager import SandboxToolManager, ToolScope, ToolWrapper

__all__ = [
    "CapabilityRegistry",
    "CapabilitySet",
    "ValidationResult",
    "Sandbox",
    "SandboxViolation",
    "SandboxToolManager",
    "ToolScope",
    "ToolWrapper",
    "ToolExecutor",
    "MCPAdapter",
    "FunctionToMCP",
]
