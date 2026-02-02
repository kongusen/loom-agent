# loom/api、loom/capabilities 研究总结

基于对两个模块的代码阅读与调用关系梳理的总结。

---

## 一、loom/api（统一对外 API）

### 1.1 定位

- **统一对外 API**：`loom.api` 作为框架顶层入口，按公理分层重导出协议、事件、分形、记忆、编排、运行时等；同时提供 **LoomApp**（FastAPI 风格应用类）与 **AgentConfig**（Pydantic 配置模型）用于创建 Agent。
- **弃用状态**：LoomApp 与 api.models.AgentConfig 均标记为 **deprecated（0.4.7）**，计划在 **v0.5.0 移除**，推荐使用 `Agent.from_llm()` 或 `Agent.create()` 代替。

### 1.2 核心组件

| 文件 | 内容 | 说明 |
|------|------|------|
| **__init__.py** | 重导出 + LoomApp、AgentConfig | 从 protocol/events/fractal/memory/orchestration/runtime 重导出核心类型；导出 LoomApp、AgentConfig（来自 api.models）；__version__ = "0.4.6" |
| **app.py** | `LoomApp` | 持 event_bus、dispatcher、_llm_provider、_default_tools、_agents、_tool_registry（ToolRegistry）、_skill_registry（loom.skills.skill_registry.SkillRegistry）、_skill_activator；set_llm_provider、set_knowledge_base、add_tools、register_tool、register_skill、create_agent、get_agent、list_agents；create_agent 时传入 tool_registry、skill_registry、skill_activator 给 Agent，**未使用 SandboxToolManager 或 CapabilityRegistry** |
| **models.py** | `AgentConfig`, `MemoryConfig` | Pydantic BaseModel：AgentConfig 含 agent_id、name、description、capabilities、system_prompt、max_iterations、require_done_tool、enable_observation、enable_context_tools、enable_tool_creation、max_context_tokens、memory_config（MemoryConfig）、context_budget_config、enabled_skills、disabled_tools、extra_tools、knowledge_*；MemoryConfig 含 LoomMemory 相关参数；capabilities 校验为 tool_use/reflection/planning/multi_agent；实例化时触发 DeprecationWarning |
| **stream_api.py** | `StreamAPI` | 持 event_bus、EventStreamConverter；stream_node_events(node_id)、stream_thinking_events(node_id)、stream_all_events(action_pattern)；返回 SSE 流，供 FastAPI StreamingResponse 使用；**未在 api/__init__ 中导出** |

### 1.3 与 config.agent.AgentConfig 的区别

- **loom.api.models.AgentConfig**：Pydantic 模型，用于 LoomApp.create_agent(config)；含 agent_id、name、capabilities、memory_config（嵌套 MemoryConfig）等；**已弃用**。
- **loom.config.agent.AgentConfig**：dataclass，用于 Agent 内部 config 与子节点继承（enabled_skills、disabled_skills、extra_tools、disabled_tools、skill_activation_mode）；**Agent 实际使用的是 config.agent.AgentConfig**；LoomApp.create_agent 时把 api.models.AgentConfig 的字段映射到 Agent 构造参数，**未**把 api 的 AgentConfig 转为 config.agent.AgentConfig 传入 Agent.config。

### 1.4 使用方

- **上层应用**：通过 `from loom.api import LoomApp, AgentConfig` 创建应用与 Agent；若需流式观测，需单独 `from loom.api.stream_api import StreamAPI`。
- **Agent**：由 LoomApp.create_agent 创建时，接收 tool_registry、skill_registry、skill_activator（及 event_bus 等），**不接收** sandbox_manager 或 CapabilityRegistry。

### 1.5 小结

- api 模块 = **统一重导出** + **LoomApp（弃用）** + **api.models.AgentConfig（弃用）** + **StreamAPI（未在包顶导出）**。
- LoomApp 使用 **ToolRegistry** 与 **loom.skills.skill_registry.SkillRegistry**，与 **loom/capabilities** 无直接关系；当前代码库中 **api 未使用 CapabilityRegistry**。

---

## 二、loom/capabilities（能力门面）

### 2.1 定位

- **门面模式**：不新建存储，复用 **SandboxToolManager** + **SkillRegistry**（+ 可选 SkillActivator）；提供统一能力发现与 Skill 依赖验证。
- **职责**：find_relevant_capabilities(task_description) → CapabilitySet；validate_skill_dependencies(skill_id) → ValidationResult。**不负责**工具执行与 Skill 实例化。

### 2.2 核心组件

| 文件 | 内容 | 说明 |
|------|------|------|
| **registry.py** | `CapabilityRegistry`, `CapabilitySet`, `ValidationResult` | 构造：sandbox_manager、skill_registry、skill_activator（当前 find/validate 未使用 skill_activator）；find：从 _tool_manager.list_tools 转 dict、从 _skill_registry.list_skills 取**全部** skill_ids（TODO：按任务过滤）；validate：get_skill(skill_id)、取 _metadata.required_tools、与 _tool_manager.list_tools 对比 |
| **__init__.py** | 导出 | CapabilityRegistry、CapabilitySet、ValidationResult |

