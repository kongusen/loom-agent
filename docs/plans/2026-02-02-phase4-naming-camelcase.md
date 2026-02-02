# Phase 4: 命名规范统一（驼峰命名法）实施计划

> **前置条件**: Phase 1–3 已完成。  
> **注意**: 本阶段为 **破坏性变更**：公开 API 从 snake_case 改为 camelCase，影响所有调用方与文档。Python 社区惯例为 PEP 8（snake_case），采纳驼峰需团队明确决策。

**Goal:** 统一公开 API 命名为驼峰（camelCase），与研究报告 §5.4 一致；内部实现可保留 snake_case 或分批迁移。

**依据文档:**
- `docs/LOOM_AGENT_0.5.0_RESEARCH_REPORT.md` §5.4 Phase 4
- `docs/API_REFACTOR_DESIGN.md` §5.4、命名对照表

**Tech Stack:** Python 3.10+, pytest

---

## 现状简要（规划前核对）

- **当前命名**: 全库为 snake_case（execute_task、system_prompt、event_bus、node_id、max_iterations 等），符合 PEP 8。
- **影响范围**: `execute_task` / `stream_thinking` / `run` 等约 154+ 处引用、40+ 文件；NodeProtocol 接口（execute_task、get_capabilities）；Agent.create() 参数；文档与示例。
- **可选决策**: 若团队决定保持 PEP 8，可将 Phase 4 标记为「不实施」或仅做「参数别名」（如同时支持 node_id 与 nodeId）。

---

## 第一部分：前置检查与决策

### Task 0: 确认是否实施 Phase 4

**Step 1: 决策**

- **选项 A（全量驼峰）**: 公开 API 全部改为 camelCase，不向后兼容；需迁移指南与大版本号（如 v0.6.0）。
- **选项 B（仅参数别名）**: Agent.create() 等支持 camelCase 参数名（nodeId、systemPrompt），内部与文档同时支持 snake_case 与 camelCase，兼容过渡。
- **选项 C（不实施）**: 保持 PEP 8 snake_case，关闭 Phase 4，在研究报告/计划中注明「命名规范维持 snake_case」。

**Step 2: 基线（若选 A 或 B）**

```bash
pytest tests/ -v --tb=short
# 可选：保存基线
pytest tests/ -v --tb=short > test_baseline_before_phase4.txt 2>&1
```

---

## 第二部分：公开 API 命名对照（若选 A）

以下为 API_REFACTOR_DESIGN 与研究报告中的对照表，实施时需全局替换并更新测试/文档。

### 协议层（NodeProtocol / BaseNode）

| 旧名称（snake_case） | 新名称（camelCase） | 说明 |
|----------------------|---------------------|------|
| `execute_task` | `executeTask` | NodeProtocol 核心方法，所有节点实现 |
| `get_capabilities` | `getCapabilities` | 能力声明 |
| `get_node_type` | `getNodeType` | 节点类型（若有对外暴露） |
| `publish_thinking` | `publishThinking` | BaseNode/Agent 观测 |
| `publish_tool_call` | `publishToolCall` | 观测 |
| `query_collective_memory` | `queryCollectiveMemory` | 集体记忆查询 |

### Agent 公开方法

| 旧名称 | 新名称 | 说明 |
|--------|--------|------|
| `execute_task` | `executeTask` | 继承自 NodeProtocol |
| `run` | `run` | 保持不变（简短常用） |
| `stream_thinking` | `streamThinking` | 流式输出 |
| `delegate` | `delegate` | 保持不变（或 `delegateTask`） |
| `get_node_type` | `getNodeType` | 若有对外 |

### Agent.create() / Agent.builder() 参数

| 旧名称 | 新名称 |
|--------|--------|
| `node_id` | `nodeId` |
| `system_prompt` | `systemPrompt` |
| `event_bus` | `eventBus` |
| `max_iterations` | `maxIterations` |
| `max_context_tokens` | `maxContextTokens` |
| `knowledge_base` | `knowledgeBase` |
| `require_done_tool` | `requireDoneTool` |
| `tool_registry` | `toolRegistry` |
| `sandbox_manager` | `sandboxManager` |
| `skill_registry` | `skillRegistry` |
| `skill_activator` | `skillActivator` |
| `knowledge_max_items` | `knowledgeMaxItems` |
| `knowledge_relevance_threshold` | `knowledgeRelevanceThreshold` |

### AgentBuilder 链式方法

| 旧名称 | 新名称 |
|--------|--------|
| `with_system_prompt` | `withSystemPrompt` |
| `with_tools` | `withTools` |
| `with_memory` | `withMemory` |
| `with_knowledge_base` | `withKnowledgeBase` |
| `with_event_bus` | `withEventBus` |
| `with_iterations` | `withIterations` |
| `with_done_tool` | `withDoneTool` |
| `build` | `build`（保持） |

