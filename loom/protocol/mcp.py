"""
Model Context Protocol (MCP) Implementation for Loom
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from pydantic import BaseModel, Field, ConfigDict

# --- MCP Data Models ---

class MCPToolDefinition(BaseModel):
    """Definition of an MCP Tool."""
    name: str
    description: str
    input_schema: Dict[str, Any] = Field(..., alias="inputSchema") 
    
    model_config = ConfigDict(populate_by_name=True)

class MCPResource(BaseModel):
    """Definition of an MCP Resource."""
    uri: str
    name: str
    mime_type: str = Field(..., alias="mimeType")
    description: Optional[str] = None
    
    model_config = ConfigDict(populate_by_name=True)

class MCPPrompt(BaseModel):
    """Definition of an MCP Prompt."""
    name: str
    description: str
    arguments: List[Dict[str, Any]] = Field(default_factory=list)

class MCPToolCall(BaseModel):
    """A request to call a tool."""
    name: str
    arguments: Dict[str, Any]

class MCPToolResult(BaseModel):
    """Result of a tool call."""
    content: List[Dict[str, Any]] # Text or Image content
    is_error: bool = False

# --- MCP Interfaces ---

class MCPServer(ABC):
    """
    Abstract Interface for an MCP Server (provider of tools/resources).
    """
    
    @abstractmethod
    async def list_tools(self) -> List[MCPToolDefinition]:
        """List available tools."""
        pass

    @abstractmethod
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> MCPToolResult:
        """Call a specific tool."""
        pass

    @abstractmethod
    async def list_resources(self) -> List[MCPResource]:
        """List available resources."""
        pass
        
    @abstractmethod
    async def read_resource(self, uri: str) -> str:
        """Read a resource content."""
        pass

    @abstractmethod
    async def list_prompts(self) -> List[MCPPrompt]:
        """List available prompts."""
        pass
        
    @abstractmethod
    async def get_prompt(self, name: str, arguments: Dict[str, Any]) -> str:
        """Get a prompt context."""
        pass

class MCPClient(ABC):
    """
    Abstract Interface for an MCP Client (consumer of tools/resources).
    """
    
    @abstractmethod
    async def discover_capabilities(self):
        """Discover tools and resources from connected servers."""
        pass
    
    @abstractmethod
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a tool via the protocol."""
        pass
