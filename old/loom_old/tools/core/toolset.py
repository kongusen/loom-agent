"""
Toolset - 预设工具集

提供 Claude Code 风格的完整编程环境工具集。

新架构（基于 SandboxToolManager）：
- 所有工具通过 SandboxToolManager 统一管理
- 支持动态工具注册
- 自动沙盒化
- MCP 工具无缝集成

核心工具：
1. Bash - 命令执行（SYSTEM 作用域）
2. File Operations - 文件读写编辑（SANDBOXED 作用域）
3. Search - 文件名和内容搜索（SANDBOXED 作用域）
4. Todo - 任务管理（SANDBOXED 作用域）
5. HTTP - HTTP 请求（SYSTEM 作用域）
6. Done - 任务完成标记

使用示例：
    from loom.tools.toolset import create_sandbox_toolset

    # 创建完整的沙箱工具集，返回 SandboxToolManager
    manager = create_sandbox_toolset(sandbox_dir="/path/to/sandbox")

    # 传递给 Agent
    agent = Agent(
        node_id="my-agent",
        llm_provider=llm,
        sandbox_manager=manager,  # 新方式：传递管理器
    )
"""

from pathlib import Path

from loom.events import EventBus
from loom.tools.builtin.bash import register_bash_tool_to_manager
from loom.tools.builtin.file import register_file_tools_to_manager
from loom.tools.builtin.http import register_http_tool_to_manager
from loom.tools.builtin.search import register_search_tools_to_manager
from loom.tools.builtin.todo import register_todo_tool_to_manager
from loom.tools.core.sandbox import Sandbox
from loom.tools.core.sandbox_manager import SandboxToolManager


async def create_sandbox_toolset(
    sandbox_dir: str | Path,
    event_bus: EventBus | None = None,
    include_bash: bool = True,
    include_files: bool = True,
    include_search: bool = True,
    include_todo: bool = True,
    include_http: bool = True,
    bash_timeout: float = 30.0,
    http_timeout: float = 30.0,
    auto_create_sandbox: bool = True,
) -> SandboxToolManager:
    """
    创建完整的沙箱工具集

    返回 SandboxToolManager 实例，所有工具已注册到管理器中。

    Args:
        sandbox_dir: 沙箱根目录
        event_bus: 事件总线（可选）
        include_bash: 是否包含 Bash 工具
        include_files: 是否包含文件操作工具
        include_search: 是否包含搜索工具
        include_todo: 是否包含 Todo 工具
        include_http: 是否包含 HTTP 工具
        bash_timeout: Bash 命令超时时间
        http_timeout: HTTP 请求超时时间
        auto_create_sandbox: 如果沙箱目录不存在，是否自动创建

    Returns:
        SandboxToolManager 实例，所有工具已注册

    Example:
        manager = await create_sandbox_toolset("/path/to/sandbox")
        # manager.list_tools() 返回所有已注册的工具
    """
    # 创建沙箱
    sandbox = Sandbox(sandbox_dir, auto_create=auto_create_sandbox)

    # 创建沙盒工具管理器
    manager = SandboxToolManager(sandbox, event_bus=event_bus)

    # 注册文件操作工具（SANDBOXED 作用域）
    if include_files:
        await register_file_tools_to_manager(manager)

    # 注册搜索工具（SANDBOXED 作用域）
    if include_search:
        await register_search_tools_to_manager(manager)

    # 注册 Todo 工具（SANDBOXED 作用域）
    if include_todo:
        await register_todo_tool_to_manager(manager)

    # 注册 Bash 工具（SYSTEM 作用域）
    if include_bash:
        await register_bash_tool_to_manager(manager, timeout=bash_timeout)

    # 注册 HTTP 工具（SYSTEM 作用域）
    if include_http:
        await register_http_tool_to_manager(manager, timeout=http_timeout)

    # 注意：done 工具不需要注册到管理器，它会被 Agent 直接处理

    return manager


async def create_minimal_toolset(
    sandbox_dir: str | Path,
    event_bus: EventBus | None = None,
) -> SandboxToolManager:
    """
    创建最小工具集（仅文件操作和 Done）

    Args:
        sandbox_dir: 沙箱根目录
        event_bus: 事件总线（可选）

    Returns:
        SandboxToolManager 实例
    """
    return await create_sandbox_toolset(
        sandbox_dir=sandbox_dir,
        event_bus=event_bus,
        include_bash=False,
        include_search=False,
        include_todo=False,
        include_http=False,
    )


async def create_coding_toolset(
    sandbox_dir: str | Path,
    event_bus: EventBus | None = None,
) -> SandboxToolManager:
    """
    创建编程工具集（Bash + 文件 + 搜索 + Done）

    Args:
        sandbox_dir: 沙箱根目录
        event_bus: 事件总线（可选）

    Returns:
        SandboxToolManager 实例
    """
    return await create_sandbox_toolset(
        sandbox_dir=sandbox_dir,
        event_bus=event_bus,
        include_bash=True,
        include_files=True,
        include_search=True,
        include_todo=False,
        include_http=False,
    )


async def create_web_toolset(
    sandbox_dir: str | Path,
    event_bus: EventBus | None = None,
) -> SandboxToolManager:
    """
    创建 Web 工具集（文件 + HTTP + Done）

    Args:
        sandbox_dir: 沙箱根目录
        event_bus: 事件总线（可选）

    Returns:
        SandboxToolManager 实例
    """
    return await create_sandbox_toolset(
        sandbox_dir=sandbox_dir,
        event_bus=event_bus,
        include_bash=False,
        include_files=True,
        include_search=False,
        include_todo=False,
        include_http=True,
    )
