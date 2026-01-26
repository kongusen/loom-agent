# Cognitive Orchestration

**Orchestration** is the ability to coordinate multiple cognitive nodes to solve problems that are too complex for a single model. This is the realization of **Axiom 5: "Thinking is Orchestration"**.

Loom provides multiple patterns of orchestration, now unified under the **Fractal Architecture** and **CompositeNode**.

## 1. Composition Patterns (The Fractal Approach)

The primary way to orchestrate in Loom v0.4+ is via **Composition**. Instead of special orchestrator classes, we use `CompositeNode` with different strategies.

### A. Sequential Composition (Chain)
**Best for**: Assembly lines, step-by-step processes.

*   **Mechanism**: `CompositeNode(strategy=SequentialStrategy())`
*   **Flow**: Child A -> Child B -> Child C
*   **Example**: Researcher -> Writer -> Editor

### B. Parallel Composition (Map-Reduce)
**Best for**: Brainstorming, independent research, multi-perspective analysis.

*   **Mechanism**: `CompositeNode(strategy=ParallelStrategy())`
*   **Flow**: Parent splits task -> All Children execute at once -> Results aggregated.
*   **Example**: Three different analysts reviewing the same stock ticker.

### C. Conditional Composition (Routing)
**Best for**: Dynamic decision making, expert selection.

*   **Mechanism**: `CompositeNode(strategy=ConditionalStrategy(selector_func))`
*   **Flow**: Task enters -> Selector decides -> One specific child executes.
*   **Example**: Customer Service Router (Refunds vs. Tech Support).

## 2. Delegation (The Recursive Tooling)

**Best for**: Ad-hoc problem solving, "Agentic" planning.

While Composition is structural (defined at build time), **Delegation** is dynamic (defined at runtime).

*   **Mechanism**: An Agent uses a tool (e.g., `delegate_subtask`) to spawn a child node on the fly.
*   **Flow**: Parent -> new Child -> Parent.
*   **Note**: This creates a temporary Fractal branch that dissolves after completion.

## Choosing a Pattern

*   **Structure it** (`CompositeNode`) when you know the workflow in advance (e.g., a known standard operating procedure).
*   **Delegate it** (`Tool`) when you want the Agent to figure out the plan itself.
