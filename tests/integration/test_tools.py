"""
Integration Test: Tool Ecosystem
"""

import pytest
from loom.api.main import LoomApp
from loom.api.factory import Tool

def calculate_mortgage(principal: int, rate: float, years: int) -> float:
    """Calculates monthly mortgage payment."""
    return 0.0

@pytest.mark.asyncio
async def test_tool_schema_generation():
    """Verify Python function -> MCP Schema conversion."""
    app = LoomApp()
    tool = Tool(app, "mortgage", calculate_mortgage)
    
    schema = tool.tool_def.input_schema
    
    assert schema["type"] == "object"
    assert schema["properties"]["principal"]["type"] == "integer"
    assert schema["properties"]["rate"]["type"] == "number" # float
    assert schema["properties"]["years"]["type"] == "integer"
    
    assert "principal" in schema["required"]
    assert "rate" in schema["required"]
    assert "years" in schema["required"]
