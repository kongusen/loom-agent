# Loom 系统深入研究报告 —— 面向 v0.5.0

基于对 RESEARCH_CONFIG_AGENT_CAPABILITIES、RESEARCH_MEMORY_FRACTAL、RESEARCH_PROTOCOL_EVENTS_RUNTIME、RESEARCH_API_CAPABILITIES、OPTIMIZATION_SKILLS_TOOLS 五份文档的综览，本报告梳理：**系统想实现的**、**已弃用/冗余/错误/不合理之处**，以及 **v0.5.0 优化方向**。v0.5.0 以公理系统为骨架，**完全以 LLM 的自我判断能力为核心** 构建 Agent 框架。

---

## 一、系统想实现的（目标与公理）

### 1.1 核心愿景

- **对抗认知熵增**：在**复杂度**与**时间**两个维度上保持可扩展——空间上通过分形架构实现 O(1) 认知负载，时间上通过记忆代谢（L1→L4）实现长期连贯。
- **认知即编排**：「Intelligence = emergent property of orchestration, not raw LLM power」；认知不在单节点内，而在节点间编排中涌现。
- **长时程可靠**：解决 Long Horizon Collapse（约 20 步后失去一致性），支持小时/天级任务与多日连贯运行。

### 1.2 六大公理与对应实现

| 公理 | 陈述 | 当前实现要点 |
|------|------|--------------|
| **A1 统一接口** | ∀x ∈ System: x implements NodeProtocol | protocol.NodeProtocol、Task、AgentCard；Agent、NodeContainer、Pipeline 等均实现 execute_task / get_capabilities |
| **A2 事件主权** | ∀communication = Task | events.EventBus 按 action 路由；Transport 可选；LoomMemory 通配订阅 "*" 收 Task |
| **A3 分形自相似** | structure(node) ≅ structure(System) | fractal.NodeContainer（单子）、MemoryScope（LOCAL/SHARED/INHERITED/GLOBAL）；Agent 内部分形通过 meta_tools（create_plan、delegate_task）由 LLM 决策 |
| **A4 记忆层次** | Memory = L1 ⊂ L2 ⊂ L3 ⊂ L4 | memory.LoomMemory（Task 分层）、MemoryManager（L1-L4 + 作用域）；promote 链 L1→L2→L3→L4 |
| **A5 认知调度** | Cognition = Orchestration(N1,…,Nk) | orchestration.Orchestrator（Router/Crew）、Workflow、Pipeline；runtime.Dispatcher（target_agent + EventBus） |
| **A6 四范式工作** | Reflection / ToolUse / Planning / MultiAgent | Agent 内由 LLM 自主选择；AgentCapability 声明；create_plan、delegate_task 等 meta_tools 供 LLM 调用 |

### 1.3 以 LLM 自我判断为核心的设计意图

- **框架提供结构，LLM 提供决策**：何时用工具、何时规划、何时委派、激活哪些 Skill、任务复杂度与是否分形等，应由 LLM 在统一接口内自主判断，而非由硬编码规则主导。
- **已有 LLM 参与点**：SkillActivator.find_relevant_skills（按任务选 Skill）、QualityEvaluator（LLM-as-a-judge 评估子任务质量）、ResultSynthesizer 的 llm 策略、create_plan/delegate_task 由 LLM 决定是否调用。
- **v0.5.0 方向**：在保留公理骨架的前提下，**扩大「由 LLM 判断」的决策面**，**收缩「由规则/启发式固定」的决策面**，使整个 Agent 体系更一致地以 LLM 自我判断为核心。

---

## 二、已弃用（v0.5.0 移除）

| 项 | 位置 | 说明 |
|----|------|------|
| **LoomApp** | loom/api/app.py | 0.4.7 已弃用，v0.5.0 移除；替代：Agent.from_llm() / Agent.create() |
| **api.models.AgentConfig** | loom/api/models.py | Pydantic 版 Agent 配置，0.4.7 弃用，v0.5.0 移除；替代：Agent.create(...) 参数 + loom.config.agent.AgentConfig（子节点继承） |
| **api 包顶导出** | loom/api/__init__.py | 若移除 LoomApp/AgentConfig，需保留或调整重导出（protocol/events/…），并明确推荐入口为 Agent.create |
| **enable_tool_creation 及相关** | OPTIMIZATION_SKILLS_TOOLS 五.5.3 | create_tool 能力建议优先用 delegate_task；v0.5.0 可移除 enable_tool_creation 与 DynamicToolExecutor 相关逻辑，简化 Agent |

上述移除后，**统一入口**为：`Agent.create(llm, ...)` 或 `Agent.from_llm(llm, ...)`，配置与能力通过参数或 CapabilityRegistry 注入。

---

## 三、冗余与不一致

### 3.1 双轨/双名导致的冗余

