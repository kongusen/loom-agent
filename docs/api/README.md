# API Reference

This section provides detailed API references for Loom submodules.

## Structure

- **`loom.builtin`**: Ready-to-use components.
    - `llms`: OpenAILLM, DeepSeekLLM, etc.
    - `tools`: `@tool`, `ToolBuilder`.
    - `memory`: `InMemoryMemory`, `PersistentMemory`.

- **`loom.execution`**: Core runtime.
    - `Agent`: The main orchestrator.
    - `RecursiveEngine`: The think-act loop.

- **`loom.patterns`**: Composition.
    - `Sequence`
    - `Group`
    - `Router`
