# Cognitive Orchestration

**Orchestration** is the ability to coordinate multiple cognitive nodes to solve problems that are too complex for a single model. This is the realization of **Axiom 5: "Thinking is Orchestration"**.

Loom provides three diverse patterns of orchestration to handle different types of problems.

## 1. Delegation (The Recursive Pattern)

**Best for**: Recursive problem solving, dividing large tasks.

In early versions of Loom, this was handled by a complex `FractalOrchestrator`. In the modern, simplified network, this is handled by **Native Recursion**.

*   **Flow**: Top-down (Parent -> Child).
*   **Key Component**: `NodeContainer` and sub-task Tools.
*   **Mechanism**: The LLM decides to break a task down. It uses a tool to "delegate" a piece of work. The system instantiates a child, isolates it, and runs the sub-task.

## 2. Routing (The Attention Pattern)

**Best for**: Classification, directing queries to specialists.

In this pattern, a **Router** node analyzes an incoming request and decides "Who is best suited to handle this?". It acts like a traffic controller.

*   **Flow**: One-to-One (Dynamic).
*   **Key Component**: `RouterOrchestrator` (`loom.orchestration.router`).
*   **Mechanism**: Uses semantic matching or LLM reasoning to select the best target node.

## 3. Collaboration (The Crew Pattern)

**Best for**: Multi-step workflows, creative brainstorming.

In this pattern, a **Crew** of agents works together. They might pass a document down a linear assembly line (Chain) or work on different aspects simultaneously (Parallel).

*   **Flow**: Horizontal (Peer-to-Peer).
*   **Key Component**: `CrewOrchestrator` (`loom.orchestration.crew`).
*   **Mechanism**: A defined workflow (Sequential or Hierarchical) where output from one agent becomes input for another.

## Choosing a Pattern

*   Use **Delegation** (Native) when the problem is self-similar but smaller (e.g., "Write App" -> "Write Class").
*   Use **Routing** when the problem needs a specific expert (e.g., "Ask Database" vs "Ask Search Engine").
*   Use **Collaboration** when the workflow is a known process (e.g., "Research -> Draft -> Edit").