- **两套 SkillRegistry**：`loom/skills/registry.py`（Loader + SkillDefinition，async）与 `loom/skills/skill_registry.py`（dict + handler，sync）均以「SkillRegistry」出现；Agent 用 Loader 版，LoomApp/CapabilityRegistry 用 dict 版，命名与入口双轨并存。
- **两套 AgentConfig**：`loom.config.agent.AgentConfig`（dataclass，继承/合并）与 `loom.api.models.AgentConfig`（Pydantic，弃用）；LoomApp.create_agent 只把 api 的字段映射到 Agent 构造参数，**未**设置 Agent.config 为 config.agent.AgentConfig，子节点继承若经 LoomApp 则无法用到 config 继承。
- **两套工具入口**：ToolRegistry（仅注册/查询，LoomApp、SkillActivator.has）与 SandboxToolManager（注册+执行+沙盒，推荐）；Agent 同时接两者，工具列表来源分散。

### 3.2 未贯通的设计（能力门面未接入主路径）

- **CapabilityRegistry**：仅测试使用；api、agent 均未引用。设计上是「能力发现 + 依赖校验」的门面，但与当前创建 Agent、构造工具列表的主路径未接通。
- **find_relevant_capabilities**：Skill 侧返回全部 skill_ids，未按任务过滤（TODO）；若以 LLM 为核心，应接入「按任务描述发现相关能力」的逻辑（如 SkillActivator.find_relevant_skills 或等价 LLM 调用）。

### 3.3 文档与导出不统一

- **config**：AgentConfig 未在 config/__init__ 的 __all__ 中导出；用户需知从 loom.config.agent 导入。
- **api**：StreamAPI 未在 api/__init__ 导出；流式观测需单独从 loom.api.stream_api 导入。
- **fractal**：FractalMemory、resolvers、sync 未在包顶导出，文档中已说明直接子模块导入。

---

## 四、错误与不合理

### 4.1 逻辑错误（必修）

- **Agent 工具列表缺少 sandbox_manager**（OPTIMIZATION_SKILLS_TOOLS P0）：`_get_available_tools()` 未把 sandbox_manager 中的工具加入发给 LLM 的列表，仅执行路径使用 sandbox_manager；若用户只传 sandbox_manager，LLM 看不到这些工具。**修复**：在 _get_available_tools() 中合并 sandbox_manager.list_tools()，并与现有去重一致。

### 4.2 不一致与不合理

- **依赖校验与执行入口不一致**：SkillActivator.validate_dependencies 使用 tool_registry.has()，而推荐执行入口是 SandboxToolManager；若用户只提供 sandbox_manager，依赖校验可能误判。**方向**：SkillActivator 支持以 SandboxToolManager 为「工具提供方」做校验（或统一工具提供方协议）。
- **L4 更新依赖显式异步调用**：promote_tasks() 同步版不执行 L3→L4；只有 promote_tasks_async() 才做 L4 向量化；若调用方只调 promote_tasks()，L4 长期不更新。**方向**：文档/日志明确「需定期或批次后调用 promote_tasks_async」，或在 Agent/记忆生命周期内提供钩子。
- **importance 完全由规则推断**：LoomMemory._infer_importance(task) 仅按 task.action 固定映射（如 node.error→0.9）；与「以 LLM 自我判断为核心」不一致。**方向**：v0.5.0 可保留规则作为默认，但允许可选「由 LLM 对任务重要性打分」的路径，写入 task.metadata，再供 L2/L3 提升使用。
- **RouterOrchestrator 选节点**：当前按 task.action 关键词与 AgentCapability 匹配，无匹配则第一个节点；若以 LLM 为核心，可改为「由 LLM 根据任务描述与节点能力描述选节点」，仅保留降级为规则或第一个节点。

---

## 五、v0.5.0 优化方向（公理 + LLM 自我判断）

### 5.1 骨架：公理系统不动

- **A1–A6** 及现有 protocol、events、memory、fractal、orchestration、runtime 的职责边界保持不变；NodeProtocol、Task、EventBus、L1-L4、MemoryManager、Orchestrator、Dispatcher 等仍是基础设施。
- **移除**：LoomApp、api.models.AgentConfig、以及 OPTIMIZATION_SKILLS_TOOLS 中列出的向后兼容/废弃代码（如 enable_tool_creation 相关）。
- **统一入口**：推荐 `Agent.create(llm, ...)`，可选 `Agent.from_llm(llm, ...)`；配置与能力通过参数或 CapabilityRegistry 注入，不再经 LoomApp。

### 5.2 以 LLM 自我判断为核心的增强

