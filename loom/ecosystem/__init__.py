"""Ecosystem module - Skill, Plugin, MCP

三大生态组件：
1. Skill: 可复用的提示词模板（类似 Claude Code 的 skills）
2. Plugin: 扩展包，可包含 Skills、Tools、Hooks、MCP servers
3. MCP: Model Context Protocol 服务器集成
"""

from .skill import Skill, SkillRegistry, SkillLoader
from .plugin import Plugin, PluginLoader, PluginManifest
from .mcp import MCPServer, MCPBridge, MCPServerConfig, MCPTransportType
from .integration import EcosystemManager

__all__ = [
    'Skill',
    'SkillRegistry',
    'SkillLoader',
    'Plugin',
    'PluginLoader',
    'PluginManifest',
    'MCPServer',
    'MCPBridge',
    'MCPServerConfig',
    'MCPTransportType',
    'EcosystemManager',
]
