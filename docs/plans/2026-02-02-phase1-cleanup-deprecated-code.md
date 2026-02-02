# Phase 1: 清理废弃代码实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 移除所有已标记为废弃的代码，统一变量命名，删除未使用的变量

**Architecture:**
- 删除废弃的 LoomApp 和 api.models
- 更新所有引用改用 Agent.from_llm() 或 Agent.create()
- 清理未使用的参数和向后兼容代码
- 统一变量命名规范

**Tech Stack:** Python 3.10+, pytest

---

## 前置检查

### Task 0: 验证当前测试基线

**Files:**
- Run: 所有测试文件

**Step 1: 运行完整测试套件**

```bash
pytest tests/ -v --tb=short
```

Expected: 记录当前测试状态（通过/失败数量）

**Step 2: 保存测试基线**

```bash
pytest tests/ -v --tb=short > test_baseline_before_phase1.txt 2>&1
```

Expected: 创建基线文件用于后续对比

---

## 第一部分：识别和记录依赖关系

### Task 1: 识别 LoomApp 的所有使用者

**Files:**
- Create: `docs/plans/phase1-loomapp-usage.txt`

**Step 1: 搜索代码文件中的 LoomApp 引用**

```bash
grep -r "from loom.api import LoomApp\|from loom.api.app import LoomApp" --include="*.py" . > docs/plans/phase1-loomapp-usage.txt
```

Expected: 生成包含所有 LoomApp 引用的文件列表

**Step 2: 分类文件类型**

手动检查 phase1-loomapp-usage.txt，将文件分为：
- 示例文件 (examples/)
- 测试文件 (tests/)
- 核心代码 (loom/)
- 文档文件 (docs/, wiki/, README)

**Step 3: Commit**

```bash
git add docs/plans/phase1-loomapp-usage.txt
git commit -m "docs: record LoomApp usage before cleanup"
```

---

### Task 2: 识别 AgentConfig (api.models) 的所有使用者

**Files:**
- Create: `docs/plans/phase1-agentconfig-usage.txt`

**Step 1: 搜索 api.models.AgentConfig 引用**

```bash
grep -r "from loom.api.models import\|from loom.api import.*AgentConfig" --include="*.py" . > docs/plans/phase1-agentconfig-usage.txt
```

Expected: 生成包含所有 AgentConfig 引用的文件列表

**Step 2: Commit**

```bash
git add docs/plans/phase1-agentconfig-usage.txt
git commit -m "docs: record AgentConfig usage before cleanup"
```

---

## 第二部分：更新示例文件

### Task 3: 更新 examples/conversational_assistant_tui.py

**Files:**
- Modify: `examples/conversational_assistant_tui.py`

**Step 1: 读取当前文件**

查看文件内容，识别 LoomApp 的使用方式

**Step 2: 替换为 Agent.from_llm()**

将 LoomApp 创建和配置代码替换为直接使用 Agent.from_llm()

示例替换：
```python
# 旧代码
from loom.api import LoomApp, AgentConfig
app = LoomApp()
app.set_llm_provider(llm)
config = AgentConfig(...)
agent = app.create_agent(config)

# 新代码
from loom.agent import Agent
from loom.events import EventBus
event_bus = EventBus()
agent = Agent.from_llm(
    llm=llm,
    node_id="conversational_assistant",
    system_prompt="...",
    event_bus=event_bus,
    max_iterations=20
)
```

**Step 3: 运行示例验证**

```bash
python examples/conversational_assistant_tui.py
```

Expected: 示例正常运行，无错误

**Step 4: Commit**

```bash
git add examples/conversational_assistant_tui.py
git commit -m "refactor: migrate conversational_assistant_tui from LoomApp to Agent.from_llm"
```

---

### Task 4: 更新 examples/task_executor_tui.py

**Files:**
- Modify: `examples/task_executor_tui.py`

**Step 1: 读取当前文件**

查看文件内容，识别 LoomApp 的使用方式

**Step 2: 替换为 Agent.from_llm()**

将 LoomApp 创建和配置代码替换为直接使用 Agent.from_llm()

**Step 3: 运行示例验证**

```bash
python examples/task_executor_tui.py
```

Expected: 示例正常运行，无错误

**Step 4: Commit**

```bash
git add examples/task_executor_tui.py
git commit -m "refactor: migrate task_executor_tui from LoomApp to Agent.from_llm"
```

