# Phase 6: 测试与文档 实施计划

> **前置条件**: Phase 1–5 已完成（或 Phase 4/5 部分收尾可与 Phase 6 并行）。  
> **目标**: 全面测试与文档完善，达到可发布质量。

**依据文档:**
- `docs/LOOM_AGENT_0.5.0_RESEARCH_REPORT.md` §5.6 Phase 6
- `docs/plans/REMAINING_UPDATES.md` 四、后续阶段

**Tech Stack:** Python 3.10+, pytest, coverage

---

## 一、Phase 6 完成度标准（总览）

Phase 6 视为完成当且仅当下表所有「完成标准」均满足，且「验收方式」通过。

| 维度 | 完成标准 | 验收方式 |
|------|----------|----------|
| **集成测试** | 关键路径有集成测试（Agent 创建、工具执行、委派、记忆、技能激活等） | 存在对应 `tests/integration/` 用例且 `pytest tests/integration/` 通过 |
| **端到端测试** | 至少 1 条可选的 E2E 场景（真实或 mock LLM）覆盖「用户输入 → Agent 执行 → 结果」 | 存在 E2E 用例或标记，文档说明如何运行 |
| **覆盖率** | 核心模块（agent、memory、tools、skills、protocol）覆盖率 ≥ 80% | `pytest tests/ --cov=loom --cov-report=term-missing` 达标或豁免项已记录 |
| **API 文档** | 公开 API（Agent.create、run、execute_task、主要参数与配置）有稳定文档 | `docs/usage/api-reference.md` 等与代码一致，无过期示例 |
| **迁移指南** | v0.4 → v0.5 迁移指南完整且可被用户发现 | `docs/usage/migration-v0.5.md` 存在；README 或 docs 首页有入口链接 |
| **最佳实践** | 至少一份「推荐用法」或「最佳实践」说明（可选为 README 小节或独立文档） | 文档存在且与当前 API 一致 |
| **示例** | 所有示例使用当前推荐 API（如 Agent.create），且可运行 | `examples/` 下示例无 LoomApp/旧 API；`pytest` 或手顺可验证 |

---

## 二、任务与完成度细则

### Task 1: 集成测试

| 完成度项 | 标准 | 检查方法 |
|----------|------|----------|
| 1.1 Agent 创建与运行 | 覆盖 Agent.create、builder、run / execute_task | `tests/integration/` 或 `tests/unit/test_agent/` 中存在并通过 |
| 1.2 工具执行 | 覆盖工具注册、调用、结果回传 | 有 test_agent_tool_execution 或等价用例 |
| 1.3 委派 | 覆盖 delegate_task / _execute_delegate_task 或等价委派路径 | 有 test_form3_delegation、test_fractal_real_api 等 |
| 1.4 记忆 | 覆盖 MemoryManager / L1–L4 或任务记忆的关键路径 | 有 test_memory_integration、test_task_based_memory 等 |
| 1.5 技能激活 | 覆盖 SkillActivator、技能加载、编译工具或节点 | 有 test_skill_activation_forms 或等价 |

**完成标准**: 上述 1.1–1.5 均有对应用例且 `pytest tests/integration/` 通过。

---

### Task 2: 端到端测试

| 完成度项 | 标准 | 检查方法 |
|----------|------|----------|
| 2.1 E2E 场景 | 至少 1 个「输入 → 执行 → 输出」完整流程 | 如 test_e2e_real_api 或带 `@pytest.mark.e2e` 的用例 |
| 2.2 可运行性 | 文档或 pytest 标记说明如何运行 E2E（含需 API key 时的说明） | README 或 tests/README 或 pytest.ini 中有说明 |

**完成标准**: 存在 E2E 用例且文档/标记明确；若依赖外部服务，说明如何跳过或 mock。

---

### Task 3: 覆盖率与质量

| 完成度项 | 标准 | 检查方法 |
|----------|------|----------|
| 3.1 核心模块覆盖率 | `loom/agent`、`loom/memory`、`loom/tools`、`loom/skills`、`loom/protocol` 等核心包覆盖率 ≥ 80% | `pytest tests/ --cov=loom --cov-report=term-missing` 查看；可设 CI 阈值 |
| 3.2 豁免策略 | 若个别文件/目录不追求 80%，在配置或文档中列出豁免理由 | `pyproject.toml` / `.coveragerc` 或 `docs/plans/` 中记录 |
| 3.3 无严重回归 | 全量测试通过，无新增 flaky 用例 | `pytest tests/ -v` 稳定通过 |

