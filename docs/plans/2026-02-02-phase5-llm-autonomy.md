# Phase 5: LLM 自主决策优化 实施计划

> **前置条件**: Phase 1–4 已完成（或 Phase 4 选择不实施亦可进入）。  
> **目标**: 移除硬编码决策逻辑，将策略权交给 LLM，符合「框架提供机制、LLM 提供策略」原则。

**依据文档:**
- `docs/LOOM_AGENT_0.5.0_RESEARCH_REPORT.md` §3.4 设计偏离清单、§4.4 LLM 自主决策、§5.5 Phase 5
- `docs/plans/REMAINING_UPDATES.md` 四、后续阶段

**Tech Stack:** Python 3.10+, pytest

---

## 一、现状与范围

### 1.1 已完成的清理（Phase 1–2）

| 项 | 状态 |
|----|------|
| `enable_tool_creation` / `enable_context_tools` | 已移除（Phase 1） |
| `estimate_task_complexity` / `should_use_fractal` | 已移除（`loom/fractal/utils.py` 已清空） |
| 工具列表 | 始终提供所有工具，由 LLM 决定是否使用 |

### 1.2 Phase 5 需处理的偏离

| 偏离 | 位置 | 问题简述 | 目标 |
|------|------|----------|------|
| **预算硬限制** | `loom/fractal/budget.py` + `loom/agent/core.py` | `check_can_create_child` 返回 violation 时 Agent 直接 `raise RuntimeError`，阻止委派 | 改为软限制：将预算/违规信息注入上下文，由 LLM 决定是否继续委派 |
| **硬编码路由** | `loom/orchestration/router.py` | `RouterOrchestrator._select_node()` 根据 action 关键词选择节点，框架决定路由 | 移除或弃用，推荐 Agent + `delegate_task` 由 LLM 指定 target |
| **硬编码重要性** | `loom/memory/core.py` | `_infer_importance(task)` 按 action 类型返回固定分数 | 改为可配置/常量或扩展点，避免框架替 LLM 做重要性判断 |

---

## 二、前置检查（Task 0）

### Step 1: 基线测试

```bash
pytest tests/ -v --tb=short
# 可选：保存基线
# pytest tests/ -v --tb=short > test_baseline_before_phase5.txt 2>&1
```

### Step 2: 依赖确认

- Phase 1–3 已完成（LoomApp/AgentConfig 已清理、工具/技能统一、Agent.create 渐进式披露与 tools= 自动 Sandbox 已就绪）。
- Phase 4 是否实施不影响 Phase 5；若已实施，需在 Phase 5 变更时保持命名一致。

---

## 三、实施任务

### Task 1: 预算控制改为软限制

**目标**: 不因预算违规直接抛错，而是把预算状态与违规信息提供给 LLM，由 LLM 决定是否继续委派。

**涉及文件**: `loom/fractal/budget.py`、`loom/agent/core.py`

**Step 1: 保留 BudgetTracker 的「检查」与「记录」**

- `check_can_create_child()` 保持返回 `BudgetViolation | None`，不在此处抛错。
- `usage`、`record_*` 等接口保持不变，便于观测与审计。

**Step 2: Agent 侧改为软限制**

- 在 `delegate`/创建子 Agent 前调用 `check_can_create_child()`。
- **若存在 violation**：
  - 不 `raise RuntimeError`。
  - 将 `violation` 信息（类型、当前值、限制值、message、suggestion）以及 `_budget_tracker.usage` 的可读摘要，注入到本次委派相关的上下文（例如：作为 `delegate_task` 工具描述中的「当前预算状态」、或注入到即将下发给子节点的 system prompt 片段）。
  - 由调用方（上层 Agent 的 LLM）根据工具结果或 prompt 中的预算信息自行决定是否仍执行委派；若仍执行，则照常 `record_child_created` 并创建子节点。
- **若无 violation**：行为与当前一致，记录并创建子节点。

**Step 3: 可选 — 预算信息注入工具描述**

- 在 `_get_available_tools()` 或构建 `delegate_task` 工具描述时，将当前 `_budget_tracker.usage` 的简要信息（如 depth、children、tokens_used、limits）写入工具描述或额外字段，便于 LLM 在调用前看到预算状态。

**验证**: 单元测试中增加「存在 violation 时不抛错、且预算信息出现在预期上下文」的用例；原有「无 violation 时正常委派」用例仍通过。

---

### Task 2: RouterOrchestrator 移除或弃用

