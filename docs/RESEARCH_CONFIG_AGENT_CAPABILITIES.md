# loom/config、loom/agent、loom/capabilities、loom/orchestration 研究总结

基于对四个模块的代码阅读与调用关系梳理的总结。

---

## 一、loom/config（配置体系）

### 1.1 定位

- 提供类型安全的配置模型，基于 **LoomBaseConfig**（Pydantic）统一接口：`to_dict`/`from_dict`、`to_json`/`from_json`，`extra="forbid"`、`validate_assignment=True`。
- **注意**：`config/__init__.py` **不导出 AgentConfig**；Agent 使用的 `AgentConfig` 来自 `loom.config.agent`，由 agent/core 直接 `from loom.config.agent import AgentConfig`。api 层另有已弃用的 `loom.api.models.AgentConfig`（Pydantic，v0.5.0 移除）。

### 1.2 核心组件

| 文件 | 内容 | 说明 |
|------|------|------|
| **base.py** | `LoomBaseConfig` | Pydantic BaseModel 基类；to_dict/from_dict、to_json/from_json |
| **agent.py** | `AgentConfig` | dataclass：enabled_skills、disabled_skills、extra_tools、disabled_tools、skill_activation_mode；inherit(parent, add/remove_skills, add/remove_tools)、merge(other) |
| **fractal.py** | `FractalConfig`, `GrowthTrigger`, `GrowthStrategy` | 分形：enabled、max_depth/max_children/max_total_nodes、growth_trigger（COMPLEXITY/ALWAYS/MANUAL/NEVER）、complexity_threshold、enable_auto_pruning、pruning_threshold 等 |
| **memory.py** | `MemoryConfig`, `MemoryLayerConfig`, `MemoryStrategyType` | L1-L4 每层 capacity、retention_hours、auto_compress、promote_threshold；strategy（SIMPLE/TIME_BASED/IMPORTANCE_BASED）；knowledge_base 可选 |
| **execution.py** | `ExecutionConfig` | timeout、max_retries、retry_delay、parallel_execution、max_parallel_tools、enable_sandbox、capture_output、log_execution |
| **llm.py** | `LLMConfig` | provider、model、api_key、base_url、temperature、max_tokens、timeout、max_retries、stream |
| **tool.py** | `ToolConfig` | enabled、auto_register、tool_timeout、max_tool_calls、require_confirmation、allowed_tools、blocked_tools、enable_tool_cache、cache_ttl |
| **knowledge.py** | 重导出 | 从 loom.providers.knowledge.base 重导出 KnowledgeBaseProvider、KnowledgeItem（向后兼容） |

### 1.3 使用方

- **Agent**：`config: AgentConfig`（来自 config.agent），用于 enabled_skills、extra_tools、disabled_tools 等；创建子节点时 `AgentConfig.inherit(parent, ...)`。
- **fractal/utils**：`FractalConfig`、`GrowthTrigger` 用于 `should_use_fractal(task, config)`。
- **providers/llm**：各 LLM 实现可选使用 `LLMConfig`。
- **config/__all__**：不包含 AgentConfig；若需从包顶导入需用 `from loom.config.agent import AgentConfig`。

### 1.4 小结

- config 模块 = **LoomBaseConfig 基类** + **各领域配置（agent/fractal/memory/execution/llm/tool）**；Agent 专用配置在 **config/agent.py**，未进包顶 __all__。
- 与 **agent**：Agent 与子 Agent 的 skills/tools 继承与禁用完全由 AgentConfig.inherit 驱动。

---

## 二、loom/agent（智能体核心）

### 2.1 定位

- 实现 **BaseNode**（观测、集体记忆、拦截器链）和 **Agent**（LLM + 四范式：反思、工具、规划、协作）；**AgentBuilder** 链式构建；**meta_tools**（delegate_task）；**SkillAgentNode**（Form 3 实例化 Skill）。
- 符合 A1/A2：NodeProtocol、Task 通信；与 memory、events、fractal、tools、skills 深度集成。

### 2.2 核心组件

