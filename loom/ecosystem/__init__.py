"""Ecosystem module - Skill, Plugin, MCP

三大生态组件：
1. Skill: 可复用的提示词模板（类似 Claude Code 的 skills）
2. Plugin: 扩展包，可包含 Skills、Tools、Hooks、MCP servers
3. MCP: Model Context Protocol 服务器集成

内部还包含 runtime activation 机制，用于将已加载生态组件注入当前运行时。
"""

from .integration import EcosystemManager
from .mcp import MCPBridge, MCPServer, MCPServerConfig, MCPTransportType
from .plugin import Plugin, PluginLoader, PluginManifest
from .skill import Skill, SkillLoader, SkillRegistry

__all__ = [
    "Skill",
    "SkillRegistry",
    "SkillLoader",
    "Plugin",
    "PluginLoader",
    "PluginManifest",
    "MCPServer",
    "MCPBridge",
    "MCPServerConfig",
    "MCPTransportType",
    "EcosystemManager",
]