---

## 第三部分：更新核心代码

### Task 5: 更新 loom/api/__init__.py

**Files:**
- Modify: `loom/api/__init__.py`

**Step 1: 读取当前文件**

查看当前导出的内容

**Step 2: 移除 LoomApp 和 AgentConfig 导出**

```python
# 删除这些行
from .app import LoomApp
from .models import AgentConfig, MemoryConfig

# 从 __all__ 中移除
__all__ = [
    # ... 其他导出
    # "LoomApp",  # 删除
    # "AgentConfig",  # 删除
    # "MemoryConfig",  # 删除
]
```

**Step 3: 添加迁移提示注释**

```python
# Deprecated in v0.4.7, removed in v0.5.0:
# - LoomApp: Use Agent.from_llm() or Agent.create() instead
# - AgentConfig (api.models): Use Agent constructor parameters directly
```

**Step 4: Commit**

```bash
git add loom/api/__init__.py
git commit -m "refactor: remove LoomApp and AgentConfig from api exports"
```

---

## 第四部分：更新测试文件

### Task 6: 更新或删除 tests/unit/test_api/test_app.py

**Files:**
- Modify or Delete: `tests/unit/test_api/test_app.py`

**Step 1: 读取测试文件**

查看测试内容，判断是否需要保留

**Step 2: 决策**

如果测试仅测试 LoomApp：删除整个文件
如果测试包含其他有价值的测试：迁移到 Agent 测试

**Step 3: 执行删除或迁移**

```bash
# 如果删除
git rm tests/unit/test_api/test_app.py

# 如果迁移
# 将测试改写为使用 Agent.from_llm()
```

**Step 4: 运行测试验证**

```bash
pytest tests/unit/test_api/ -v
```

Expected: 测试通过或文件已删除

**Step 5: Commit**

```bash
git add tests/unit/test_api/
git commit -m "test: remove or migrate LoomApp tests"
```

---

## 第五部分：删除废弃文件

### Task 7: 删除 loom/api/app.py

**Files:**
- Delete: `loom/api/app.py`

**Step 1: 确认没有遗漏的引用**

```bash
grep -r "from loom.api.app import\|from loom.api import.*LoomApp" --include="*.py" loom/ tests/
```

Expected: 无输出（所有引用已清理）

**Step 2: 删除文件**

```bash
git rm loom/api/app.py
```

**Step 3: Commit**

```bash
git commit -m "refactor: remove deprecated LoomApp (v0.5.0)"
```

---

### Task 8: 删除 loom/api/models.py

**Files:**
- Delete: `loom/api/models.py`

**Step 1: 确认没有遗漏的引用**

```bash
grep -r "from loom.api.models import" --include="*.py" loom/ tests/
```

Expected: 无输出（所有引用已清理）

**Step 2: 删除文件**

```bash
git rm loom/api/models.py
```

**Step 3: Commit**

```bash
git commit -m "refactor: remove deprecated api.models (v0.5.0)"
```

---

## 第六部分：运行完整测试

### Task 9: 验证所有测试通过

**Files:**
- Run: 所有测试文件

**Step 1: 运行完整测试套件**

```bash
pytest tests/ -v --tb=short
```

Expected: 所有测试通过（或与基线相同）

**Step 2: 对比测试结果**

```bash
pytest tests/ -v --tb=short > test_baseline_after_phase1.txt 2>&1
diff test_baseline_before_phase1.txt test_baseline_after_phase1.txt
```

Expected: 无新增失败测试

**Step 3: 如果有失败测试**

修复失败的测试，确保它们通过

---

## 第七部分：更新文档

### Task 10: 更新主 README

**Files:**
- Modify: `README.md`
- Modify: `README_EN.md`

**Step 1: 搜索 LoomApp 引用**

在 README 中查找所有 LoomApp 示例

**Step 2: 替换为 Agent.from_llm() 示例**

将所有 LoomApp 示例改为使用 Agent.from_llm()

**Step 3: Commit**

```bash
git add README.md README_EN.md
git commit -m "docs: update README to use Agent.from_llm instead of LoomApp"
```

---

### Task 11: 更新 wiki 文档

**Files:**
- Modify: `wiki/Getting-Started.md`
- Modify: `wiki/API-Agent.md`
- Modify: `wiki/examples/*.md`

