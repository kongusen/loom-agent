# loom/skills 与 loom/tools 整体优化建议

基于对 `loom/skills`、`loom/tools`、`loom/capabilities` 及 Agent 集成的梳理，整理以下可落地的优化建议。

---

## 一、现状与问题概览

### 1. Skills 模块：两套「Skill」概念并存

| 维度 | `loom/skills/registry.py` | `loom/skills/skill_registry.py` |
|------|---------------------------|----------------------------------|
| **定位** | SKILL.md/DB 技能包（Loader + SkillDefinition） | 可调用工具型 Skill（类似 OpenAI function） |
| **API** | async：`get_skill`, `get_all_metadata`, `register_loader` | sync：`get_skill`, `list_skills`, `register_skill` |
| **返回** | `SkillDefinition` | `dict`（含 `_metadata`, `_handler`） |
| **使用者** | Agent core、集成测试（Loader 链） | LoomApp、CapabilityRegistry |

问题：

- 包内同时导出两个都叫「SkillRegistry」的类（`registry.SkillRegistry` 与 `skill_registry.SkillRegistry`），命名冲突、心智负担大。
- CapabilityRegistry 的 `validate_skill_dependencies` 只适配 dict 版（`_metadata.required_tools`），与 Loader 版 SkillDefinition 不兼容。
- Agent 期望 async + metadata（Loader 版），LoomApp 使用 sync + dict（skill_registry 版），两套入口难以统一到 CapabilityRegistry。

### 2. Tools 模块：双轨工具入口

| 维度 | `loom/tools/registry.py` (ToolRegistry) | `loom/tools/sandbox_manager.py` (SandboxToolManager) |
|------|------------------------------------------|------------------------------------------------------|
| **定位** | 同步工具注册表（func + MCP 定义） | 沙盒工具管理器（推荐主入口） |
| **API** | `register_function`, `get_definition`, `has` | `register_tool`, `execute_tool`, `list_tools` |
| **执行** | 无（只存定义与 callable） | 有（含 scope、沙盒、事件） |
| **使用者** | LoomApp、SkillActivator（依赖验证 `has()`）、Agent `extra_tools` | CapabilityRegistry、Agent 执行、toolset |

问题：

- SkillActivator 的 `validate_dependencies` 使用 `tool_registry.has(tool_name)`，而推荐用法是 SandboxToolManager，导致「依赖校验」与「实际执行」可能不一致。
- Agent 同时支持 `tool_registry` 与 `sandbox_manager`，工具列表来源分散（见下节）。

### 3. Agent 工具列表与执行来源不一致

- `_get_available_tools()` 当前只合并：
  1. `self.tools`
  2. `config.extra_tools` → 来自 **tool_registry**
- 注释写「已激活 Skills 绑定的工具（通过 sandbox_manager）」和「沙盒工具已经在 _get_available_tools() 中处理」，但**并未把 sandbox_manager 中的工具加入 LLM 工具列表**。
- 执行时：先走 context_tools，再走 **sandbox_manager**，最后才走 **tool_registry**。

结果：若用户只传 `sandbox_manager` 不传 `tool_registry`，这些工具可被执行，但**不会出现在发给 LLM 的 tool list 中**，属于逻辑 bug。

---

## 二、优化建议（按优先级）

### P0：修复 Agent 工具列表缺失 sandbox_manager 工具（必做）

**位置**：`loom/agent/core.py` 的 `_get_available_tools()`。

**建议**：在合并 `self.tools` 和 `config.extra_tools` 之后，增加「从 sandbox_manager 合并工具定义」的逻辑，并与现有去重（按 tool name）一致。

示例逻辑（保留你现有结构即可）：

```python
# 在 _get_available_tools() 中，步骤 2 或 3 后添加：
if self.sandbox_manager:
    for mcp_def in self.sandbox_manager.list_tools():
        name = mcp_def.name
        if name not in tool_names_seen:
            tool_names_seen.add(name)
            available.append({
                "type": "function",
                "function": {
                    "name": name,
                    "description": mcp_def.description,
                    "parameters": mcp_def.input_schema,
                },
            })
```