---

## 第三部分：实施任务（若选 A）

### Task 1: 协议层重命名

**Files:** `loom/protocol/node.py`（NodeProtocol）、`loom/agent/base.py`、`loom/agent/core.py`

**Step 1:** 在 NodeProtocol 中将 `execute_task` → `executeTask`，`get_capabilities` → `getCapabilities`（或保留旧名作为别名一版）。

**Step 2:** 所有实现类（Agent、BaseNode、CompositeNode、SkillAgentNode、Pipeline 等）同步重命名实现方法。

**Step 3:** 内部调用处（如 `await self.execute_task(task)`）改为 `await self.executeTask(task)`（或通过别名保持兼容）。

**Step 4:** 运行 `pytest tests/ -v --tb=short`，修复失败用例。

---

### Task 2: Agent 公开方法重命名

**Files:** `loom/agent/core.py`、`loom/agent/base.py`

**Step 1:** `stream_thinking` → `streamThinking`，`get_node_type` → `getNodeType`；`publish_thinking` / `publish_tool_call` / `query_collective_memory` 等按对照表重命名。

**Step 2:** 内部调用与测试、示例、文档中所有引用更新。

**Step 3:** 运行测试，修复失败。

---

### Task 3: Agent.create() / Agent.builder() 参数重命名

**Files:** `loom/agent/core.py`（create、__init__、AgentBuilder）

**Step 1:** Agent.create() 与 Agent.__init__ 的参数名改为 camelCase（见上表）；若需兼容，可保留 snake_case 作为别名（kwargs 映射）。

**Step 2:** AgentBuilder 的 config 键与 with_* 方法名改为 camelCase。

**Step 3:** 全库搜索并替换调用处（tests、examples、docs）。

**Step 4:** 运行测试，修复失败。

---

### Task 4: 测试与示例更新

**Files:** `tests/**/*.py`、`examples/**/*.py`、`docs/**/*.md`、`wiki/**/*.md`

**Step 1:** 批量替换：execute_task → executeTask，system_prompt → systemPrompt 等（按对照表）。

**Step 2:** 运行 `pytest tests/ -v --tb=short`，确保全部通过。

**Step 3:** 检查示例可运行：`python examples/conversational_assistant_tui.py` 等（按需）。

---

### Task 5: 文档与迁移说明

**Files:** `docs/usage/api-reference.md`、`docs/usage/getting-started.md`、`docs/usage/migration-v0.5.md`、README、wiki

**Step 1:** 所有文档中的 API 示例与参数表改为 camelCase。

**Step 2:** 在 `docs/usage/migration-v0.5.md` 或新建 `migration-v0.6.md` 中增加「v0.5.x → v0.6.0 命名变更」：snake_case → camelCase 对照表与替换示例。

**Step 3:** CHANGELOG 中注明破坏性变更与迁移步骤。

---

## 第四部分：若选 B（仅参数别名）

- 在 Agent.create() 与 __init__ 中同时接受 snake_case 与 camelCase 参数（如 node_id 与 nodeId），内部统一转为同一属性。
- 文档与示例可优先使用 camelCase，旧代码仍可用 snake_case。
- 协议方法（execute_task 等）保持 snake_case，不重命名。
- 工作量与影响面远小于选项 A。

---

## 验证清单（若选 A）

- [ ] NodeProtocol 与所有实现类的方法名为 camelCase（或旧名仅作别名）
- [ ] Agent.create() / Agent.builder() 参数名为 camelCase
- [ ] 所有测试通过
- [ ] 所有示例可运行且使用新命名
- [ ] 文档与迁移指南已更新
- [ ] CHANGELOG 已注明破坏性变更

---

## 与研究报告的对应关系

| 研究报告 §5.4 Phase 4 任务 | 本计划 Task |
|----------------------------|-------------|
| 重命名 Agent 方法 | Task 1（协议）、Task 2（Agent 方法） |
| 重命名参数名 | Task 3 |
| 更新所有内部方法名 | Task 1–2（公开部分）；内部可保留 snake_case |
| 更新测试代码 | Task 4 |
| 更新文档和示例 | Task 4–5 |

---

## 下一步

Phase 4 完成后，进入 **Phase 5: LLM 自主决策优化**（参见 `docs/LOOM_AGENT_0.5.0_RESEARCH_REPORT.md` §5.5）。若 Phase 4 选「不实施」，可直接进入 Phase 5 或 Phase 6（测试与文档收尾）。
