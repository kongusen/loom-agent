# What's New in v0.5.0

**版本**: v0.5.0  
**更新日期**: 2026-02

本文档汇总 v0.5.0 相对 v0.4.x 的新增与变更，便于快速对齐当前文档与实现。

---

## 1. 设计原则（0.5.0 核心理念）

- **LLM 自主决策**：框架提供机制（mechanism），LLM 提供策略（policy）；移除“由框架决定是否用工具/分形”的开关与启发式。
- **渐进式披露**：简单用法最少参数（如 `Agent.create(llm)`），高级用法显式注入组件（event_bus、sandbox_manager、capabilities）。
- **统一入口**：推荐 `Agent.create(llm, ...)` 或 `Agent.from_llm(llm, ...)`；LoomApp 已弃用，0.5.0 以 Agent 为中心。

---

## 2. 新增与改进

### 2.1 Agent 与工具

- **工具列表与执行一致（P0 修复）**：`_get_available_tools()` 现已包含 `sandbox_manager` 中的工具，LLM 可见工具与执行来源一致。
- **始终提供全部工具**：上下文查询工具、工具创建（create_tool）、委派（delegate_task/create_plan）等由 LLM 自主选择使用，不再通过配置开关隐藏。

### 2.2 统一 Skill 与能力

- **统一 SkillRegistry**：  
  - 仅保留一套 `SkillRegistry`（`loom.skills.registry`）。  
  - 支持 **Loader 来源**（文件系统/数据库，async `get_skill` / `get_all_metadata`）与 **运行时注册**（`register_skill`，dict 格式，兼容原 skill_market）。  
  - `get_skill(skill_id)`：先查运行时，再查 Loaders；返回 `SkillDefinition`（运行时 dict 会转为 SkillDefinition）。  
  - `loom.skills.skill_registry` 现为薄封装，导出同一 `SkillRegistry` 与 `skill_market` 单例。
- **SkillActivator 依赖校验**：  
  - 新增参数 `tool_manager: SandboxToolManager | None`。  
  - 依赖校验优先使用 `tool_manager.list_tools()`（与执行来源一致），无 tool_manager 时回退到 `tool_registry.has()`。
- **CapabilityRegistry**：  
  - `find_relevant_capabilities(...)` 改为 **async**，Skill 列表通过 `list_skills_async()` 获取（含 Loader + 运行时）。  
  - `validate_skill_dependencies(skill_id)` 改为 **async**，内部使用 `get_skill`（支持 Loader 与运行时）并统一用 SandboxToolManager 校验工具依赖。

### 2.3 分形与复杂度

- **移除框架侧复杂度评估**：  
  - `estimate_task_complexity`、`should_use_fractal` 已从 `loom.fractal.utils` 及包导出中移除。  
  - 是否委派、是否分形由 LLM 通过 `delegate_task` 等工具自主决定，不再由框架启发式判定。

### 2.4 动态工具创建

- **tool_creation 与沙盒**：  
  - 当存在 `sandbox_manager` 时，动态创建的工具仅注册到沙盒，不再在本地做重复存储；  
  - 无 sandbox_manager 时仍使用本地 `created_tools` / `tool_definitions`。

---

## 3. 破坏性变更与移除项

- **Agent**  
  - 移除参数：`enable_tool_creation`、`enable_context_tools`。  
  - 行为：始终创建上下文工具执行器与动态工具执行器，是否调用由 LLM 决定。
- **ContextToolExecutor**  
  - 构造函数仅保留 `memory`，移除未使用的 `event_bus` 参数。
- **api.models.AgentConfig（若仍使用）**  
  - 已移除字段：`enable_context_tools`、`enable_tool_creation`。
- **fractal**  
  - 移除导出：`estimate_task_complexity`、`should_use_fractal`。  
  - `loom.fractal.utils` 保留为占位模块，无上述函数。
- **CapabilityRegistry**  
  - `find_relevant_capabilities`、`validate_skill_dependencies` 改为 **async**，调用处需使用 `await`。

---

## 4. 文档与索引

- **迁移**：详见 [Migration Guide: v0.4.x → v0.5.0](migration-v0.5.md)。  
- **入门与 API**：  
  - [Getting Started](getting-started.md)  
  - [API Reference](api-reference.md)  
- **配置与继承**：  
  - [AgentConfig 继承](agent-config-inheritance.md)

---