| 文件 | 内容 | 说明 |
|------|------|------|
| **base.py** | `BaseNode`, `NodeState` | node_id、source_uri、agent_card、event_bus、enable_observation、enable_collective_memory、state、stats、interceptor_chain；_publish_event、publish_thinking、publish_tool_call 等；execute_task 由子类实现 |
| **core.py** | `Agent`, `AgentBuilder` | 继承 BaseNode；llm_provider、system_prompt、memory（MemoryManager）、context_orchestrator、config（AgentConfig）、skill_registry、skill_activator、tool_registry、sandbox_manager、parent_memory；_build_tool_list、_get_available_tools、_execute_impl（主循环）；from_llm、create→AgentBuilder；delegate、_auto_delegate、_create_child_node、_sync_memory_from_child |
| **meta_tools.py** | `create_delegate_task_tool`, `execute_delegate_task` | delegate_task 工具定义；execute_delegate_task 调 agent._auto_delegate |
| **skill_node.py** | `SkillAgentNode` | 继承 BaseNode；用 Skill 的 instructions 作 system_prompt；_execute_impl 简化版（无工具循环）；Form 3 实例化形态 |

### 2.3 Agent 构造与依赖链

- **构造**：必选 node_id、llm_provider；可选 system_prompt、tools、event_bus、skill_registry、skill_activator、tool_registry、sandbox_manager、parent_memory、config、memory_config、context_budget_config、knowledge_base 等。
- **内部创建**：MemoryManager（parent=parent_memory, event_bus）；ContextOrchestrator（sources：MemoryContextSource、MemoryScopeContextSource、可选 KnowledgeContextSource）；ContextToolExecutor（enable_context_tools）；DynamicToolExecutor（enable_tool_creation，sandbox_manager）；若未传 skill_activator 且存在 skill_registry 则创建 SkillActivator(tool_registry)。
- **工具列表**：_build_tool_list → _get_available_tools（self.tools、config.extra_tools 从 tool_registry、**未含 sandbox_manager 工具**，见 OPTIMIZATION_SKILLS_TOOLS.md）+ create_plan、delegate_task、context_tools、create_tool 等元工具。
- **执行**：_execute_impl 中 context_orchestrator.build_context、LLM 调用、工具执行（先 context_tools→sandbox_manager→tool_registry）、done 检测、迭代直至完成或 max_iterations。

### 2.4 委派与子节点

- **delegate(task, target_node_id)**：构造 Task 经 event_bus.publish(task, wait_result=True) 发给目标节点。
- **_auto_delegate(args, parent_task)**：由 delegate_task meta-tool 触发；创建 subtask、_ensure_shared_task_context、_create_child_node（AgentConfig.inherit、子 Agent 持 parent_memory=self.memory）、execute_task(subtask)、_sync_memory_from_child（SHARED 与 L2 回写）。
- **子节点**：与父共享 event_bus、skill_registry、tool_registry、sandbox_manager、skill_activator；独立 config（继承）、memory（parent_memory=self.memory）、recursive_depth+1、budget_tracker 同一实例。

### 2.5 使用方

- **api/app**：LoomApp 创建 Agent 时传入 event_bus、skill_registry、tool_registry、sandbox_manager 等。
- **orchestration**：可注册 Agent 为节点、通过 Dispatcher 或 EventBus 调度。
- **SkillActivator**：Form 3 时 instantiate 出 SkillAgentNode。

### 2.6 小结

- agent 模块 = **BaseNode（观测、记忆、拦截器）** + **Agent（LLM、MemoryManager、ContextOrchestrator、config、skills/tools 双轨、委派与子节点）** + **AgentBuilder** + **meta_tools（delegate_task）** + **SkillAgentNode（Form 3）**。
- 与 **config**：AgentConfig 驱动 skills/tools 继承与禁用；子节点 config = AgentConfig.inherit(parent, ...)。
- 与 **capabilities**：当前 Agent 未直接依赖 CapabilityRegistry；若采用「简单用法」由上层构造 CapabilityRegistry 再注入 sandbox_manager/skill_registry，则 Agent 仍只认现有参数。

---

## 三、loom/capabilities（能力门面）

### 3.1 定位

- **门面模式**：不新建存储，复用 SandboxToolManager + SkillRegistry（+ 可选 SkillActivator）；提供统一能力发现与 Skill 依赖验证。
- **职责**：find_relevant_capabilities(task_description) → CapabilitySet（tools + skill_ids）；validate_skill_dependencies(skill_id) → ValidationResult（is_valid、missing_tools、error、can_autofix）。

### 3.2 核心组件

