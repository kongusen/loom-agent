# Phase 3: Agent API 与渐进式披露 实施计划

> **前置条件**: Phase 1、Phase 2 已完成（Agent.create() 已落地，工具与技能已统一）。

**Goal:** 完成「渐进式披露」：简单用法最少参数即可运行，高级用法支持显式传入组件；可选集成 CapabilityRegistry；补齐迁移指南与示例。

**依据文档:**
- `docs/LOOM_AGENT_0.5.0_RESEARCH_REPORT.md` §5.3 Phase 3
- `docs/API_REFACTOR_DESIGN.md` §5.3、§6 迁移指南
- `docs/OPTIMIZATION_SKILLS_TOOLS.md` 五、API 重构设计决策

**Tech Stack:** Python 3.10+, pytest

---

## 现状简要（规划前核对）

- **Agent.create()**：已实现（Phase 1），支持 llm、system_prompt、tools、node_id、event_bus、knowledge_base、max_context_tokens、max_iterations、**kwargs。
- **Agent.builder()**：已实现，链式 .with_*().build()。
- **默认组件**：未传 event_bus 时当前为 None，观测/集体记忆会跳过；未传 skill_registry/tool_registry/sandbox_manager 时均为 None。
- **简单配置**：Agent.create() 未支持 skills= 参数；未支持 capabilities= 参数；传入 tools= 时仅作为 self.tools，未自动创建 SandboxToolManager。
- **迁移指南**：文档中散布迁移示例，无单独的 v0.4.x → v0.5.0 迁移文档。

---

## 第一部分：前置检查与基线

### Task 0: 验证当前测试基线

**Step 1: 运行完整测试**

```bash
pytest tests/ -v --tb=short
```

Expected: 记录通过/失败数量，作为 Phase 3 前基线。

**Step 2: 保存基线（可选）**

```bash
pytest tests/ -v --tb=short > test_baseline_before_phase3.txt 2>&1
```

---

## 第二部分：默认组件（渐进式披露 - 简单用法）

### Task 1: 未传 event_bus 时自动创建 EventBus

**目标:** 简单用法 `Agent.create(llm, system_prompt="...")` 无需显式创建 EventBus，观测与集体记忆即可工作。

**Files:** `loom/agent/core.py` — `Agent.create()` 或 `Agent.__init__`

**Step 1: 实现**

- 在 `Agent.create()` 中：若 `event_bus is None`，则 `event_bus = EventBus()` 再传给 `cls(...)`。
- 或在 `Agent.__init__` 中：若 `event_bus is None`，则 `self.event_bus = EventBus()`（需确认 BaseNode 对 event_bus 的约定）。

**Step 2: 单测**

- 用例：不传 event_bus 创建 Agent，断言 `agent.event_bus is not None`，且可调用 publish/query_recent（或等价行为）。

**Step 3: 文档**

- 在 api-reference / getting-started 中注明：不传 event_bus 时框架会自动创建，多 Agent 需共享时请显式传入同一 EventBus。

---

### Task 2: Agent.create() 支持 skills= 参数（简单配置）

**目标:** 用户可写 `Agent.create(llm, system_prompt="...", skills=["python-dev", "testing"])`，内部启用对应 skills，无需手建 SkillRegistry/SkillActivator。

**Files:** `loom/agent/core.py` — `Agent.create()`, `Agent.__init__`（或 config）

**Step 1: 设计**

- 增加参数 `skills: list[str] | None = None`（skill_id 列表）。
- 若传入 skills：
  - 若无 skill_registry，可创建默认 SkillRegistry（如 `loom.skills.skill_market` 或 `SkillRegistry()`）并注册默认 Loader（可选）；
  - 将 skills 写入 config.enabled_skills（或等价），并传入 skill_registry。
- 若未传入 skills，保持现有行为（依赖 config.enabled_skills 或显式传入 skill_registry）。

**Step 2: 实现**

- 在 `Agent.create()` 中解析 skills，构造或复用 SkillRegistry，设置 config.enabled_skills，传给 `cls(...)`。

**Step 3: 单测**

- 用例：`Agent.create(llm, system_prompt="...", skills=["some-skill"])`，断言 agent.config.enabled_skills 含 "some-skill"，且 skill_registry 可用（若有默认 Loader 可断言 get_skill 不报错）。

**Step 4: 文档**

- 在 api-reference 中补充 Agent.create() 的 skills= 参数说明与示例。

---

## 第三部分：CapabilityRegistry 集成（高级用法）

### Task 3: Agent.create() 支持 capabilities= 参数

