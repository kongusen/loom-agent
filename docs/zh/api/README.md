# API 参考

本节提供 Loom 子模块的详细 API 参考。

## 结构

- **`loom.builtin`**: 开箱即用的组件。
    - `llms`: OpenAILLM, DeepSeekLLM 等。
    - `tools`: `@tool`, `ToolBuilder`。
    - `memory`: `InMemoryMemory`, `PersistentMemory`。

- **`loom.execution`**: 核心运行时。
    - `Agent`: 核心协调器。
    - `RecursiveEngine`: 思考-行动循环。

- **`loom.patterns`**: 组合模式。
    - `Sequence` (串行)
    - `Group` (并行)
    - `Router` (路由)