| 文件 | 内容 | 说明 |
|------|------|------|
| **registry.py** | `CapabilityRegistry`, `CapabilitySet`, `ValidationResult` | 构造：sandbox_manager、skill_registry、skill_activator（当前未在 find/validate 中使用）；find：从 _tool_manager.list_tools 转 dict、从 _skill_registry.list_skills 取全部 skill_ids（**TODO：按任务过滤**）；validate：get_skill(skill_id)、取 _metadata.required_tools、与 _tool_manager.list_tools 对比 |
| **__init__.py** | 导出 | CapabilityRegistry、CapabilitySet、ValidationResult |

### 3.3 与 Agent / skills / tools 的关系

- **CapabilityRegistry** 期望 **SandboxToolManager**（list_tools）和 **SkillRegistry**（list_skills、get_skill 返回 dict 且含 _metadata.required_tools），即适配 **loom.skills.skill_registry**（可调用工具型 Skill）与 **loom.tools.sandbox_manager**。
- **Agent** 当前不持有 CapabilityRegistry；Agent 持有 sandbox_manager、skill_registry、skill_activator 等，若上层用 CapabilityRegistry(sandbox_manager, skill_registry, skill_activator) 做「发现 + 依赖校验」，与 Agent 是并列使用同一批组件。
- **find_relevant_capabilities** 目前 Skill 侧返回全部 skill_ids，未按 task_description 过滤（TODO）；可后续接入 SkillActivator.find_relevant_skills 或类似逻辑。

### 3.4 使用方

- 当前代码库中 **无** 对 CapabilityRegistry 的引用；设计上供「创建 Agent 前的能力发现」或「运行时按任务推荐 tools/skills」使用，可与 API 重构中的「简单用法 / 高级用法」结合（见 OPTIMIZATION_SKILLS_TOOLS.md）。

### 3.5 小结

- capabilities 模块 = **CapabilityRegistry（门面）** + **CapabilitySet / ValidationResult**；依赖 **SandboxToolManager** 与 **SkillRegistry（dict 版）**，与 **Agent** 无直接耦合，可与 Agent 共用同一 sandbox_manager / skill_registry 实例。

---

## 四、loom/orchestration（A5 认知调度）

### 4.1 定位与公理

- **公理 A5**：Cognition = Orchestration(N1, N2, …, Nk)  
- 认知通过节点编排涌现；「思考即是调度」。与 **runtime.Dispatcher**（按 target_agent 选节点 + EventBus fallback）不同，orchestration 提供 **多节点协作模式**（路由、团队、流水线、工作流）的抽象与实现。

### 4.2 核心组件

| 文件 | 内容 | 说明 |
|------|------|------|
| **base.py** | `Orchestrator` | 抽象基类：nodes: list[NodeProtocol]；add_node、remove_node；抽象方法 orchestrate(task) -> Task |
| **router.py** | `RouterOrchestrator` | 单节点路由：_select_node(task) 按 task.action 与 AgentCapability 匹配（tool_use/planning/reflection/multi_agent），无匹配则返回第一个节点；orchestrate 调 selected_node.execute_task(task) |
| **crew.py** | `CrewOrchestrator` | 多节点并行：orchestrate 时 asyncio.gather(所有 node.execute_task(task))，_aggregate_results 聚合成 results/errors 列表写入 task.result |
| **workflow.py** | `Workflow` | 抽象基类：workflow_id；抽象 execute(task)、get_description() |
| **sequential_workflow.py** | `SequentialWorkflow` | 固定步骤：steps: list[Callable]，execute 时依次 step(task, results)，结果写入 task.result["steps_results"] |
| **agent_workflow.py** | `AgentWorkflow` | 动态流程：持 coordinator_agent: Agent，execute 时 coordinator.execute_task(task)；由 Agent 自主决策与委派 |
| **pipeline_builder.py** | `PipelineBuilder`, `Pipeline`, `PipelineStep` | 流水线：StepType（SEQUENTIAL/PARALLEL/CONDITIONAL）；SequentialStep/ParallelStep/ConditionalStep；Pipeline 实现 NodeProtocol（node_id, source_uri, agent_card, execute_task），按 steps 顺序执行；PipelineBuilder 链式 add/then/parallel/conditional、build(pipeline_id) |

### 4.3 与 protocol / runtime / agent 的关系