**目标:** 高级用法可传入已配置的 CapabilityRegistry，Agent 使用其 sandbox_manager、skill_registry、skill_activator，与「发现 → 校验 → 执行」一条线一致。

**Files:** `loom/agent/core.py` — `Agent.create()`；`loom/capabilities/registry.py`（若需暴露只读属性）

**Step 1: 设计**

- 增加参数 `capabilities: Any | None = None`（CapabilityRegistry 实例）。
- 若 `capabilities is not None`：
  - 从 capabilities 获取 tool_manager（sandbox_manager）、skill_registry、skill_activator。
  - CapabilityRegistry 需提供可读属性（如 .tool_manager / .skill_registry / .skill_activator），或在 registry 内增加 getter，避免 Agent 依赖私有 _tool_manager 等。

**Step 2: 实现**

- 在 `Agent.create()` 中：若传入 capabilities，则 `sandbox_manager = getattr(capabilities, "tool_manager", None) or getattr(capabilities, "_tool_manager", None)`，同理 skill_registry、skill_activator，再传给 `cls(...)`。
- 若 CapabilityRegistry 暂无公开属性，可在本 Phase 为其增加只读属性（如 `@property def tool_manager(self): return self._tool_manager`）。

**Step 3: 单测**

- 用例：构造 CapabilityRegistry(sandbox_manager=..., skill_registry=..., skill_activator=...)，`Agent.create(llm, capabilities=reg)`，断言 agent.sandbox_manager / agent.skill_registry / agent.skill_activator 与 reg 内一致。

**Step 4: 文档**

- 在 api-reference 与 OPTIMIZATION_SKILLS_TOOLS 中补充「高级用法：传入 CapabilityRegistry」示例。

---

## 第四部分：工具简单配置（可选）

### Task 4: 传入 tools= 且无 sandbox_manager 时的可选行为（可选）

**目标:** 简单用法仅传 `tools=[...]` 时，可选地内部创建 SandboxToolManager 并注册，使「发给 LLM 的工具列表」与「执行来源」一致。

**说明:** 当前行为是 tools= 仅作为 self.tools（LLM 格式），执行时若无 sandbox_manager 则依赖 tool_registry。若希望「只传 tools= 即可」，需在 Agent.create() 中：当 tools 非空且 sandbox_manager 为 None 时，创建 SandboxToolManager，将 tools 转为注册调用（或通过 create_sandbox_toolset 等现有工厂），再传入 Agent。本任务为可选，可在 Phase 3 仅做设计与文档，实现留待后续。

**Step 1: 设计**

- 约定：Agent.create(llm, tools=[...]) 且未传 sandbox_manager 时，是否自动创建 SandboxToolManager 并注册；若自动创建，workspace/sandbox 路径的默认值。

**Step 2: 文档**

- 在 api-reference 中说明：当前推荐显式传入 sandbox_manager 或 tool_registry；若未来支持「仅传 tools= 即自动创建 SandboxToolManager」，会在文档中注明。

---

## 第五部分：迁移指南与示例

### Task 5: 编写 v0.4.x → v0.5.0 迁移指南

**目标:** 提供一份集中文档，便于用户从 LoomApp/AgentConfig 迁移到 Agent.create()。

**Files:** 新建 `docs/usage/migration-v0.5.md` 或 `docs/MIGRATION_V05.md`

**Step 1: 内容结构**

- 概述：v0.5.0 移除 LoomApp、api.models.AgentConfig，推荐使用 Agent.create() / Agent.builder()。
- 快速对照：
  - 创建 Agent：LoomApp + AgentConfig → Agent.create(llm, ...)
  - 工具配置：app.register_tool / app.add_tools → Agent.create(..., tools=...) 或 sandbox_manager
  - 多 Agent 共享 EventBus：显式创建 EventBus() 并传入各 Agent.create(..., event_bus=bus)
- 常见场景：仅 LLM+prompt、带工具、带 Skill、多 Agent 协作。
- 破坏性变更列表：LoomApp、AgentConfig、api.models 移除；enable_tool_creation 等移除（若已做）。
- 链接：api-reference、getting-started、Phase 1 计划（可选）。

**Step 2: 编写与评审**

- 编写迁移文档，确保代码块可运行（或注明需替换 api_key 等）。
- 在 README 或 docs 首页增加「升级到 v0.5」链接。

---

### Task 6: 确认所有示例使用 Agent.create()

**目标:** 仓库内示例与文档中的 Agent 创建方式统一为 Agent.create() 或 Agent.builder()。

**Files:** `examples/*.py`, `docs/**/*.md`, `wiki/**/*.md`

