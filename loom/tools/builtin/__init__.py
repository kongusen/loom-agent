"""
Builtin - 内置工具

包含：
- bash: Bash 命令执行
- file: 文件操作
- http: HTTP 请求
- search: 搜索工具
- done: 完成信号
- todo: TODO 管理
- creation: 动态工具创建
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .bash import create_bash_tool, register_bash_tool_to_manager
    from .creation import DynamicToolExecutor, create_tool_creation_tool
    from .done import create_done_tool, execute_done_tool
    from .file import create_file_tools, register_file_tools_to_manager
    from .http import create_http_tool, register_http_tool_to_manager
    from .search import create_search_tools, register_search_tools_to_manager
    from .todo import create_todo_tool, register_todo_tool_to_manager

# 懒加载映射
_BUILTIN_REGISTRY: dict[str, tuple[str, str]] = {
    "create_bash_tool": (".bash", "create_bash_tool"),
    "register_bash_tool_to_manager": (".bash", "register_bash_tool_to_manager"),
    "create_file_tools": (".file", "create_file_tools"),
    "register_file_tools_to_manager": (".file", "register_file_tools_to_manager"),
    "create_http_tool": (".http", "create_http_tool"),
    "register_http_tool_to_manager": (".http", "register_http_tool_to_manager"),
    "create_search_tools": (".search", "create_search_tools"),
    "register_search_tools_to_manager": (".search", "register_search_tools_to_manager"),
    "create_done_tool": (".done", "create_done_tool"),
    "execute_done_tool": (".done", "execute_done_tool"),
    "create_todo_tool": (".todo", "create_todo_tool"),
    "register_todo_tool_to_manager": (".todo", "register_todo_tool_to_manager"),
    "create_tool_creation_tool": (".creation", "create_tool_creation_tool"),
    "DynamicToolExecutor": (".creation", "DynamicToolExecutor"),
}

_loaded: dict[str, object] = {}


def __getattr__(name: str):
    if name in _BUILTIN_REGISTRY:
        if name not in _loaded:
            import importlib
            module_path, attr_name = _BUILTIN_REGISTRY[name]
            module = importlib.import_module(module_path, package="loom.tools.builtin")
            _loaded[name] = getattr(module, attr_name)
        return _loaded[name]
    raise AttributeError(f"module 'loom.tools.builtin' has no attribute '{name}'")


__all__ = [
    "create_bash_tool",
    "register_bash_tool_to_manager",
    "create_file_tools",
    "register_file_tools_to_manager",
    "create_http_tool",
    "register_http_tool_to_manager",
    "create_search_tools",
    "register_search_tools_to_manager",
    "create_done_tool",
    "execute_done_tool",
    "create_todo_tool",
    "register_todo_tool_to_manager",
    "create_tool_creation_tool",
    "DynamicToolExecutor",
]
