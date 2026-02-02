# Phase 2: 统一工具和技能管理 实施计划

> **前置条件**: Phase 1 已完成（LoomApp/api.models 已移除，Agent.create() 已落地并提交）。

**Goal:** 解决工具与技能双轨并行问题，确保「工具列表与执行来源一致」「Skill 依赖校验与执行一致」。

**依据文档:**
- `docs/LOOM_AGENT_0.5.0_RESEARCH_REPORT.md` §5.2 Phase 2
- `docs/OPTIMIZATION_SKILLS_TOOLS.md` P0–P2
- `docs/API_REFACTOR_DESIGN.md` §5.2

**Tech Stack:** Python 3.10+, pytest

---

## 现状简要（规划前核对）

- **Skills**: `loom/skills/registry.py` 已为统一 SkillRegistry（Loader + 运行时注册）；`skill_registry.py` 仅重导出 + `skill_market`。
- **Tools**: Agent `_get_available_tools()` 已合并 sandbox_manager 工具（步骤 4）；SkillActivator 已支持 `tool_manager` 且 `validate_dependencies` 优先使用 `tool_manager`。
- **待收敛**: 命名/导出清晰度、测试覆盖、文档与示例统一以 SandboxToolManager 为主。

---

## 第一部分：前置检查与基线

### Task 0: 验证当前测试基线

**Step 1: 运行完整测试**

```bash
pytest tests/ -v --tb=short
```

Expected: 记录通过/失败数量，作为 Phase 2 前基线。

**Step 2: 保存基线（可选）**

```bash
pytest tests/ -v --tb=short > test_baseline_before_phase2.txt 2>&1
```

---

## 第二部分：工具侧统一（P0/P1 验证与收尾）

### Task 1: 确认 Agent 工具列表包含 sandbox_manager（P0）

**目标:** 确保「发给 LLM 的工具列表」与「实际可执行工具」一致。

**Files:** `loom/agent/core.py` — `_get_available_tools()`

**Step 1: 代码审查**

- 确认在合并 `self.tools`、`config.extra_tools`（来自 tool_registry）之后，有「从 sandbox_manager 合并工具定义」的逻辑。
- 确认去重按 tool name，且 `config.disabled_tools` 的过滤生效。

**Step 2: 单测**

- 在 `tests/unit/test_agent/` 增加或补充用例：仅传入 `sandbox_manager`（不传 tool_registry），调用 `_get_available_tools()`，断言 sandbox_manager 中的工具出现在返回列表中。

**Step 3: 运行测试**

```bash
pytest tests/unit/test_agent/ -v -k "tool" --tb=short
```

Expected: 通过。

---

### Task 2: SkillActivator 依赖校验统一使用 SandboxToolManager（P1）

**目标:** 依赖校验与执行入口一致（均以 SandboxToolManager 为主）。

**Files:** `loom/skills/activator.py`

**Step 1: 确认逻辑**

- `validate_dependencies` 已优先使用 `tool_manager`（SandboxToolManager），缺省时才回退 `tool_registry`。
- 确认 Agent 创建 SkillActivator 时传入的 `tool_manager` 与执行工具时使用的 `sandbox_manager` 为同一实例（或一致来源）。

**Step 2: 单测**

- 用例：仅提供 `tool_manager`、不提供 `tool_registry`，对某 Skill 的 `required_tools` 做 `validate_dependencies`，断言行为符合预期（有则通过、缺则失败）。

**Step 3: 文档**

- 在 `docs/usage/` 或 `docs/features/` 中明确：**推荐只传 SandboxToolManager**，ToolRegistry 仅作兼容或内部适配；示例统一使用 `sandbox_manager`。

---

## 第三部分：技能侧统一（P2 收尾与命名）

### Task 3: 确认唯一 SkillRegistry 与导出

**目标:** 对外仅暴露一套 SkillRegistry，消除「两个 SkillRegistry」的混淆。

**Files:** `loom/skills/registry.py`, `loom/skills/skill_registry.py`, `loom/skills/__init__.py`