- **protocol**：依赖 NodeProtocol、Task、TaskStatus、AgentCard；RouterOrchestrator 用 node.get_capabilities() 做能力匹配。
- **runtime**：Dispatcher 持 EventBus + nodes，dispatch(task) 时按 target_agent 选节点或 event_bus.publish；Orchestrator 持 nodes，orchestrate(task) 时按策略选一个或全部执行。二者可组合：Dispatcher 的节点可以是 Orchestrator 或 Pipeline。
- **agent**：Agent 实现 NodeProtocol，可作为 Orchestrator 的节点；AgentWorkflow 包装单个 Agent 为 Workflow；Pipeline 可包含 Agent 节点。fractal 文档注明「多节点编排请使用 Orchestrator」。

### 4.4 使用方

- **api/__init__.py**：导出 RouterOrchestrator、CrewOrchestrator，供上层组合多 Agent 或节点。
- **fractal/container**：README 与注释指出多子节点编排用 Orchestrator，NodeContainer 仅单子节点。

### 4.5 小结

- orchestration 模块 = **Orchestrator 基类** + **RouterOrchestrator（单节点路由）** + **CrewOrchestrator（多节点并行）** + **Workflow 基类** + **SequentialWorkflow / AgentWorkflow** + **PipelineBuilder / Pipeline（顺序/并行/条件步骤，实现 NodeProtocol）**。
- 与 **runtime.Dispatcher**：Dispatcher 按 target_agent 路由、无节点时走 EventBus；Orchestrator 按策略（路由/团队/流水线）执行 nodes，不直接依赖 EventBus。可把 Orchestrator 或 Pipeline 注册为 Dispatcher 的一个「节点」。

---

## 五、四模块关系图（概念）

```
                    +------------------+
                    | loom.config      |
                    | AgentConfig      |
                    | FractalConfig…   |
                    +--------+---------+
                             |
    +------------------------+------------------------+------------------------+
    |                        |                        |                        |
    v                        v                        v                        v
+----------+          +-------------+          +----------------+          +----------------+
| loom.    |          | loom.       |          | loom.capabilities|        | loom.          |
| agent    |          | orchestration|         | CapabilityRegistry|        | (其他)         |
| Agent    |<---------| Orchestrator |         | find_relevant_   |         | fractal/utils |
| config=  | 作为节点  | Router/Crew  |         | validate_skill_  |         |                |
| AgentConfig|        | Workflow    |         | (复用 tools/     |         |                |
| skill_   |          | Pipeline    |         |  skills 组件)    |         |                |
| sandbox_ |          +------+------+         +----------------+         +----------------+
+----+-----+                 |
     |                       | nodes: NodeProtocol[]
     |                       v
     |              +----------------+
     |              | protocol.Task  |
     +--------------| NodeProtocol   |
                    +----------------+
```

---

## 六、可优化点（简要）

1. **config 导出**：AgentConfig 未在 config/__init__.py 的 __all__ 中导出，建议统一从 `loom.config` 导出或文档标明从 `loom.config.agent` 导入。
2. **Agent 工具列表**：_get_available_tools 未包含 sandbox_manager 的工具，见 OPTIMIZATION_SKILLS_TOOLS.md P0。
3. **CapabilityRegistry 与 Agent 集成**：若采用「简单用法」Agent.create(llm, tools=[], skills=[])，可在 Agent 内部构造 CapabilityRegistry（或等价逻辑）并据此填充 sandbox_manager / skill_registry，或显式传入 capabilities 参数；当前 Agent 未使用 CapabilityRegistry。
4. **find_relevant_capabilities 过滤**：Skill 侧目前返回全部 skill_ids；可接入 SkillActivator.find_relevant_skills 或按 task 的语义过滤。
5. **AgentConfig 与 api.models.AgentConfig**：两套 AgentConfig（config.agent 的 dataclass 与 api.models 的 Pydantic 弃用版），文档或迁移说明中注明区别与替代方式。
6. **orchestration 与 Dispatcher**：Orchestrator/Pipeline 与 runtime.Dispatcher 的职责边界（Dispatcher 按 target_agent + EventBus；Orchestrator 按策略执行 nodes）在文档中可明确；将 Orchestrator 或 Pipeline 注册为 Dispatcher 的一个节点即可统一入口。

---

*文档版本：基于 loom-agent 代码库梳理，适用于 feature/agent-skill-refactor 及后续分支。*
