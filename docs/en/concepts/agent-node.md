# Agent Patterns & Node Mechanism

Loom unifies all active components under the concept of a **Node**. Whether it's a simple tool, a complex agent, or a team of agents, they are all Nodes that communicate via standard protocols.

## The Node Protocol

Every component in Loom implements the `NodeProtocol`. This ensures that any part of the system can communicate with any other part without knowing its internal implementation.

```python
class NodeProtocol(Protocol):
    node_id: str
    
    async def process(self, event: CloudEvent) -> CloudEvent:
        """Process an incoming event and return a response."""
        ...
```

### Fractal Recursion

Because Agents and workflows (Crews) share the same `Node` interface, they can be composed infinitely.

*   **Agent A** can call **Agent B**.
*   **Agent B** can call a **Crew C** (which contains Agents D, E, F).
*   **Agent D** can call **Agent A** (handling cycles via depth limits).

This **Fractal Architecture** allows you to build complex systems from simple, self-similar building blocks.

## Agent Architecture

An `AgentNode` is a specific implementation of a Node that possesses **Cognition**.

### Internals
1.  **Ingest**: Receives a `CloudEvent`.
2.  **Cognition**:
    *   Retrieves Context (Memory).
    *   Decides Mode (System 1/2).
    *   Generates a Plan (if System 2).
3.  **Execution (Fractal Orchestrator)**:
    *   Executes Tools.
    *   Delegates sub-tasks to other Nodes.
4.  **Synthesize**: Formulates the final response.

## Agent Patterns

Loom supports various agentic patterns seamlessly:

### 1. ReAct (Reasoning + Acting)
The standard pattern where an agent reasons, selects a tool, executes it, observes the output, and repeats. This is the default behavior of `AgentNode` in System 2 mode.

### 2. Planning (Plan-and-Solve)
The agent generates a multi-step plan first, then executes it step-by-step.
*   **Implementation**: Done via the `PlannerSkill` or implicitly by the LLM in System 2.

### 3. Crew / Swarm
A group of agents working together.
*   **SequentialCrew**: Agents pass tasks in a chain (A -> B -> C).
*   **HierarchicalCrew**: A leader agent delegates to worker agents.

In Loom, a `Crew` is just another `Node`. To the caller, it looks exactly like a single Agent.

## Recursion & Delegation

Loom v0.3.6 introduces **Infinite Recursion**. An agent can decide to **delegate** a sub-task to another Node.

```python
# User asks: "Research X and write a report."

# Agent A (Manager)
#  -> Delegates "Research X" to Agent B (Researcher)
#       -> Agent B searches web, summarizes.
#       -> Agent B returns summary.
#  -> Delegates "Write Report" to Agent C (Writer)
#       -> Agent C takes summary, writes text.
#       -> Agent C returns text.
#  -> Agent A returns final report to User.
```

This is handled by the `FractalOrchestrator`, which manages the call stack and ensures context is passed correctly (and compressed if necessary) between layers.
