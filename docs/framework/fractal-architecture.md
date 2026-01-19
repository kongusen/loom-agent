# Fractal Architecture

Loom employs a **Fractal Architecture** to solve the problem of **Spatial Entropy** (Complexity). By enabling infinite recursion, the system allows for **Infinite Semantic Depth** while maintaining a constant O(1) cognitive load on any single node.

## The Core Concept: Native Recursion

Unlike early designs that relied on complex, heavy-weight "Orchestrators" to manage task decomposition, Loom v0.4 embraces **Native Recursion**.

In this model, "recursion" is not a special engine class, but a natural result of an Agent having access to tools that can spawn children. If an Agent can call a function `delegate(task)`, and that function creates a new Agent, you have a fractal system.

### Solving the Complexity Wall
Traditional agents hit a "Complexity Wall" when context fills up. Loom avoids this by ensuring that **no single node ever sees the full complexity**. A node only sees its immediate layer.

## Components

### 1. NodeContainer (The Holon)
The `NodeContainer` (`loom.fractal.container`) is simple. It is a lightweight wrapper that holds a collection of child nodes. It provides the mechanism for parent nodes to "own" and manage the lifecycle of children.

### 2. Task Tools (The Interface)
Recursion happens via the **Tool System** (Axiom 6).
*   **Decomposition**: The LLM naturally breaks down a prompt.
*   **Delegation**: The Agent calls a `create_subtask` tool.
*   **Execution**: Loom instantiates a new child node to handle that call.

### 3. Result Synthesizer
The `ResultSynthesizer` (`loom.fractal.synthesizer`) acts as the "Sense-Making" layer. Once child nodes complete their work, the synthesizer aggregates their results.

It supports:
1.  **Structured**: JSON aggregation.
2.  **LLM-based**: Narrative weaving.
3.  **Concatenate**: Simple joining.

## How it Works

1.  **Receive Task**: Agent A receives "Build a Mobile App".
2.  **Reason**: Agent A thinks "This is too big. I need a UI designer and a Backend dev."
3.  **Tool Call**: Agent A calls `delegate(role="UI Designer", task="Design Login Screen")`.
4.  **Fractal Step**: Loom creates Agent B (UI Designer).
5.  **Recursion**: Agent B receives the task. If it's still too complex, Agent B calls `delegate` again (creating Agent C).
6.  **Return**: Results bubble back up the stack.

This process enables **Infinite Semantic Depth** without complex code paths. The "Intelligence" of the recursion comes from the Model, not the Python framework.
