# Quickstart: Your First Agent

This guide will walk you through building a simple "Math Assistant" agent that can perform calculations and remember context.

## 1. Create the App
The `LoomApp` is the central controller.

```python
from loom.api.main import LoomApp

app = LoomApp()
```

## 2. Define a Tool
Agents use tools to interact with the world. Loom uses the **MCP (Model Context Protocol)** standard for tool definitions.

```python
from loom.node.tool import ToolNode
from loom.protocol.mcp import MCPToolDefinition

# Define the Tool Metadata (Schema)
calc_def = MCPToolDefinition(
    name="calculator",
    description="Adds two numbers",
    inputSchema={
        "type": "object",
        "properties": {
            "a": {"type": "number"},
            "b": {"type": "number"}
        }
    }
)

# Define the Tool Implementation (Function)
async def add_numbers(args):
    return args['a'] + args['b']

# Create the Tool Node
calc_tool = ToolNode(
    node_id="tool/calc",
    dispatcher=app.dispatcher,
    tool_def=calc_def,
    func=add_numbers
)
```

## 3. Create the Agent
Agents are nodes that perceive, reason, and act.

```python
from loom.node.agent import AgentNode

agent = AgentNode(
    node_id="agent/math",
    dispatcher=app.dispatcher,
    role="Math Expert",
    system_prompt="You are a helpful math tutor. Use the calculator for sums.",
    tools=[calc_tool] 
)
```

## 4. Register and Run
Add the nodes to the app and send a task.

```python
import asyncio

async def main():
    # Register components
    app.add_node(calc_tool)
    app.add_node(agent)
    
    # Run the task
    print("Sending task...")
    result = await app.run(
        task="What is 55 plus 120?", 
        target="agent/math"
    )
    
    print(f"Agent Response: {result['response']}")

if __name__ == "__main__":
    asyncio.run(main())
```

## What happened?
1. **Perceive**: The Agent received the task and stored it in its **Metabolic Memory**.
2. **Think**: The Agent (using a Mock LLM by default) reasoned it needed the `calculator` tool.
3. **Act**: It sent a `node.request` to the `tool/calc` node.
4. **Observe**: The tool executed effectively (RPC) and returned `175`.
5. **Answer**: The Agent synthesized the final answer.

## Next Steps
- Learn about [Memory](../02_core_concepts/memory_system.md)
- Explore [Configuration](../04_advanced/configuration.md)
