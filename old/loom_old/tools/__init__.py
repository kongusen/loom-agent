"""
Loom Tools - 统一的工具和能力管理系统（懒加载版本）

目录结构:
- core/: 核心基础设施（Registry, Sandbox, Executor）
- skills/: Skill 系统（Loader, Activator, Registry）
- builtin/: 内置工具（bash, file, http, search, done, todo, creation）
- memory/: 记忆操作工具（query, browse, manage, events）

所有导出保持兼容：
>>> from loom.tools import CapabilityRegistry, Sandbox, create_bash_tool
>>> from loom.tools import FilesystemSkillLoader, skill_market
"""

from typing import TYPE_CHECKING

# === 核心基础设施（始终加载）===
from .core import (
    CapabilityRegistry,
    CapabilitySet,
    FunctionToMCP,
    MCPAdapter,
    Sandbox,
    SandboxToolManager,
    SandboxViolation,
    ToolExecutor,
    ToolScope,
    ToolWrapper,
    ValidationResult,
)

# === Skill 系统（始终加载）===
from .skills import (
    ActivationResult,
    FilesystemSkillLoader,
    SkillActivator,
    SkillDefinition,
    SkillLoader,
    SkillRegistry,
    skill_market,
)

if TYPE_CHECKING:
    # Builtin tools (lazy loaded)
    from .builtin import (
        DynamicToolExecutor,
        create_bash_tool,
        create_done_tool,
        create_file_tools,
        create_http_tool,
        create_search_tools,
        create_todo_tool,
        create_tool_creation_tool,
        execute_done_tool,
        register_bash_tool_to_manager,
        register_file_tools_to_manager,
        register_http_tool_to_manager,
        register_search_tools_to_manager,
        register_todo_tool_to_manager,
    )

    # Memory tools (lazy loaded)
    from .memory import (
        create_unified_browse_tool,
        create_unified_events_tool,
        create_unified_manage_tool,
        create_unified_memory_tool,
        execute_unified_browse_tool,
        execute_unified_events_tool,
        execute_unified_manage_tool,
        execute_unified_memory_tool,
    )

# 内置工具注册表（懒加载映射）
_TOOL_REGISTRY: dict[str, tuple[str, str]] = {
    # builtin/bash
    "create_bash_tool": (".builtin.bash", "create_bash_tool"),
    "register_bash_tool_to_manager": (".builtin.bash", "register_bash_tool_to_manager"),
    # builtin/file
    "create_file_tools": (".builtin.file", "create_file_tools"),
    "register_file_tools_to_manager": (".builtin.file", "register_file_tools_to_manager"),
    # builtin/http
    "create_http_tool": (".builtin.http", "create_http_tool"),
    "register_http_tool_to_manager": (".builtin.http", "register_http_tool_to_manager"),
    # builtin/search
    "create_search_tools": (".builtin.search", "create_search_tools"),
    "register_search_tools_to_manager": (".builtin.search", "register_search_tools_to_manager"),
    # builtin/done
    "create_done_tool": (".builtin.done", "create_done_tool"),
    "execute_done_tool": (".builtin.done", "execute_done_tool"),
    # builtin/todo
    "create_todo_tool": (".builtin.todo", "create_todo_tool"),
    "register_todo_tool_to_manager": (".builtin.todo", "register_todo_tool_to_manager"),
    # builtin/creation
    "create_tool_creation_tool": (".builtin.creation", "create_tool_creation_tool"),
    "DynamicToolExecutor": (".builtin.creation", "DynamicToolExecutor"),
    # memory/query
    "create_unified_memory_tool": (".memory.query", "create_unified_memory_tool"),
    "execute_unified_memory_tool": (".memory.query", "execute_unified_memory_tool"),
    # memory/browse
    "create_unified_browse_tool": (".memory.browse", "create_unified_browse_tool"),
    "execute_unified_browse_tool": (".memory.browse", "execute_unified_browse_tool"),
    # memory/manage
    "create_unified_manage_tool": (".memory.manage", "create_unified_manage_tool"),
    "execute_unified_manage_tool": (".memory.manage", "execute_unified_manage_tool"),
    # memory/events
    "create_unified_events_tool": (".memory.events", "create_unified_events_tool"),
    "execute_unified_events_tool": (".memory.events", "execute_unified_events_tool"),
}

# 缓存已加载的工具
_loaded_tools: dict[str, object] = {}


def __getattr__(name: str):
    """懒加载内置工具 - 只在首次访问时导入"""
    if name in _TOOL_REGISTRY:
        if name not in _loaded_tools:
            import importlib

            module_path, attr_name = _TOOL_REGISTRY[name]
            module = importlib.import_module(module_path, package="loom.tools")
            _loaded_tools[name] = getattr(module, attr_name)
        return _loaded_tools[name]
    raise AttributeError(f"module 'loom.tools' has no attribute '{name}'")


__all__ = [
    # Core - Registry
    "CapabilityRegistry",
    "CapabilitySet",
    "ValidationResult",
    # Core - Sandbox
    "Sandbox",
    "SandboxViolation",
    # Core - Tool Management
    "SandboxToolManager",
    "ToolScope",
    "ToolWrapper",
    "ToolExecutor",
    "MCPAdapter",
    "FunctionToMCP",
    # Skills
    "SkillDefinition",
    "ActivationResult",
    "SkillActivator",
    "FilesystemSkillLoader",
    "SkillLoader",
    "SkillRegistry",
    "skill_market",
    # Builtin Tools
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
    # Memory Tools
    "create_unified_memory_tool",
    "execute_unified_memory_tool",
    "create_unified_browse_tool",
    "execute_unified_browse_tool",
    "create_unified_manage_tool",
    "execute_unified_manage_tool",
    "create_unified_events_tool",
    "execute_unified_events_tool",
]
