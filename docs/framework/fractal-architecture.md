# Fractal Architecture

> **"Infinite Semantic Depth in Finite Cognitive Space"**

Loom employs a **Fractal Architecture** to solve the problem of **Spatial Entropy** (Complexity). Inspired by the **Koch Snowflake**, the system implements a recursive composition pattern that allows for infinite task decomposition while ensuring that the cognitive load on any single node remains constant (O(1)).

## The Core Concept: Recursive Composition

In Loom's fractal model, every component—whether a simple Agent or a complex team—is a **Node**. Nodes can contain other Nodes, forming a tree structure of arbitrary depth.

### The Koch Snowflake Analogy

Just as a Koch curve increases its perimeter infinitely within a finite area by recursively splitting line segments, Loom agents increase their "thought perimeter" (complexity handling) by recursively delegating sub-tasks.

```mermaid
graph TD
    Root[Root Agent<br>O(1) Context] -->|Delegate| Child1[Child Agent 1<br>O(1) Context]
    Root -->|Delegate| Child2[Child Agent 2<br>O(1) Context]
    Child1 -->|Delegate| GrandChild1[GrandChild A<br>O(1) Context]
    Child1 -->|Delegate| GrandChild2[GrandChild B<br>O(1) Context]
```

- **Self-Similarity**: Every level of the hierarchy looks and behaves the same.
- **Complexity Conservation**: No matter how deep the tree goes, each node only manages its immediate children.

## Components

### 1. NodeProtocol (The Uniform Interface)
The foundation of the architecture is the `NodeProtocol`. All entities in the system must strictly adhere to this interface (Axiom 1).

```python
class NodeProtocol(Protocol):
    node_id: str
    agent_card: AgentCard

    async def execute_task(self, task: Task) -> Task:
        """Standard execution entry point"""
        ...
```

This transparency means a parent node doesn't need to know if it's delegating to a single LLM Agent or a massive sub-system of 100 agents; it just calls `execute_task`.

### 2. CompositeNode (The Container)
The `CompositeNode` replaces the legacy `NodeContainer`. It implements the **Composite Pattern**, allowing it to treat individual objects and compositions of objects uniformly.

- **Recursive**: A `CompositeNode` implements `NodeProtocol`.
- **Flexible strategies**: How children are executed is determined by a `CompositionStrategy`.

```python
# Example: Creating a fractal tree
team = CompositeNode(
    children=[agent_a, agent_b],
    strategy=ParallelStrategy()
)
```

### 3. Composition Strategies
The `CompositeNode` delegates the actual flow control to a strategy:

- **`SequentialStrategy`**: Executes children one by one (Chain of Thought).
- **`ParallelStrategy`**: Executes children concurrently (Map-Reduce).
- **`ConditionalStrategy`**: Dynamically selects children based on task state (Router).

## Data Flow: Memory & Context

Fractal architecture creates challenges for context management. Loom solves this with **Scoped Memory** and **Context Injection**.

- **Scope-based Memory**:
  - `LOCAL`: Private to the node.
  - `SHARED`: Accessible by parent and children.
  - `GLOBAL`: Accessible by the entire organism.

- **Minimal Context**: A parent node selectively injects only the necessary context into the sub-task, preventing the child from triggering a context overflow.

## Execution Flow

1.  **Receipt**: A `CompositeNode` receives a `Task`.
2.  **Strategy**: The configured Strategy determines the execution order.
3.  **Delegation**: The Strategy calls `execute_task` on Child Nodes.
4.  **Synthesis**: Results from children bubble up and are synthesized into the parent's result.

This architecture proves that **"Intelligence is an emergent property of the orchestration,"** not just the raw power of the underlying LLM.