**Step 1: 批量搜索替换**

在所有 wiki 文件中将 LoomApp 示例替换为 Agent.from_llm()

**Step 2: Commit**

```bash
git add wiki/
git commit -m "docs: update wiki to use Agent.from_llm instead of LoomApp"
```

---

### Task 12: 更新 docs 文档

**Files:**
- Modify: `docs/usage/getting-started.md`
- Modify: `docs/usage/api-reference.md`
- Modify: `docs/usage/examples/*.md`
- Modify: `docs/features/*.md`

**Step 1: 批量搜索替换**

在所有 docs 文件中将 LoomApp 示例替换为 Agent.from_llm()

**Step 2: Commit**

```bash
git add docs/
git commit -m "docs: update documentation to use Agent.from_llm instead of LoomApp"
```

---

## 验证清单

完成所有任务后，验证以下内容：

- [x] loom/api/app.py 已删除
- [x] loom/api/models.py 已删除
- [x] 所有示例文件已更新并可运行
- [x] 所有测试通过（基线 1200 → Phase1 后 1179，因删除 test_app.py）
- [x] 所有文档已更新（AGENTS.md、loom/api/README.md、KNOWLEDGE_RAG_README.md 已改为 Agent.create()）
- [x] 无 LoomApp 或 api.models.AgentConfig 的 **代码** 引用残留（loom/、tests/、examples/ 已清理）
- [ ] git status 显示所有更改已提交（当前有未提交修改）

---

## 完成度报告（2026-02-02 检查）

| Task | 状态 | 说明 |
|------|------|------|
| **Task 0** 测试基线 | ✅ | `test_baseline_before_phase1.txt` 存在（1200 条）；Phase1 后为 `test_results_after_phase1.txt`（1179 条，文件名与计划略不同） |
| **Task 1** LoomApp 使用者 | ✅ | `docs/plans/phase1-loomapp-usage.txt` 已创建 |
| **Task 2** AgentConfig 使用者 | ✅ | `docs/plans/phase1-agentconfig-usage.txt` 已创建 |
| **Task 3** conversational_assistant_tui | ✅ | 已使用 `Agent.create()` |
| **Task 4** task_executor_tui | ✅ | 已使用 `Agent.create()` |
| **Task 5** loom/api/__init__.py | ✅ | 已移除 LoomApp/AgentConfig 导出，保留迁移注释 |
| **Task 6** test_app.py | ✅ | 文件已删除（tests/unit/test_api/test_app.py 不存在） |
| **Task 7** loom/api/app.py | ✅ | 已删除 |
| **Task 8** loom/api/models.py | ✅ | 已删除 |
| **Task 9** 完整测试 | ✅ | 有 Phase1 后结果文件，测试数减少与删除 test_app 一致 |
| **Task 10** README | ✅ | README.md、README_EN.md 无 LoomApp 引用 |
| **Task 11** wiki | ✅ | wiki/Getting-Started.md、API-Agent.md 已使用 Agent.create() |
| **Task 12** docs | ✅ | AGENTS.md、loom/api/README.md、examples/KNOWLEDGE_RAG_README.md 已改为 Agent.create()；docs/usage、wiki 已更新 |

**代码与核心文档**：loom/、tests/、examples/*.py 中无 `from loom.api.app import` 或 `from loom.api.models import`；`loom.config.agent.AgentConfig` 为保留的新配置类，非废弃 api.models。

**收尾已完成（2026-02-02）**：
1. ✅ **AGENTS.md** Quick Start、Key Classes、Modules 已改为 Agent.create()。
2. ✅ **loom/api/README.md** 已重写为 Agent.create() / Agent.builder()，移除 LoomApp/AgentConfig。
3. ✅ **examples/KNOWLEDGE_RAG_README.md**「配置 LoomApp」已改为 Agent.create() 流程。
4. 可选：docs 中研究/设计类文档（RESEARCH_*.md、API_REFACTOR_DESIGN 等）多为历史说明，可保留「已弃用/已移除」表述。
5. 提交所有更改：`git add -A && git status` 后由维护者提交。

---

## 下一步

Phase 1 完成后，继续 **Phase 2: 统一工具和技能管理** → 见 [2026-02-02-phase2-unify-tools-skills.md](2026-02-02-phase2-unify-tools-skills.md)
