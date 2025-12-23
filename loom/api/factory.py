"""
Loom SDK: Factory Helpers
"""

from typing import List, Optional, Callable, Dict, Any

from loom.api.main import LoomApp
from loom.node.agent import AgentNode
from loom.node.tool import ToolNode
from loom.node.crew import CrewNode
from loom.protocol.mcp import MCPToolDefinition
from loom.interfaces.llm import LLMProvider

from loom.interfaces.memory import MemoryInterface

def Agent(
    app: LoomApp,
    name: str,
    role: str = "Assistant",
    tools: Optional[List[ToolNode]] = None,
    provider: Optional[LLMProvider] = None,
    memory: Optional[MemoryInterface] = None
) -> AgentNode:
    """Helper to create an AgentNode."""
    return AgentNode(
        node_id=name,
        dispatcher=app.dispatcher,
        role=role,
        tools=tools,
        provider=provider,
        memory=memory
    )

from loom.adapters.converters import FunctionToMCP

def Tool(
    app: LoomApp,
    name: str,
    func: Callable[..., Any],
    description: Optional[str] = None,
    parameters: Optional[Dict[str, Any]] = None
) -> ToolNode:
    """
    Helper to create a ToolNode.
    Auto-generates schema from function signature if parameters not provided.
    """
    
    # Auto-generate definition/schema if not provided
    auto_def = FunctionToMCP.convert(func, name=name)
    
    final_desc = description or auto_def.description
    final_input_schema = parameters or auto_def.input_schema
    
    tool_def = MCPToolDefinition(
        name=name,
        description=final_desc,
        input_schema=final_input_schema
    )
    
    return ToolNode(
        node_id=name,
        dispatcher=app.dispatcher,
        tool_def=tool_def,
        func=func
    )

def Crew(
    app: LoomApp,
    name: str,
    agents: List[AgentNode]
) -> CrewNode:
    """Helper to create a CrewNode."""
    return CrewNode(
        node_id=name,
        dispatcher=app.dispatcher,
        agents=agents
    )