**完成标准**: 覆盖率达标或豁免已记录；全量测试稳定通过。

---

### Task 4: API 文档

| 完成度项 | 标准 | 检查方法 |
|----------|------|----------|
| 4.1 入口与结构 | 有 api-reference 或等价文档，包含 Agent、配置、主要模块入口 | `docs/usage/api-reference.md` 存在且可读 |
| 4.2 Agent.create / run | 参数、返回值、示例与当前代码一致 | 文档中无 LoomApp/app.create_agent；有 Agent.create 示例 |
| 4.3 配置与能力 | AgentConfig、capabilities、skills、tools、sandbox 等与实现一致 | 文档与 `loom/agent/core.py`、`loom/config/` 对齐 |
| 4.4 过期内容 | 无已删除 API（如 LoomApp、RouterOrchestrator）的推荐用法 | grep 检查文档中无过期推荐 |

**完成标准**: 公开 API 有文档且与代码一致；无过期或错误示例。

---

### Task 5: 迁移指南

| 完成度项 | 标准 | 检查方法 |
|----------|------|----------|
| 5.1 文档存在 | 有 v0.4 → v0.5 迁移说明 | `docs/usage/migration-v0.5.md` 存在 |
| 5.2 内容完整 | 覆盖主要破坏性变更（LoomApp 移除、Agent.create、配置方式、工具/技能等） | 人工审阅迁移指南条目 |
| 5.3 可发现性 | README 或 docs 首页有「迁移」「升级」或「Migration」链接 | grep 或手顺确认入口 |

**完成标准**: 迁移指南完整且从主文档可链入。

---

### Task 6: 最佳实践（可选）

| 完成度项 | 标准 | 检查方法 |
|----------|------|----------|
| 6.1 推荐用法 | 至少一份「推荐用法」或「最佳实践」（可为 README 小节或独立文档） | 内容存在且与当前 API 一致 |
| 6.2 反例与注意 | 若有，列出常见反模式或注意事项 | 可选 |

**完成标准**: 有即可；无则 Phase 6 仍可标记完成，但建议补上。

---

### Task 7: 示例更新

| 完成度项 | 标准 | 检查方法 |
|----------|------|----------|
| 7.1 无旧 API | 示例中无 LoomApp、app.create_agent、from loom.api.models 等 | `grep -r "LoomApp\|app\.create_agent" examples/` 无推荐用法 |
| 7.2 使用推荐 API | 使用 Agent.create 或 Agent.builder().build() 等当前推荐方式 | 审阅 examples/ 入口文件 |
| 7.3 可运行 | 至少一个示例可通过复制粘贴或简短说明运行 | README 或 examples/ 内说明运行方式 |

**完成标准**: 所有示例符合当前 API；至少一个示例有明确运行说明。

---

## 三、Phase 6 完成度汇总表

在实施过程中可用下表自检（每项打勾表示达标）：

```
[ ] Task 1  集成测试：1.1–1.5 均有用例且 integration 通过
[ ] Task 2  端到端：至少 1 个 E2E 场景 + 运行说明
[ ] Task 3  覆盖率：核心 ≥80% 或豁免已记录；全量通过
[ ] Task 4  API 文档：入口存在、与代码一致、无过期推荐
[ ] Task 5  迁移指南：文档存在、内容完整、有入口链接
[ ] Task 6  最佳实践：有推荐用法文档（可选）
[ ] Task 7  示例：无旧 API、使用推荐 API、可运行
```

**Phase 6 完成**: Task 1–5 与 Task 7 全部勾选；Task 6 可选，建议勾选。

---

## 四、验收命令建议

```bash
# 全量测试
pytest tests/ -v --tb=short

# 集成测试
pytest tests/integration/ -v --tb=short

# 覆盖率（检查是否 ≥80%）
pytest tests/ --cov=loom --cov-report=term-missing --cov-fail-under=80

# 文档中无过期 API 推荐（应无输出或仅预期遗留说明）
grep -r "LoomApp\|app\.create_agent\|RouterOrchestrator" docs/ loom/api/README.md --include="*.md"
```

---

## 五、与其它阶段的关系

- **Phase 5 收尾**: 若 Phase 5 文档/CHANGELOG 未收尾，可在 Phase 6 的「文档」任务中一并完成。
- **Phase 4（命名）**: 若在 Phase 6 之后实施 Phase 4，API 文档需在 Phase 4 后再做一次同步更新。

---

*创建日期: 2026-02-02 | 状态: 规划完成，待实施*