### 2.3 与 api / agent / tools / skills 的关系

- **api**：LoomApp 使用 ToolRegistry + skill_registry（skill_registry.py），**未使用** CapabilityRegistry 或 SandboxToolManager；若未来「简单用法」希望统一能力入口，可在 LoomApp 或 Agent 构造链中引入 CapabilityRegistry（或等价逻辑）。
- **agent**：Agent 当前不持有 CapabilityRegistry；可传入 sandbox_manager、skill_registry，与 CapabilityRegistry 共用同一批组件（见 OPTIMIZATION_SKILLS_TOOLS.md）。
- **tools/skills**：CapabilityRegistry 依赖 **SandboxToolManager**（list_tools）与 **SkillRegistry**（list_skills、get_skill 返回 dict 且含 _metadata.required_tools），即适配 **loom.tools.sandbox_manager** 与 **loom.skills.skill_registry**（可调用工具型 Skill）；与 loom.skills.registry（Loader 版 SkillRegistry）未对接。

### 2.4 使用方

- **当前代码库**：仅 **tests/unit/test_capabilities** 使用 CapabilityRegistry；**api、agent 均未引用**。
- **设计意图**：供「创建 Agent 前的能力发现」或「运行时按任务推荐 tools/skills」使用；可与 API 重构中的「简单用法 / 高级用法」结合。

### 2.5 小结

- capabilities 模块 = **CapabilityRegistry（门面）** + **CapabilitySet / ValidationResult**；依赖 SandboxToolManager 与 SkillRegistry（dict 版）；与 api 无直接耦合，**api 未使用 capabilities**。

---

## 三、两模块关系图（概念）

```
                    +------------------+
                    | loom.api         |
                    | LoomApp (deprecated)
                    | AgentConfig (api.models, deprecated)
                    | StreamAPI (未在 __init__ 导出)
                    | 重导出 protocol/events/… |
                    +--------+---------+
                             |
         +-------------------+-------------------+
         |                   |                   |
         v                   v                   v
+----------------+  +----------------+  +----------------+
| LoomApp 内部   |  | loom.capabilities|  | Agent.from_llm |
| _tool_registry |  | CapabilityRegistry|  | Agent.create  |
| _skill_registry|  | find_relevant_   |  | (推荐替代)     |
| (ToolRegistry) |  | validate_skill_  |  |               |
| (skill_registry|  | (复用 sandbox_   |  |               |
|  .py)          |  |  manager +       |  |               |
|                |  |  skill_registry) |  |               |
+----------------+  +----------------+  +----------------+
        |                   |                   |
        | 当前无连接        | 当前仅测试使用    | 可不经 LoomApp
        v                   v                   v
+----------------+  +----------------+  +----------------+
| Agent          |  | SandboxToolManager| | tools/skills  |
| (tool_registry,|  | SkillRegistry     | | 组件          |
|  skill_registry|  | (同上)            | |               |
|  由 LoomApp 注入)|  |                  | |               |
+----------------+  +----------------+  +----------------+
```

---

## 四、可优化点（简要）

1. **api 弃用与迁移**：LoomApp、api.models.AgentConfig 已弃用，v0.5.0 移除；文档与示例应统一导向 Agent.from_llm() / Agent.create()，并说明如何用 config.agent.AgentConfig 做子节点继承。
2. **LoomApp 与 SandboxToolManager**：LoomApp 当前仅用 ToolRegistry，未用 SandboxToolManager；若希望与 capabilities 及 OPTIMIZATION_SKILLS_TOOLS 方案一致，可在 LoomApp 中支持传入或创建 SandboxToolManager，并传给 Agent。
3. **api 与 capabilities 集成**：若保留 LoomApp 一段时间，可增加「可选 CapabilityRegistry」：用户传入或由 LoomApp 内部构造，create_agent 时用其提供的 sandbox_manager/skill_registry，或仅用 find_relevant_capabilities 做发现与校验。
4. **StreamAPI 导出**：stream_api 未在 api/__init__ 的 __all__ 中导出；若流式观测是官方能力，建议在包顶导出或文档中明确从 loom.api.stream_api 导入。
5. **api.models.AgentConfig 与 config.agent.AgentConfig**：create_agent 时仅把 api 的 AgentConfig 字段传给 Agent 构造参数，未设置 Agent.config（loom.config.agent.AgentConfig）；若需子节点继承 enabled_skills/extra_tools 等，需在 create_agent 内从 api 的 config 构造 config.agent.AgentConfig 并传入。
6. **find_relevant_capabilities 过滤**：Skill 侧目前返回全部 skill_ids；可接入 SkillActivator.find_relevant_skills 或按 task_description 语义过滤（见 OPTIMIZATION_SKILLS_TOOLS.md P3）。

---

*文档版本：基于 loom-agent 代码库梳理，适用于 feature/agent-skill-refactor 及后续分支。*
