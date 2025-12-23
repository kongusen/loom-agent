# Comparison Guide

## Loom vs LangChain (LangGraph)
-   **LangChain**: A vast library of integrations. Great for rapid prototyping of chains.
-   **Loom**: An opinionated *Distributed System* for agents. Focuses on lifecycle, memory metabolism, and event sourcing. Loom is "heavier" architecturally but better for long-running autonomous processes.

## Loom vs AutoGPT
-   **AutoGPT**: A single, very powerful loop. Often hard to control.
-   **Loom**: "Controlled Fractal". You build hierarchies of constrained agents (Crews) rather than one giant loop.

## Loom vs CrewAI
-   **CrewAI**: Excellent high-level orchestration for Role-Playing.
-   **Loom**: Lower-level protocol. You can implement CrewAI patterns *on top* of Loom. Loom adds features like Event Sourcing and the Event Bus which CrewAI abstracts away.