**目标**: 消除「框架根据 action 硬编码选节点」的决策，统一为 LLM 通过 `delegate_task` 指定 target。

**涉及文件**: `loom/orchestration/router.py`、`loom/orchestration/__init__.py`、`loom/api/__init__.py`、`loom/api/README.md`、`loom/orchestration/README.md`、所有引用 `RouterOrchestrator` 的示例/测试。

**方案 A（推荐）: 弃用并保留类**

- 在 `RouterOrchestrator` 类及 `orchestrate`/`_select_node` 上添加 `warnings.warn(DeprecationWarning, ...)`，说明推荐使用 Agent + `delegate_task` 由 LLM 指定目标。
- 文档中注明：仅在不便使用 LLM 决策的遗留/特殊场景下使用，新代码应使用 Agent 与委派工具。

**方案 B: 完全移除**

- 删除 `loom/orchestration/router.py`。
- 从 `loom/orchestration/__init__.py`、`loom/api/__init__.py` 中移除导出。
- 更新 `loom/api/README.md`、`loom/orchestration/README.md` 及所有引用处；若有示例或测试依赖 RouterOrchestrator，改为使用 Agent + delegate 或删除/改写。

**验证**: 若选 A，运行全量测试并确认无新失败；若选 B，grep 无 `RouterOrchestrator` 引用（或仅文档中的弃用说明）。

---

### Task 3: 记忆重要性推断去硬编码

**目标**: 不再由框架对「何种 action 更重要」做硬编码判断，改为可配置或中性默认。

**涉及文件**: `loom/memory/core.py`

**Step 1: 默认行为**

- **选项 A**: `_infer_importance(task)` 改为返回固定中性值（如 `0.5`），不再根据 `task.action` 分支。
- **选项 B**: 保留方法但改为从 `task.metadata` 读取 `importance`（若存在则用，否则返回常量如 `0.5`），不再按 action 类型写死分数。

**Step 2: 可选扩展**

- 若希望上层可注入重要性逻辑，可在 MemoryManager 构造或配置中增加可选回调，例如 `importance_inferrer: Callable[[Task], float] | None`，若提供则优先使用，否则用默认常量。

**验证**: 依赖 `_infer_importance` 或 `_ensure_importance` 的单元测试仍通过；若有测试断言特定 action 得到特定分数，改为断言中性值或通过 metadata/回调注入的值。

---

### Task 4: 复查其他硬编码决策

**目标**: 确保无遗漏的「框架替 LLM 做策略决策」逻辑。

**建议检查**:

- 搜索 `if.*action.*==|elif.*action|complexity|should_use|must_use|force_` 等与决策相关的模式。
- 重点复查：Agent 循环内是否有「根据某条件强制跳过工具/委派/反思」的逻辑；若有，改为仅影响上下文信息（如提示「当前建议……」），而不直接关闭能力。

**输出**: 在计划或 CHANGELOG 中简短列出「已复查并确认无新增硬编码决策」或「已处理项列表」。

---

### Task 5: 测试与文档

- **测试**: 全量 `pytest tests/` 通过；新增/调整的用例覆盖「预算软限制」「Router 弃用/移除」「重要性默认行为」。
- **文档**: 
  - 在 `docs/plans/REMAINING_UPDATES.md` 中将 Phase 5 标为已规划/进行中/已完成。
  - 若对外有「设计原则」或「LLM 自主决策」说明，补充「预算为软限制」「路由由 LLM 委派」「重要性可配置」的简短描述。
  - CHANGELOG 中记录 Phase 5 的破坏性变更（如预算不再抛错、Router 弃用/移除、重要性默认行为变更）。

---

## 四、验证标准（Phase 5 完成）

- 预算超限时不再因委派而 `raise RuntimeError`，预算信息可被 LLM 使用。
- 无「框架根据 action 硬编码选择执行节点」的推荐路径（RouterOrchestrator 已弃用或移除）。
- 记忆重要性不再依赖对 action 类型的硬编码分数（或仅保留可配置/扩展的默认值）。
- 全量测试通过，文档与 CHANGELOG 已更新。

---

## 五、与后续阶段的关系

- **Phase 6（测试与文档）**: Phase 5 完成后，可进入 Phase 6 做集成/端到端测试、API 文档与迁移指南的完善。
- **Phase 4（命名）**: 若在 Phase 5 之后实施 Phase 4，新增或修改的 API（如预算相关的方法名、参数名）需一并纳入驼峰命名范围。

---

*创建日期: 2026-02-02 | 状态: 规划完成，待实施*
