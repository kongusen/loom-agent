# Using Tools

Loom builds on the **Model Context Protocol (MCP)** for tool definitions. This ensures your tools are standard-compliant and portable.

## 1. Define schema (`MCPToolDefinition`)
Describe the tool for the LLM.

```python
from loom.protocol.mcp import MCPToolDefinition

weather_tool_def = MCPToolDefinition(
    name="get_weather",
    description="Get current weather for a location",
    inputSchema={
        "type": "object",
        "properties": {
            "city": {"type": "string"}
        },
        "required": ["city"]
    }
)
```

## 2. Implement logic (Python Function)
Write the actual code.

```python
async def get_weather(args: dict):
    city = args["city"]
    # In reality, call an API
    return f"The weather in {city} is Sunny."
```

## 3. Wrap in `ToolNode`
Connect it to the Loom network.

```python
from loom.node.tool import ToolNode

weather_node = ToolNode(
    node_id="tool/weather",
    dispatcher=app.dispatcher,
    tool_def=weather_tool_def,
    func=get_weather
)
```

## 4. Register
Always register tools with the app so they can be discovered/called.

```python
app.add_node(weather_node)
```
