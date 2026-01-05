"""
Tool Registry (M4)
"""

from typing import Dict, Any, Callable, List, Optional
from loom.protocol.mcp import MCPToolDefinition
from loom.tools.converters import FunctionToMCP
# ToolNode is in loom.node.tool, but avoid circular import if possible.
# Ideally Registry produces definitions + execution callables. 
# Factory creates Nodes.

class ToolRegistry:
    """
    Central repository for tools available to Agents.
    """
    
    def __init__(self):
        self._tools: Dict[str, Callable] = {}
        self._definitions: Dict[str, MCPToolDefinition] = {}

    def register_function(self, func: Callable, name: str = None) -> MCPToolDefinition:
        """Register a python function as a tool."""
        # Clean name
        tool_name = name or func.__name__
        
        # Convert to MCP
        definition = FunctionToMCP.convert(func, name=tool_name)
        
        # Store
        self._tools[tool_name] = func
        self._definitions[tool_name] = definition
        
        return definition
        
    def get_definition(self, name: str) -> Optional[MCPToolDefinition]:
        return self._definitions.get(name)
        
    def get_callable(self, name: str) -> Optional[Callable]:
        return self._tools.get(name)

    @property
    def definitions(self) -> List[MCPToolDefinition]:
        return list(self._definitions.values())