这样「发给 LLM 的工具列表」与「实际可执行工具」对齐，避免只传 sandbox_manager 时行为不一致。

---

### P1：统一「工具」入口，以 SandboxToolManager 为主

目标：新用法只认 SandboxToolManager；ToolRegistry 仅作兼容或内部适配。

建议：

1. **SkillActivator 依赖校验**  
   - 支持同时接受 `tool_registry` 与 `sandbox_manager`，或  
   - 仅接受一个「工具提供方」抽象（例如协议：`has(name)`, `list_tool_names()`）。  
   - 若传入的是 SandboxToolManager，用 `name in self.sandbox_manager` 或 `list_tool_names()` 实现 `has`，这样依赖校验与执行来源一致。

2. **Agent 构造**  
   - 文档与默认路径明确：**优先使用 sandbox_manager**；  
   - 当存在 sandbox_manager 时，从 sandbox_manager 拉取「基础工具列表」，tool_registry 仅用于 `config.extra_tools` 的补充（或逐步废弃 extra_tools 从 registry 拉取，改为从 sandbox_manager 注册后再通过 config 只做「启用/禁用」）。

3. **CapabilityRegistry**  
   - 已正确使用 SandboxToolManager 作为 `_tool_manager`，保持不变即可。

---

### P2：厘清并统一两套 Skill 概念

目标：消除「两个 SkillRegistry」的混淆，并让 CapabilityRegistry 能对接 Agent 实际使用的 Skill 来源。

可选方向（二选一或分阶段）：

**方案 A：保留两套，改名为不同概念**

- `loom/skills/registry.py` 的 Loader 体系：保留名 **SkillRegistry**，表示「技能包注册表」（SKILL.md/DB）。
- `loom/skills/skill_registry.py`：重命名为 **ToolLikeSkillRegistry** 或 **CallableSkillRegistry**，并在文档中明确是「可调用工具形态的 Skill（OpenAI function 风格）」。
- `loom/skills/__init__.py`：  
  - 导出：`SkillRegistry`（Loader 版）、`CallableSkillRegistry`（原 skill_registry）及 `skill_market`（若保留全局单例）。  
  - 在文档中说明两者适用场景与区别。

**方案 B：统一到一套抽象**

- 定义「Skill 提供方」协议：例如 `get_skill(id)`, `list_skill_ids()`, 可选 `get_skill_metadata(id)`。
- Loader 版 SkillRegistry 实现该协议（async）。
- 为 dict 版（现 skill_registry）写一个薄适配器，实现同一协议（sync 转 async 或仅用于 LoomApp 路径）。
- CapabilityRegistry 只依赖该协议，内部可同时支持「技能包」与「可调用 Skill」两种后端。

建议先做 **方案 A**（改名 + 文档），成本低且立刻减少混淆；方案 B 可作为后续重构。

---

### P3：CapabilityRegistry 与「按任务过滤」能力

- `find_relevant_capabilities` 中 Skill 侧目前是「返回所有 skill_ids」；注释有 TODO：按任务描述过滤。
- 若 Skill 侧采用 Loader 版 SkillRegistry，可直接复用 SkillActivator 的 `find_relevant_skills(task_description, metadata_list)`，只取「与任务相关的 skill_ids」，再与现有「全部 tools」或后续「按任务过滤的 tools」组合成 CapabilitySet。
- 这样 CapabilityRegistry 真正起到「按任务发现能力」的作用，而不是简单列举全部。

---

### P4：目录与命名清晰化

- **skills**  
  - `registry.py`：Loader + SkillDefinition 的「技能包注册表」。  
  - `skill_registry.py`：可调用 Skill 注册表；若采用方案 A，改名为 `callable_skill_registry.py` 或类似，并保持 `skill_market` 从该模块导出。  
  - 在 `README` 或 `docs` 中画一张「Skills 双轨示意图」：来源（DB/FS vs 代码注册）、谁用、何时用哪一套。

