"""
Tool Node (Fractal System)
"""

from typing import Any, Callable, Dict

from loom.protocol.cloudevents import CloudEvent
from loom.protocol.mcp import MCPToolDefinition
from loom.node.base import Node
from loom.kernel.dispatcher import Dispatcher

class ToolNode(Node):
    """
    A Node that acts as an MCP Server for a single tool.
    Reference Implementation.
    """
    
    def __init__(
        self,
        node_id: str,
        dispatcher: Dispatcher,
        tool_def: MCPToolDefinition,
        func: Callable[[Dict[str, Any]], Any]
    ):
        super().__init__(node_id, dispatcher)
        self.tool_def = tool_def
        self.func = func
        
    async def process(self, event: CloudEvent) -> Any:
        """
        Execute the tool.
        Expects event.data to contain 'arguments'.
        """
        args = event.data.get("arguments", {})
        
        # In a real system, validate against self.tool_def.input_schema
        
        # Execute
        try:
            # Check if func is async
            import inspect
            if inspect.iscoroutinefunction(self.func):
                result = await self.func(args)
            else:
                result = self.func(args)
                
            return {"result": result}
        except Exception as e:
            # Re-raise to trigger node.error in Base Node
            raise RuntimeError(f"Tool execution failed: {e}")
