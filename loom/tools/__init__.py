"""
Loom Tools - 统一的工具和能力管理系统（懒加载版本）

整合了 Tools 和 Skills 的统一管理：
- Tools: 内置工具 + MCP 工具 + 动态工具
- Skills: Anthropic SKILL.md 格式的能力包

核心组件（始终加载）：
- CapabilityRegistry: 统一能力发现和管理门面
- SandboxToolManager: 工具注册和执行
- Sandbox: 沙盒执行环境

内置工具（懒加载）：
- bash_tool, file_tools, http_tool, search_tools
- done_tool, todo_tool, context_tools, etc.
"""

from typing import TYPE_CHECKING

from .activator import SkillActivator
from .converters import FunctionToMCP
from .executor import ToolExecutor
from .loader import SkillLoader
from .mcp_adapter import MCPAdapter

# Skill 加载 - 始终加载（核心功能）
from .models import ActivationResult, SkillDefinition

# 核心注册表 - 始终加载
from .registry import CapabilityRegistry, CapabilitySet, ValidationResult

# 沙盒环境 - 始终加载
from .sandbox import Sandbox, SandboxViolation

# 工具管理 - 始终加载
from .sandbox_manager import SandboxToolManager, ToolScope, ToolWrapper
from .skill_loader import FilesystemSkillLoader
from .skill_registry import SkillRegistry, skill_market

if TYPE_CHECKING:
    from .bash_tool import create_bash_tool, register_bash_tool_to_manager
    from .context_tools import ContextToolExecutor, create_all_context_tools
    from .done_tool import create_done_tool, execute_done_tool
    from .file_tools import create_file_tools, register_file_tools_to_manager
    from .http_tool import create_http_tool, register_http_tool_to_manager
    from .index_context_tools import create_all_index_context_tools
    from .memory_management_tools import create_all_memory_management_tools
    from .search_tools import create_search_tools, register_search_tools_to_manager
    from .todo_tool import create_todo_tool, register_todo_tool_to_manager
    from .tool_creation import DynamicToolExecutor, create_tool_creation_tool

# 内置工具注册表（懒加载映射）
_TOOL_REGISTRY: dict[str, tuple[str, str]] = {
    # bash_tool
    "create_bash_tool": (".bash_tool", "create_bash_tool"),
    "register_bash_tool_to_manager": (".bash_tool", "register_bash_tool_to_manager"),
    # file_tools
    "create_file_tools": (".file_tools", "create_file_tools"),
    "register_file_tools_to_manager": (".file_tools", "register_file_tools_to_manager"),
    # http_tool
    "create_http_tool": (".http_tool", "create_http_tool"),
    "register_http_tool_to_manager": (".http_tool", "register_http_tool_to_manager"),
    # search_tools
    "create_search_tools": (".search_tools", "create_search_tools"),
    "register_search_tools_to_manager": (".search_tools", "register_search_tools_to_manager"),
    # done_tool
    "create_done_tool": (".done_tool", "create_done_tool"),
    "execute_done_tool": (".done_tool", "execute_done_tool"),
    # todo_tool
    "create_todo_tool": (".todo_tool", "create_todo_tool"),
    "register_todo_tool_to_manager": (".todo_tool", "register_todo_tool_to_manager"),
    # context_tools
    "create_all_context_tools": (".context_tools", "create_all_context_tools"),
    "ContextToolExecutor": (".context_tools", "ContextToolExecutor"),
    # index_context_tools
    "create_all_index_context_tools": (".index_context_tools", "create_all_index_context_tools"),
    # memory_management_tools
    "create_all_memory_management_tools": (".memory_management_tools", "create_all_memory_management_tools"),
    # tool_creation
    "create_tool_creation_tool": (".tool_creation", "create_tool_creation_tool"),
    "DynamicToolExecutor": (".tool_creation", "DynamicToolExecutor"),
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
    # Registry
    "CapabilityRegistry",
    "CapabilitySet",
    "ValidationResult",
    # Sandbox
    "Sandbox",
    "SandboxViolation",
    # Tool Management
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
    "create_all_context_tools",
    "ContextToolExecutor",
    "create_all_index_context_tools",
    "create_all_memory_management_tools",
    "create_tool_creation_tool",
    "DynamicToolExecutor",
]