**Step 1: 检查**

```bash
grep -r "LoomApp\|AgentConfig\|app\.create_agent\|from loom.api.models" --include="*.py" examples/
grep -r "LoomApp\|app\.create_agent" --include="*.md" docs/ wiki/ README.md
```

Expected: 无残留（或仅迁移文档中的「旧代码」示例）。

**Step 2: 修正**

- 若有残留，替换为 Agent.create() / Agent.builder()，并补充 event_bus 等必要参数（若已实现 Task 1，可不传 event_bus）。

---

## 第六部分：验收与文档收尾

### Task 7: 全量测试与文档更新

**Step 1: 运行完整测试**

```bash
pytest tests/ -v --tb=short
```

Expected: 与 Phase 3 前基线对比，无新增失败。

**Step 2: 文档索引**

- 在 docs/usage/ 或 docs/ 首页/目录中增加「迁移指南（v0.5）」入口。
- 检查 api-reference 中 Agent.create() 参数表与示例是否包含 event_bus 默认行为、skills=、capabilities=。

---

## 验证清单

完成 Phase 3 后，确认：

- [x] 未传 event_bus 时自动创建 EventBus，简单用法无需显式创建
- [x] Agent.create() 支持 skills= 参数，文档已更新（api-reference、migration-v0.5）
- [x] Agent.create() 支持 capabilities= 参数，CapabilityRegistry 可被 Agent 复用（CapabilityRegistry 已暴露 tool_manager/skill_registry/skill_activator 只读属性）
- [x] 迁移指南文档已编写（docs/usage/migration-v0.5.md）；可选：README 或 docs 首页增加「升级到 v0.5」链接
- [x] 所有示例与文档中 Agent 创建方式统一为 Agent.create() / Agent.builder()（examples/*.py 无 LoomApp 残留）
- [x] Phase 3 相关单测通过（test_agent_create.py 10 条全部通过）

---

## 完成度报告（检查日期：按需填写）

| Task | 状态 | 说明 |
|------|------|------|
| **Task 0** 测试基线 | ✅ | 可选基线文件 test_baseline_phase3.txt 存在 |
| **Task 1** 自动创建 EventBus | ✅ | core.py 395–397：event_bus is None 时 event_bus = EventBus()；test_agent_create.py TestAgentCreateEventBus 覆盖 |
| **Task 2** skills= 参数 | ✅ | core.py 335、409–420：skills= 使用 skill_market，config.enabled_skills=set(skills)；TestAgentCreateSkills 覆盖 |
| **Task 3** capabilities= 参数 | ✅ | core.py 336、399–406：从 CapabilityRegistry 提取 tool_manager/skill_registry/skill_activator；CapabilityRegistry 有 @property；TestAgentCreateCapabilities 覆盖 |
| **Task 4** tools= 自动 Sandbox（可选） | ⏭️ 未做 | 计划为可选，当前未实现；文档可注明推荐显式传入 sandbox_manager |
| **Task 5** 迁移指南 | ✅ | docs/usage/migration-v0.5.md 已编写（EventBus/skills/capabilities 对照与 FAQ）；可选：README 增加「升级到 v0.5」链接 |
| **Task 6** 示例统一 | ✅ | examples/*.py 无 LoomApp/app.create_agent 残留 |
| **Task 7** 全量测试与文档索引 | ✅ | test_agent_create.py 10 条通过；迁移指南可从 docs/usage/migration-v0.5.md 直接访问 |

---

## 与研究报告的对应关系

| 研究报告 §5.3 Phase 3 任务 | 本计划 Task |
|----------------------------|-------------|
| 实现 Agent.create() 类方法 | 已在 Phase 1 完成 |
| 实现自动创建默认组件的逻辑 | Task 1（EventBus）、Task 2（skills 默认 SkillRegistry，可选） |
| 实现工具和 Skill 的简单配置 | Task 2（skills=）、Task 4（tools= 可选） |
| 集成 CapabilityRegistry | Task 3 |
| 更新所有示例代码 | Task 6 |
| 编写迁移指南 | Task 5 |

---

## 下一步

Phase 3 完成后，进入 **Phase 4: 命名规范统一（驼峰命名法）** → 见 [2026-02-02-phase4-naming-camelcase.md](2026-02-02-phase4-naming-camelcase.md)；或 **Phase 5: LLM 自主决策优化**（参见 `docs/LOOM_AGENT_0.5.0_RESEARCH_REPORT.md` §5.4、§5.5）。  
待更新与收尾项见 [REMAINING_UPDATES.md](REMAINING_UPDATES.md)。