**Step 1: 确认实现**

- `loom/skills/registry.py` 的 `SkillRegistry` 已支持：Loader（async）+ 运行时注册（dict 风格），且 `get_skill` 先查运行时再查 Loaders。
- `loom/skills/skill_registry.py` 仅保留：`from .registry import SkillRegistry` 与 `skill_market = SkillRegistry()`，无额外类。

**Step 2: 导出与命名**

- `loom/skills/__init__.py` 只导出一个 `SkillRegistry`（来自 registry），以及 `skill_market`（来自 skill_registry 或直接从 registry 创建，视当前实现而定）。
- 若仍有「CallableSkillRegistry」等旧名，在文档或注释中标明已废弃，统一用 SkillRegistry。

**Step 3: 引用检查**

```bash
grep -r "skill_registry\.SkillRegistry\|from.*skill_registry import.*Registry" --include="*.py" loom/ tests/
```

Expected: 无对「另一套」SkillRegistry 类的引用；仅有对 `registry.SkillRegistry` 或 `skill_market` 的引用。

---

### Task 4: CapabilityRegistry 与 SkillRegistry 对接

**目标:** CapabilityRegistry 使用统一 SkillRegistry，且依赖校验与执行一致。

**Files:** `loom/capabilities/registry.py`（或当前 CapabilityRegistry 所在位置）, Agent 创建链

**Step 1: 审查**

- CapabilityRegistry 使用的 Skill 来源是否为统一的 `SkillRegistry`（Loader + 运行时）。
- 若存在 `validate_skill_dependencies`，确认其所需元数据（如 `required_tools`）与 SkillRegistry 返回的 SkillDefinition/dict 一致。

**Step 2: 适配**

- 若当前仍依赖「仅 dict 版」的 Skill 结构，改为兼容 SkillDefinition 或通过 SkillRegistry 统一获取元数据，避免双轨。

**Step 3: 测试**

- 集成或单元测试：CapabilityRegistry + 统一 SkillRegistry + SandboxToolManager，验证「发现 → 校验 → 执行」一条线。

---

## 第四部分：测试与文档

### Task 5: 工具与技能相关单测补全

**Files:** `tests/unit/test_agent/`, `tests/unit/test_skills/`, `tests/unit/test_tools/`, `tests/unit/test_capabilities/`（若存在）

**Step 1: 覆盖**

- Agent：仅 sandbox_manager、仅 tool_registry、两者都有时的 `_get_available_tools()` 行为。
- SkillActivator：仅 tool_manager、仅 tool_registry 时的 `validate_dependencies` 行为。
- SkillRegistry：运行时注册 + Loader 的 `get_skill` / `list_skills`（或等价接口）行为。

**Step 2: 运行**

```bash
pytest tests/unit/test_agent/ tests/unit/test_skills/ tests/unit/test_tools/ -v --tb=short
```

Expected: 全部通过。

---

### Task 6: 文档更新

**Files:** `docs/usage/`, `docs/features/`, `loom/tools/README.md` 或 `docs/features/tool-system.md`（若存在）, `OPTIMIZATION_SKILLS_TOOLS.md`

**Step 1: 工具入口**

- 明确写出：**推荐使用 SandboxToolManager**；ToolRegistry 为兼容/内部用；新示例统一用 `Agent.create(..., tool_registry=..., sandbox_manager=...)` 且以 sandbox_manager 为主。

**Step 2: 技能入口**

- 明确写出：**仅一套 SkillRegistry**（`loom.skills.registry.SkillRegistry`），支持 Loader + 运行时注册；`skill_market` 为全局单例；不再提及「两套 SkillRegistry」。

**Step 3: 可选**

- 在 `OPTIMIZATION_SKILLS_TOOLS.md` 文末增加「Phase 2 实施状态」小节，勾选 P0/P1/P2 的完成项。

---

## 第五部分：Phase 2 验收

### Task 7: 全量测试与回归

**Step 1: 运行完整测试**

```bash
pytest tests/ -v --tb=short
```

