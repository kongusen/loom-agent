"""
Memory - 记忆操作工具

包含：
- query: 查询记忆 (query_memory)
- browse: 浏览记忆 (browse_memory)
- manage: 管理记忆 (manage_memory)
- events: 事件查询 (query_events)
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .browse import create_unified_browse_tool, execute_unified_browse_tool
    from .events import create_unified_events_tool, execute_unified_events_tool
    from .manage import create_unified_manage_tool, execute_unified_manage_tool
    from .query import create_unified_memory_tool, execute_unified_memory_tool

# 懒加载映射
_MEMORY_REGISTRY: dict[str, tuple[str, str]] = {
    "create_unified_memory_tool": (".query", "create_unified_memory_tool"),
    "execute_unified_memory_tool": (".query", "execute_unified_memory_tool"),
    "create_unified_browse_tool": (".browse", "create_unified_browse_tool"),
    "execute_unified_browse_tool": (".browse", "execute_unified_browse_tool"),
    "create_unified_manage_tool": (".manage", "create_unified_manage_tool"),
    "execute_unified_manage_tool": (".manage", "execute_unified_manage_tool"),
    "create_unified_events_tool": (".events", "create_unified_events_tool"),
    "execute_unified_events_tool": (".events", "execute_unified_events_tool"),
}

_loaded: dict[str, object] = {}


def __getattr__(name: str):
    if name in _MEMORY_REGISTRY:
        if name not in _loaded:
            import importlib
            module_path, attr_name = _MEMORY_REGISTRY[name]
            module = importlib.import_module(module_path, package="loom.tools.memory")
            _loaded[name] = getattr(module, attr_name)
        return _loaded[name]
    raise AttributeError(f"module 'loom.tools.memory' has no attribute '{name}'")


__all__ = [
    "create_unified_memory_tool",
    "execute_unified_memory_tool",
    "create_unified_browse_tool",
    "execute_unified_browse_tool",
    "create_unified_manage_tool",
    "execute_unified_manage_tool",
    "create_unified_events_tool",
    "execute_unified_events_tool",
]
