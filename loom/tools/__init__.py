"""
Loom Tools - 统一的工具系统

新架构（基于 SandboxToolManager）：
- 所有工具通过 SandboxToolManager 统一管理
- 支持动态工具注册和注销
- 自动沙盒化
- MCP 工具无缝集成

核心组件：
- Sandbox: 沙盒安全边界
- SandboxToolManager: 统一工具注册和执行中心
- SandboxedExecutor: 沙盒感知的工具执行器
- ToolScope: 工具作用域（SANDBOXED, SYSTEM, MCP, CONTEXT）

使用方式：
    from loom.tools import Sandbox, SandboxToolManager

    # 创建沙盒工具管理器
    sandbox = Sandbox("/path/to/workspace")
    manager = SandboxToolManager(sandbox)

    # 注册工具
    await register_file_tools_to_manager(manager)
    await register_search_tools_to_manager(manager)
    await register_bash_tool_to_manager(manager)

    # 传递给 Agent
    agent = Agent(
        node_id="my-agent",
        llm_provider=llm,
        sandbox_manager=manager,
    )
"""

# 核心组件
# 工具注册函数（新方式）
from loom.tools.bash_tool import register_bash_tool_to_manager

# Done 工具（特殊处理，不需要注册到管理器）
from loom.tools.done_tool import create_done_tool, execute_done_tool
from loom.tools.executor import SandboxedExecutor, ToolExecutor
from loom.tools.file_tools import register_file_tools_to_manager
from loom.tools.http_tool import register_http_tool_to_manager
from loom.tools.sandbox import Sandbox, SandboxViolation
from loom.tools.sandbox_manager import SandboxToolManager, ToolScope, ToolWrapper
from loom.tools.search_tools import register_search_tools_to_manager
from loom.tools.todo_tool import register_todo_tool_to_manager

# 工具集（新方式 - 返回 SandboxToolManager）
from loom.tools.toolset import (
    create_coding_toolset,
    create_minimal_toolset,
    create_sandbox_toolset,
    create_web_toolset,
)

__all__ = [
    # 核心组件
    "Sandbox",
    "SandboxViolation",
    "SandboxToolManager",
    "ToolScope",
    "ToolWrapper",
    # 执行器
    "ToolExecutor",
    "SandboxedExecutor",
    # Done 工具
    "create_done_tool",
    "execute_done_tool",
    # 工具注册函数
    "register_file_tools_to_manager",
    "register_search_tools_to_manager",
    "register_todo_tool_to_manager",
    "register_bash_tool_to_manager",
    "register_http_tool_to_manager",
    # 工具集
    "create_sandbox_toolset",
    "create_minimal_toolset",
    "create_coding_toolset",
    "create_web_toolset",
]