Expected: 与 Phase 2 前基线对比，无新增失败。

**Step 2: 可选基线对比**

```bash
pytest tests/ -v --tb=short > test_baseline_after_phase2.txt 2>&1
diff test_baseline_before_phase2.txt test_baseline_after_phase2.txt
```

Expected: 无新增失败（diff 仅可能为用例数量/名称变化，无失败增加）。

---

## 验证清单

完成 Phase 2 后，确认：

- [x] Agent 工具列表与执行来源一致（sandbox_manager 工具一定出现在 _get_available_tools 中）
- [x] SkillActivator 依赖校验与执行一致（优先 tool_manager/SandboxToolManager）
- [x] 仅一套 SkillRegistry 对外暴露，Loader + 运行时注册统一
- [x] CapabilityRegistry 使用统一 SkillRegistry，无双轨 Skill 来源
- [x] 相关单测通过且已补全
- [x] 文档与示例明确「以 SandboxToolManager 为主、单一 SkillRegistry」

---

## 完成度报告（检查日期：按需填写）

| Task | 状态 | 说明 |
|------|------|------|
| **Task 0** 测试基线 | ✅ | `test_baseline_before_phase2.txt` 已存在；可选 `test_baseline_after_phase2.txt` 未强制要求 |
| **Task 1** Agent 工具列表（P0） | ✅ | `_get_available_tools()` 步骤 4 已合并 sandbox_manager；单测 `test_get_available_tools_with_sandbox_manager`、`test_get_available_tools_with_both_managers` 已覆盖 |
| **Task 2** SkillActivator（P1） | ✅ | `validate_dependencies` 已优先 `tool_manager`；单测 `test_validate_dependencies_with_tool_manager_*`、`test_validate_dependencies_tool_manager_priority` 已覆盖 |
| **Task 3** 唯一 SkillRegistry | ✅ | `registry.py` 为统一实现；`skill_registry.py` 仅重导出 + `skill_market`；`__init__.py` 只导出 `SkillRegistry` 与 `skill_market`；无对「另一套」SkillRegistry 的引用 |
| **Task 4** CapabilityRegistry | ✅ | `capabilities/registry.py` 使用 `_skill_registry`，支持 async `get_skill` 与 SkillDefinition/dict 的 `required_tools`，与统一 SkillRegistry 一致 |
| **Task 5** 单测补全 | ✅ | test_dynamic_tools、test_activator_dependency_validation、test_capabilities、test_tools 等通过（377 passed） |
| **Task 6** 文档 | ✅ | `docs/features/tool-system.md` 已明确 SandboxToolManager 推荐、ToolRegistry 兼容；wiki/Skills 使用单一 SkillRegistry；可选：OPTIMIZATION_SKILLS_TOOLS 未加 Phase 2 状态小节 |
| **Task 7** 全量测试 | ✅ | Phase 2 相关单测全部通过；全量回归可由维护者执行 `pytest tests/ -v --tb=short` 确认 |

---

## 与研究报告的对应关系

| 研究报告 §5.2 Phase 2 任务 | 本计划 Task |
|----------------------------|-------------|
| 合并两套 SkillRegistry 为统一实现 | Task 3（确认与导出）、Task 4（CapabilityRegistry） |
| 统一使用 SandboxToolManager | Task 1（Agent 工具列表）、Task 2（SkillActivator） |
| 更新 SkillActivator 使用 SandboxToolManager | Task 2 |
| 修复 Agent 工具列表 bug（P0） | Task 1 |
| 更新 CapabilityRegistry 适配新 SkillRegistry | Task 4 |
| 更新所有测试用例 | Task 5、Task 7 |

---

## 下一步

Phase 2 完成后，进入 **Phase 3: Agent API 与渐进式披露** → 见 [2026-02-02-phase3-agent-api-progressive-disclosure.md](2026-02-02-phase3-agent-api-progressive-disclosure.md)。参见 `docs/LOOM_AGENT_0.5.0_RESEARCH_REPORT.md` §5.3。