- **能力发现**：CapabilityRegistry.find_relevant_capabilities 接入「按任务描述发现相关 tools/skills」的逻辑；Skill 侧复用或对齐 SkillActivator.find_relevant_skills（LLM 选相关 Skill），Tool 侧可增加「按任务描述筛选/排序工具」的 LLM 调用（可选），使「发现」与「执行」一致且以 LLM 判断为主。
- **重要性/优先级**：在保留 _infer_importance 默认规则的前提下，支持「可选：由 LLM 对当前任务/结果做重要性或优先级打分」，结果写入 Task.metadata，供 L2/L3 提升与上下文预算使用；与 A4 记忆层次兼容。
- **分形与编排**：是否分形、是否委派、选哪个子节点，已由 LLM 通过 create_plan、delegate_task 决策；v0.5.0 可明确文档化「框架只提供预算与结构，分解与路由由 LLM 决定」，并保证 BudgetTracker、AgentConfig.inherit 与 meta_tools 的衔接清晰。
- **质量与合成**：QualityEvaluator（LLM-as-a-judge）、ResultSynthesizer 的 llm 策略已体现 LLM 判断；v0.5.0 可将「子任务质量评估」「结果合成策略选择」更明确地列为「由 LLM 自我判断」的推荐路径，规则仅作降级。

### 5.3 工具与 Skill 统一（与 OPTIMIZATION_SKILLS_TOOLS 对齐）

- **P0**：修复 _get_available_tools() 包含 sandbox_manager 工具（必做）。
- **P1**：以 SandboxToolManager 为默认工具入口；SkillActivator 依赖校验支持 SandboxToolManager；Agent 文档与默认路径仅暴露 sandbox_manager，tool_registry 仅兼容或逐步废弃。
- **P2**：两套 Skill 改名/文档区分（方案 A）或统一到 Skill 提供方协议（方案 B）；CapabilityRegistry 能对接 Agent 实际使用的 Skill 来源（Loader 版或 dict 版）。
- **P3**：CapabilityRegistry 接入按任务过滤的 Skill（及可选 Tool）发现；与 Agent 构造链集成（简单用法：Agent.create(llm, tools=[], skills=[]) 内部构造或使用 CapabilityRegistry，使「发现—校验—执行」一致）。

### 5.4 配置与 API 清理

- **config**：AgentConfig 在 config/__init__ 中统一导出（或文档明确从 config.agent 导入）；子节点继承仅使用 config.agent.AgentConfig.inherit，不再依赖 api 的 AgentConfig。
- **api**：移除 LoomApp、api.models.AgentConfig 后，保留 loom.api 对 protocol/events/memory/orchestration/runtime 等的重导出，并推荐 Agent.create；若保留流式观测，将 StreamAPI 在 api 包顶导出或文档标明。
- **渐进式披露**：简单用法 `Agent.create(llm, tools=[], skills=[...])`；高级用法传入 event_bus、sandbox_manager 或 capabilities（CapabilityRegistry），显式控制全局组件。

---

## 六、实施优先级建议

1. **P0（必做）**：修复 Agent 工具列表缺失 sandbox_manager（_get_available_tools）。
2. **v0.5.0 移除**：LoomApp、api.models.AgentConfig；OPTIMIZATION_SKILLS_TOOLS 五.5.3 所列向后兼容/废弃代码。
3. **统一入口与配置**：文档与示例统一到 Agent.create / Agent.from_llm；config.agent.AgentConfig 导出与子节点继承说明；CapabilityRegistry 与 Agent 构造链集成（简单/高级用法）。
4. **工具/Skill 统一**：P1（SandboxToolManager 为主、SkillActivator 支持）、P2（Skill 双轨改名或协议统一）、P3（find_relevant_capabilities 按任务过滤）。
5. **LLM 自我判断增强**：能力发现与重要性/质量评估的 LLM 路径可文档化与可选实现；RouterOrchestrator 可选「由 LLM 选节点」；promote_tasks_async 与 L4 更新的使用方式在文档/钩子中明确。

---

## 七、小结

- **系统想实现的**：在六大公理下实现长时程、可扩展的认知系统，认知通过编排与记忆代谢涌现；**v0.5.0 进一步把「做什么、选什么、何时分解」交给 LLM 自我判断，框架只提供协议、事件、记忆、编排与预算。**
- **已弃用**：LoomApp、api.models.AgentConfig 及部分向后兼容逻辑，v0.5.0 移除。
- **冗余与不一致**：双轨 Skill、双轨 AgentConfig、双轨工具入口；CapabilityRegistry 未接入主路径；部分导出与文档不统一。
- **错误与不合理**：Agent 工具列表漏 sandbox_manager（必修）；依赖校验与执行入口不一致；L4 更新与 importance 推断过于规则化；可逐步改为「LLM 优先、规则降级」。
- **v0.5.0 方向**：公理骨架不变，移除弃用代码，统一入口与配置，修复工具列表，统一工具/Skill 与能力发现，并以「**完全以 LLM 的自我判断能力为核心**」为主线增强能力发现、重要性/质量评估与编排决策的可选 LLM 路径。

---

*报告版本：基于五份研究文档与公理系统梳理，适用于 v0.5.0 规划与 feature/agent-skill-refactor 及后续分支。*
