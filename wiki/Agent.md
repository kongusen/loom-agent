# Agent 模块

`loom/agent/` 是框架的核心模块，实现了统一的智能体抽象。

## 文件结构

```
loom/agent/
├── base.py          # BaseNode - 所有节点的基类
├── core.py          # Agent - 统一智能体类（Mixin 组合）
├── builder.py       # AgentBuilder - 链式构建器
├── factory.py       # AgentFactory - 工厂方法
├── executor.py      # ExecutorMixin - 执行循环
├── execution.py     # ExecutionEngine - 提取的执行引擎
├── tool_handler.py  # ToolHandlerMixin - 工具管理
├── tool_router.py   # ToolRouter - 工具路由
├── skill_handler.py # SkillHandlerMixin - 技能管理
├── planner.py       # PlannerMixin - 规划逻辑
├── delegator.py     # DelegatorMixin - 委派逻辑
└── card.py          # AgentCard - 能力声明
```

## BaseNode

所有节点的基类，提供基础能力：

- **生命周期管理** — `on_start`, `on_complete`, `on_error`, `on_planning`, `on_tool_call_request`
- **事件发布** — 通过 EventBus 发布观测事件（thinking, tool_call, tool_result, message）
- **集体记忆** — 查询其他节点的事件（`query_collective_memory`, `query_sibling_insights`）
- **拦截器链** — `InterceptorChain` 支持中间件模式（如 SessionLaneInterceptor）
- **统计信息** — 执行次数、成功率、平均耗时

```python
class BaseNode:
    node_id: str              # 节点唯一标识
    node_type: str            # 节点类型
    agent_card: AgentCard     # 能力声明
    event_bus: EventBus       # 事件总线
    state: NodeState          # IDLE / RUNNING / COMPLETED / FAILED
    interceptor_chain: InterceptorChain
```

## Agent

通过五个 Mixin 组合而成的统一智能体类：

### 创建方式

```python
# 1. 工厂方法（推荐）
agent = Agent.create(
    llm,
    system_prompt="你是一个AI助手",
    tools=[...],
    knowledge_base=kb,
    max_context_tokens=4000,
    max_iterations=10,
)

# 2. Builder 模式
agent = (Agent.builder(llm)
    .with_system_prompt("你是一个AI助手")
    .with_tools([...])
    .build())

# 3. 直接实例化
agent = Agent(node_id="agent1", llm_provider=llm, ...)
```

### 核心参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `llm_provider` | `LLMProvider` | LLM 提供者 |
| `system_prompt` | `str` | 用户业务提示词（框架能力自动追加） |
| `tools` | `list[dict]` | 工具定义列表（`tools=[]` 表示不使用工具） |
| `knowledge_base` | `KnowledgeBaseProvider` | 知识库（可选） |
| `max_context_tokens` | `int` | 上下文窗口大小（默认 4000） |
| `max_iterations` | `int` | 最大迭代次数（默认 10） |
| `require_done_tool` | `bool` | 是否要求显式调用 done 工具（默认 True） |
| `session_isolation` | `SessionIsolationMode` | Session 隔离模式（strict/advisory/none） |
| `memory_config` | `MemoryConfig \| dict` | 记忆配置 |
| `tool_policy` | `ToolPolicy` | 工具权限策略 |
| `shared_pool` | `SharedMemoryPool` | 跨 Agent 共享记忆池（多 Agent 传入同一实例，子节点自动继承） |

### 执行接口

```python
# 简化接口
result: str = await agent.run("帮我分析这段代码")

# 完整接口
task = Task(taskId="...", action="execute", parameters={"content": "..."})
result_task: Task = await agent.execute_task(task)
```

### System Prompt 构建

Agent 的 system_prompt 由三层组成：

1. **用户提示词** — `system_prompt` 参数传入的业务逻辑
2. **Skill 指令** — 已激活 Skill 的指令注入
3. **框架能力** — 四范式自主能力描述（自动追加，不可配置）

当 Agent 有 memory 或 knowledge_base 时，会自动注入 `MEMORY_GUIDANCE`（记忆管理指引）。

### Importance 标记

Agent 在响应末尾可以添加 `<imp:X.X/>` 标记（0.0-1.0），框架自动提取并用于记忆优先级排序。用户不会看到此标记。

```
"建议使用 OAuth2.0 Authorization Code 模式。<imp:0.8/>"
→ clean_text: "建议使用 OAuth2.0 Authorization Code 模式。"
→ importance: 0.8
```

## Mixin 职责

### ToolHandlerMixin
- 工具列表构建（基础工具 + 元工具 + Skill 工具 + 沙盒工具）
- 动态工具创建（`create_tool` 元工具）
- Ephemeral 消息过滤（大输出工具只保留最近 N 次）

### SkillHandlerMixin
- Skill 发现（Progressive Disclosure）
- Skill 激活（INJECTION 模式 — 指令注入到 system_prompt）
- 激活状态管理（`_active_skills` 集合）

### PlannerMixin
- `create_plan` 元工具处理
- 子任务创建与分形执行
- LLM 综合生成最终答案

### DelegatorMixin
- `delegate_task` 元工具处理
- 子节点创建（`_create_child_node`）
- 记忆同步（通过 `parent_memory` 自动继承）

### ExecutorMixin
- ReAct 执行循环
- LLM 交互与 streaming
- 消息历史管理

## AgentFactory

`Agent.create()` 委派给 `AgentFactory.create()`，处理：

- 渐进式披露配置解析（`ToolConfig`, `ContextConfig`）
- Skill 注册表和加载器初始化
- SandboxToolManager 创建
- 内置工具注册（bash, file, http, search, todo, done）
- 可调用对象转 MCP 工具定义

## ToolRouter

从 `core.py` 提取的工具路由组件，负责将工具调用分发到正确的执行器：

- 元工具（create_plan, delegate_task, create_tool）
- 沙盒工具（SandboxToolManager）
- 动态工具（DynamicToolExecutor）
- 统一检索工具（query）
