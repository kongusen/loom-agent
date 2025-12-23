# Nodes and Topology

The fundamental building block of Loom is the **Node**.

## The Fractal Philosophy
In Loom, everything is a Node. This allows for a "Fractal" architecture where complex systems (Swarms) look and behave exactly like simple systems (single Agents).

- An **Agent** is a Node.
- A **Tool** is a Node.
- A **Crew** (a group of Agents) is also a Node.

This means you can treat a whole swarm of agents as a single "Tool" for another, higher-level Agent.

## Node Types

### 1. Base Node
The abstract base class. Handles:
- Identity (`node_id`, `source_uri`)
- Communication (Event Bus interaction)
- Protocol compliance

### 2. ToolNode
Wraps a specific function or capability.
- Implements **MCP (Model Context Protocol)**.
- Stateless and deterministic (usually).
- **Usage**:
  ```python
  tool = ToolNode(..., func=my_function)
  ```

### 3. AgentNode
An intelligent node driven by an LLM.
- Has **Memory** (Metabolic).
- Has **Identity** (Role, System Prompt).
- executed a **ReAct Loop** (Reasoning + Acting).
- **Usage**:
  ```python
  agent = AgentNode(..., role="Analyst", tools=[tool_node])
  ```

### 4. RouterNode (`AttentionRouter`)
A specialized node for traffic control.
- Uses an LLM to analyze the intent of a task.
- Routes the task to the best-suited child node.
- **Usage**:
  ```python
  router = AttentionRouter(..., agents=[math_agent, writer_agent])
  ```

### 5. CrewNode
Orchestrates a group of agents in a pattern.
- **Sequential**: A -> B -> C (Pipeline)
- **Parallel**: Run all, aggregate results (Map-Reduce)
- **Usage**:
  ```python
  crew = CrewNode(..., agents=[a, b], pattern="sequential")
  ```
