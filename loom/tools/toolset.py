"""
Toolset - 预设工具集

提供 Claude Code 风格的完整编程环境工具集。

核心工具：
1. Bash - 命令执行
2. File Operations - 文件读写编辑
3. Search - 文件名和内容搜索
4. Todo - 任务管理
5. HTTP - HTTP 请求
6. Done - 任务完成标记

所有文件操作都在沙箱内进行，确保安全隔离。

使用示例：
    from loom.tools.toolset import create_sandbox_toolset

    # 创建完整的沙箱工具集
    tools = create_sandbox_toolset(sandbox_dir="/path/to/sandbox")

    # 传递给 Agent
    agent = Agent(
        node_id="my-agent",
        llm_provider=llm,
        tools=tools,
    )
"""

from pathlib import Path

from loom.tools.bash_tool import create_bash_tool
from loom.tools.done_tool import create_done_tool
from loom.tools.file_tools import create_file_tools
from loom.tools.http_tool import create_http_tool
from loom.tools.sandbox import Sandbox
from loom.tools.search_tools import create_search_tools
from loom.tools.todo_tool import create_todo_tool


def create_sandbox_toolset(
    sandbox_dir: str | Path,
    include_bash: bool = True,
    include_files: bool = True,
    include_search: bool = True,
    include_todo: bool = True,
    include_http: bool = True,
    include_done: bool = True,
    bash_timeout: float = 30.0,
    http_timeout: float = 30.0,
    auto_create_sandbox: bool = True,
) -> list[dict]:
    """
    创建完整的沙箱工具集

    Args:
        sandbox_dir: 沙箱根目录
        include_bash: 是否包含 Bash 工具
        include_files: 是否包含文件操作工具
        include_search: 是否包含搜索工具
        include_todo: 是否包含 Todo 工具
        include_http: 是否包含 HTTP 工具
        include_done: 是否包含 Done 工具
        bash_timeout: Bash 命令超时时间
        http_timeout: HTTP 请求超时时间
        auto_create_sandbox: 如果沙箱目录不存在，是否自动创建

    Returns:
        工具定义列表
    """
    # 创建沙箱
    sandbox = Sandbox(sandbox_dir, auto_create=auto_create_sandbox)

    tools = []

    # 添加 Bash 工具
    if include_bash:
        tools.append(create_bash_tool(sandbox, timeout=bash_timeout))

    # 添加文件操作工具
    if include_files:
        tools.extend(create_file_tools(sandbox))

    # 添加搜索工具
    if include_search:
        tools.extend(create_search_tools(sandbox))

    # 添加 Todo 工具
    if include_todo:
        tools.append(create_todo_tool(sandbox))

    # 添加 HTTP 工具
    if include_http:
        tools.append(create_http_tool(timeout=http_timeout))

    # 添加 Done 工具
    if include_done:
        tools.append(create_done_tool())

    return tools


def create_minimal_toolset(sandbox_dir: str | Path) -> list[dict]:
    """
    创建最小工具集（仅文件操作和 Done）

    Args:
        sandbox_dir: 沙箱根目录

    Returns:
        工具定义列表
    """
    return create_sandbox_toolset(
        sandbox_dir=sandbox_dir,
        include_bash=False,
        include_search=False,
        include_todo=False,
        include_http=False,
        include_done=True,
    )


def create_coding_toolset(sandbox_dir: str | Path) -> list[dict]:
    """
    创建编程工具集（Bash + 文件 + 搜索 + Done）

    Args:
        sandbox_dir: 沙箱根目录

    Returns:
        工具定义列表
    """
    return create_sandbox_toolset(
        sandbox_dir=sandbox_dir,
        include_bash=True,
        include_files=True,
        include_search=True,
        include_todo=False,
        include_http=False,
        include_done=True,
    )


def create_web_toolset(sandbox_dir: str | Path) -> list[dict]:
    """
    创建 Web 工具集（文件 + HTTP + Done）

    Args:
        sandbox_dir: 沙箱根目录

    Returns:
        工具定义列表
    """
    return create_sandbox_toolset(
        sandbox_dir=sandbox_dir,
        include_bash=False,
        include_files=True,
        include_search=False,
        include_todo=False,
        include_http=True,
        include_done=True,
    )