- **tools**  
  - 在 `loom/tools/__init__.py` 或文档中明确：  
    - **SandboxToolManager** = 推荐入口，负责注册、执行、沙盒、MCP。  
    - **ToolRegistry** = 旧版/兼容入口，仅在有 `extra_tools` 或 LoomApp 路径时使用。  
  - 新示例与文档统一用 `create_sandbox_toolset` + `SandboxToolManager`，避免再出现「只给 ToolRegistry 不给 SandboxToolManager」的用法。

---

## 三、建议实施顺序

1. **P0**：在 `_get_available_tools()` 中补全 sandbox_manager 工具列表（必做，修 bug）。  
2. **P1**：SkillActivator 支持用 SandboxToolManager 做依赖校验；文档明确「工具入口以 SandboxToolManager 为主」。  
3. **P2**：Skills 双轨改名与文档（方案 A），减少命名冲突。  
4. **P3**：CapabilityRegistry 接入「按任务过滤」的 Skill（可依赖 SkillActivator）。  
5. **P4**：目录/命名与文档的最终整理。

---

## 四、与「渐进式配置」的一致性

你之前讨论的 API 形态可以保持不变：

- 简单用法：`Agent.create(llm, tools=[...], skills=["python-dev"])` → 内部构造 CapabilityRegistry + SandboxToolManager（及可选 Loader 版 SkillRegistry），并正确合并 sandbox 工具到 LLM 工具列表。  
- 高级用法：传入已配置的 `CapabilityRegistry` 或 `sandbox_manager`。

在实现「简单用法」时，只要保证：

- 内部若创建了 SandboxToolManager，其工具一定会进入 `_get_available_tools()`（P0）；  
- 若使用 Loader 版 SkillRegistry，CapabilityRegistry 通过协议或适配器与之对接（P2/P3），  

则「工具/Skill 配置」与「发现、校验、执行」会在一条线上一致，便于后续再优化命名与目录结构。

---

## 五、API 重构设计决策（2026-02-02 更新）

基于对六大管理体系的深入研究和 API 设计讨论，确定以下重构方向：

### 5.1 核心设计原则

1. **驼峰命名法**：所有新 API 使用驼峰命名（camelCase），替代下划线命名
2. **显式传入全局组件**：用户显式创建和管理全局组件（EventBus 等）
3. **渐进式披露**：简单用法只需最少参数，高级用法支持深度定制
4. **不向后兼容**：彻底移除废弃代码，保持框架简洁

### 5.2 Skills 模块重构决策

**决定：采用方案 B - 合并为统一的 SkillRegistry**

```python
class SkillRegistry:
    def __init__(self):
        self.loaders = []  # 预定义 Skills（文件系统/数据库）
        self.runtimeSkills = {}  # 运行时注册的 Skills

    async def getSkill(self, skillId: str):
        # 先查运行时，再查 Loaders
        pass
```

**优势**：
- 消除命名冲突
- 提供统一接口
- 简化用户使用体验
- 支持多种 Skill 来源

### 5.3 需要移除的向后兼容代码

| 文件 | 位置 | 说明 |
|------|------|------|
| `loom/api/app.py` | 整个文件 | LoomApp 类（已标记废弃 0.4.7） |
| `loom/api/models.py` | 整个文件 | AgentConfig 和 MemoryConfig（已标记废弃） |
| `loom/tools/tool_creation.py` | 第 216 行 | 本地工具存储（向后兼容注释） |
| `loom/tools/context_tools.py` | 第 730 行 | 未使用的 event_bus 参数 |
| `loom/agent/core.py` | 多处 | enable_tool_creation 参数及相关逻辑 |

### 5.4 新的 Agent API 设计

**核心方法**：`Agent.create()` - 直接创建 Agent 实例

```python
# 简单用法
agent = Agent.create(llm)

# 常用配置
agent = Agent.create(
    llm=llm,
    systemPrompt="你是一个AI助手",
    nodeId="my-agent",
    maxIterations=20
)

# 高级配置 - 显式传入全局组件
eventBus = EventBus()
agent = Agent.create(
    llm=llm,
    systemPrompt="...",
    eventBus=eventBus,
    maxIterations=20
)
```

