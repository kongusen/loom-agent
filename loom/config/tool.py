"""
Tool Configuration & Factory
"""

import importlib
import os
from typing import Any

from pydantic import BaseModel, Field

from loom.kernel.core import Dispatcher
from loom.node.tool import ToolNode
from loom.protocol.mcp import MCPToolDefinition


class ToolConfig(BaseModel):
    """
    Configuration for a Tool.
    """
    name: str
    description: str = ""
    python_path: str = Field(..., description="Dot-path to the python function e.g. 'my_pkg.tools.search'")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Input schema properties")
    env_vars: dict[str, str] = Field(default_factory=dict)

class ToolFactory:
    """
    Factory to load valid ToolConfigs into ToolNodes.
    """

    @staticmethod
    def create_node(
        config: ToolConfig,
        node_id: str,
        dispatcher: Dispatcher
    ) -> ToolNode:
        # 1. Load function
        module_name, func_name = config.python_path.rsplit(".", 1)
        try:
            mod = importlib.import_module(module_name)
            func = getattr(mod, func_name)
        except (ImportError, AttributeError) as e:
            raise ValueError(f"Could not load tool function {config.python_path}: {e}")

        # 2. Apply Env Vars
        for k, v in config.env_vars.items():
            os.environ[k] = v

        # 3. Create Definition
        tool_def = MCPToolDefinition(
            name=config.name,
            description=config.description,
            inputSchema={
                "type": "object",
                "properties": config.parameters
            }
        )

        # 4. Create Node
        return ToolNode(
            node_id=node_id,
            dispatcher=dispatcher,
            tool_def=tool_def,
            func=func
        )