**工具和 Skill 配置**：

```python
# 简单用法 - 通过参数配置
agent = Agent.create(
    llm=llm,
    tools=[tool1, tool2],
    skills=["python-dev", "testing"]
)

# 高级用法 - 传入自定义 CapabilityRegistry
capabilities = CapabilityRegistry()
capabilities.registerTool(customTool)
capabilities.registerSkill("advanced-skill")

agent = Agent.create(
    llm=llm,
    capabilities=capabilities
)
```

---

## Phase 2 实施状态

**实施日期**: 2026-02-02
**分支**: feature/agent-skill-refactor

### P0 - 关键问题修复

- [x] **Agent 工具列表包含 sandbox_manager**
  - 确认 `_get_available_tools()` 正确合并 sandbox_manager 工具
  - 添加测试验证 sandbox_manager 工具出现在工具列表中
  - 提交: `bc87d7f` - test: add sandbox_manager integration test for Agent tool list (P0)

### P1 - 统一工具管理

- [x] **SkillActivator 依赖校验统一使用 SandboxToolManager**
  - 确认 `validate_dependencies` 优先使用 tool_manager
  - 添加测试验证 tool_manager 优先级和行为
  - 更新文档推荐使用 SandboxToolManager
  - 提交: `06a88ed` - test: add tool_manager dependency validation tests (P1)
  - 提交: `f368705` - docs: add SandboxToolManager as recommended tool management approach (P1)

### P2 - 统一技能管理

- [x] **确认唯一 SkillRegistry 与导出**
  - 验证 `loom/skills/registry.py` 为统一实现
  - 验证 `skill_registry.py` 仅重导出
  - 验证 `__init__.py` 仅导出一个 SkillRegistry
  - 引用检查：无对「另一套」SkillRegistry 的引用

- [x] **CapabilityRegistry 与 SkillRegistry 对接**
  - 验证 CapabilityRegistry 使用统一 SkillRegistry
  - 验证 validate_skill_dependencies 兼容 SkillDefinition 和 dict 格式
  - 所有测试通过（22/22）

- [x] **完善单元测试**
  - Agent: 测试 sandbox_manager、tool_registry、两者都有的场景
  - SkillActivator: 测试 tool_manager、tool_registry、优先级
  - 所有测试通过（363 passed）
  - 提交: `c1e031a` - test: add test for Agent with both sandbox_manager and tool_registry (P2)

### 验证清单

- [x] Agent 工具列表与执行来源一致（sandbox_manager 工具一定出现在 _get_available_tools 中）
- [x] SkillActivator 依赖校验与执行一致（优先 tool_manager/SandboxToolManager）
- [x] 仅一套 SkillRegistry 对外暴露，Loader + 运行时注册统一
- [x] CapabilityRegistry 使用统一 SkillRegistry，无双轨 Skill 来源
- [x] 相关单测通过且已补全
- [x] 文档与示例明确「以 SandboxToolManager 为主、单一 SkillRegistry」

### 测试结果

**基线测试** (Task 0):
- 1155 passed, 2 failed (performance tests, pre-existing)
- 11 skipped, 9 xfailed, 2 xpassed

**Phase 2 后测试** (Task 5):
- 363 passed (agent + skills + tools)
- 8 xfailed, 1 xpassed
- 所有新增测试通过

### 提交记录

1. `bc87d7f` - test: add sandbox_manager integration test for Agent tool list (P0)
2. `06a88ed` - test: add tool_manager dependency validation tests (P1)
3. `f368705` - docs: add SandboxToolManager as recommended tool management approach (P1)
4. `c1e031a` - test: add test for Agent with both sandbox_manager and tool_registry (P2)

---

*文档版本：基于 loom-agent 代码库梳理，适用于 feature/agent-skill-refactor 分支及后续整合。*
*最后更新：2026-02-02 - 添加 API 重构设计决策*
