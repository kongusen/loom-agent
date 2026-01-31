# Loom-Agent 六大 Manager 体系深度分析

**文档版本**: 2.0
**分析日期**: 2026-01-31
**代码库状态**: feature/agent-skill-refactor 分支

---

## 目录

1. [架构概览](#架构概览)
2. [Agent Manager 体系](#1-agent-manager-体系)
3. [Tool Manager 体系](#2-tool-manager-体系)
4. [Fractal Manager 体系](#3-fractal-manager-体系)
5. [Memory Manager 体系](#4-memory-manager-体系)
6. [Event+Task Manager 体系](#5-eventtask-manager-体系)
7. [Skill Manager 体系](#6-skill-manager-体系)
8. [系统集成与交互](#系统集成与交互)
9. [设计模式与架构决策](#设计模式与架构决策)

---

## 架构概览

Loom-Agent 是一个基于公理系统的多智能体框架，通过六大 Manager 体系实现「智能 = 编排的涌现」。这六个系统相互协作，形成了一个完整的智能体生态系统。

### 核心设计原则

1. **唯一性原则** - 每个功能只在一个地方实现
2. **分层架构** - 基础能力在底层，高级功能在上层
3. **事件驱动** - 通过 EventBus 实现松耦合通信
4. **分形自相似** - 父子节点具有相同的能力结构
5. **渐进式披露** - 按需加载能力和上下文

### 系统依赖关系图

```
┌─────────────────────────────────────────────────────────────┐
│                         LoomApp                              │
│  (应用入口 - 持有所有全局单例)                                │
└─────────────────────────────────────────────────────────────┘
                              │
                              ├─── EventBus (事件总线)
                              ├─── Dispatcher (任务分发)
                              ├─── ToolRegistry (工具注册表)
                              ├─── SkillRegistry (技能注册表)
                              ├─── SkillActivator (技能激活器)
                              └─── KnowledgeBase (知识库)
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                          Agent                               │
│  (智能体核心 - 继承 BaseNode)                                │
└─────────────────────────────────────────────────────────────┘
                              │
                              ├─── LoomMemory (L1-L4 分层记忆)
                              ├─── FractalMemory (分形记忆)
                              ├─── TaskContextManager (上下文管理)
                              ├─── SandboxToolManager (沙盒工具管理)
                              ├─── AgentConfig (配置继承)
                              └─── BudgetTracker (预算控制)
```

---

## 1. Agent Manager 体系

### 1.1 核心职责

Agent Manager 体系负责智能体的**创建、配置、生命周期管理和能力继承**。

### 1.2 核心组件

#### 1.2.1 LoomApp (应用入口)

**位置**: `loom/__init__.py` (导出), 实际实现在 API 层

**职责**:
- 应用级单例管理（EventBus, Dispatcher, LLM, KnowledgeBase）
- Agent 创建工厂 (`create_agent()`)
- Agent 存储与检索 (`get_agent()`, `list_agents()`)
- 全局工具注册 (`register_tool()`)
- 全局技能注册 (`register_skill()`)

**关键数据结构**:
```python
class LoomApp:
    _agents: dict[str, Agent]           # Agent 实例池
    _tool_registry: ToolRegistry        # 全局工具表
    _skill_registry: SkillRegistry      # 全局技能表
    _skill_activator: SkillActivator    # 技能激活器
    event_bus: EventBus                 # 事件总线
    dispatcher: Dispatcher              # 任务分发器
    knowledge_base: KnowledgeBase       # 知识库
```

**创建 Agent 的流程**:
```python
# 1. 用户调用
agent = app.create_agent(
    agent_id="worker-1",
    config=AgentConfig(enabled_skills={"python-dev"})
)

# 2. LoomApp 内部流程
# 2.1 创建 Agent 实例，注入全局依赖
agent = Agent(
    node_id=agent_id,
    llm_provider=self.llm_provider,
    tool_registry=self._tool_registry,      # 共享
    skill_registry=self._skill_registry,    # 共享
    skill_activator=self._skill_activator,  # 共享
    event_bus=self.event_bus,               # 共享
    knowledge_base=self.knowledge_base,     # 共享
    config=config,                          # 独立
)

# 2.2 存储到 Agent 池
self._agents[agent_id] = agent

# 2.3 返回 Agent 实例
return agent
```

#### 1.2.2 BaseNode (节点基类)

**位置**: `loom/agent/base.py`

**职责**:
- 提供所有节点的基础能力（观测、记忆、生命周期）
- 实现 NodeProtocol 接口
- 管理节点状态和统计信息
- 提供拦截器链支持

**核心能力**:

1. **观测能力** (Observation):
```python
async def publish_thinking(content: str, task_id: str):
    """发布思考过程事件"""

async def publish_tool_call(tool_name: str, tool_args: dict):
    """发布工具调用事件"""

async def publish_tool_result(tool_name: str, result: str):
    """发布工具执行结果事件"""
```

2. **集体记忆能力** (Collective Memory):
```python
def query_collective_memory(
    action_filter: str | None = None,
    node_filter: str | None = None,
    limit: int = 10
) -> list[Task]:
    """查询其他节点发布的事件"""

def query_sibling_insights(task_id: str) -> list[dict]:
    """查询兄弟节点的洞察"""
```

3. **生命周期钩子**:
```python
async def on_start(task: Task):
    """任务开始前的钩子"""

async def on_planning(task: Task, plan: dict) -> bool:
    """规划阶段的钩子（可能需要用户审查）"""

async def on_tool_call_request(task: Task, tool_name: str, tool_args: dict) -> bool:
    """工具调用请求钩子（可能需要用户审查）"""

async def on_complete(task: Task):
    """任务成功完成后的钩子"""

async def on_error(task: Task, error: Exception):
    """任务执行出错后的钩子"""
```

**状态管理**:
```python
class NodeState(Enum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

# 统计信息
stats = {
    "execution_count": 0,
    "success_count": 0,
    "failure_count": 0,
    "total_duration": 0.0,
    "last_execution": None,
}
```

#### 1.2.3 Agent (智能体核心)

**位置**: `loom/agent/core.py`

**职责**:
- 实现四范式工作模式（反思、工具使用、规划、协作）
- 管理 LLM 交互和流式输出
- 执行工具调用和元工具
- 管理子节点创建和记忆同步
- 技能激活和配置继承

**核心属性**:
```python
class Agent(BaseNode):
    # LLM 相关
    llm_provider: LLMProvider
    system_prompt: str                    # 完整系统提示词
    max_iterations: int                   # 最大迭代次数

    # 工具相关
    tools: list[dict]                     # 基础工具列表
    all_tools: list[dict]                 # 完整工具列表（含元工具）
    tool_registry: ToolRegistry           # 工具注册表（共享）
    sandbox_manager: SandboxToolManager   # 沙盒工具管理器

    # 技能相关
    skill_registry: SkillRegistry         # 技能注册表（共享）
    skill_activator: SkillActivator       # 技能激活器（共享）
    config: AgentConfig                   # 配置（可继承）
    _active_skills: set[str]              # 已激活技能（独立）

    # 记忆相关
    memory: LoomMemory                    # L1-L4 分层记忆
    fractal_memory: FractalMemory         # 分形记忆
    context_manager: TaskContextManager   # 上下文管理器

    # 分形相关
    budget_tracker: BudgetTracker         # 预算跟踪器（共享）
    recursive_depth: int                  # 当前递归深度
    available_agents: dict[str, Agent]    # 可委派的 Agent

    # 知识库相关
    knowledge_base: KnowledgeBase         # 知识库提供者
    knowledge_max_items: int              # 查询最大条目数
    knowledge_relevance_threshold: float  # 相关度阈值
```

**系统提示词构建** (`_build_full_system_prompt`):

系统提示词分为三层：
1. **用户提示词** - 业务逻辑和任务特定指令
2. **技能指令** - 激活的 Skill 指令（Form 1 - 知识注入）
3. **框架能力** - 四范式自主能力（始终添加，不可配置）

```python
def _build_full_system_prompt(
    user_prompt: str,
    skill_instructions: list[str] | None = None
) -> str:
    parts = []

    # Layer 1: 用户业务逻辑
    if user_prompt:
        parts.append(user_prompt)

    # Layer 2: 技能指令（Form 1 注入）
    if skill_instructions:
        parts.append("\n\n".join(skill_instructions))

    # Layer 3: 框架能力（ReAct + Planning + Collaboration）
    parts.append(autonomous_capabilities)

    return "\n\n".join(parts)
```

框架能力的核心内容：
```xml
<autonomous_agent>
You are an autonomous agent using ReAct (Reasoning + Acting) as your PRIMARY working method.

<primary_method>
  <react>
    Your DEFAULT approach for ALL tasks:
    1. Think: Analyze the task
    2. Act: Use available tools directly
    3. Observe: See results
    4. Repeat until completion

    ALWAYS try ReAct first. Most tasks can be solved with direct tool use.
  </react>
</primary_method>

<secondary_methods>
  <planning tool="create_plan">
    ONLY use when task genuinely requires 5+ INDEPENDENT steps.
  </planning>

  <collaboration tool="delegate_task">
    Use when need specialized expertise beyond your tools.
  </collaboration>

  <context_query>
    Query historical information when needed:
    - query_l1_memory, query_l2_memory, query_events_by_action
  </context_query>
</secondary_methods>

<decision_framework>
  1. DEFAULT: Use ReAct - directly call tools to solve the task
  2. ONLY if task has 5+ truly independent steps: Consider planning
  3. If executing plan step: Use ReAct, avoid re-planning
</decision_framework>
</autonomous_agent>
```

**Agent 执行流程** (`_execute_impl` - 核心循环):

Agent 的核心理念是 **"Agent is just a for loop"**，通过迭代循环实现 ReAct 模式。

```python
async def _execute_impl(self, task: Task) -> Task:
    """Agent 核心执行循环"""

    # 1. 存储任务到记忆
    self.memory.add_task(task)
    await self._ensure_shared_task_context(task)

    # 2. 加载并激活相关 Skills（Progressive Disclosure）
    task_content = task.parameters.get("content", "")
    activated_skills = await self._load_relevant_skills(task_content)

    # 提取三种形态的激活结果
    injected_instructions = activated_skills.get("injected_instructions", [])
    compiled_tools = activated_skills.get("compiled_tools", [])
    instantiated_nodes = activated_skills.get("instantiated_nodes", [])

    # 3. Agent 循环（最多 max_iterations 次）
    accumulated_messages = []
    final_content = ""

    try:
        for iteration in range(self.max_iterations):
            # 3.1 构建上下文（两层防护）
            # 第一层：过滤 ephemeral 消息
            filtered_messages = self._filter_ephemeral_messages(accumulated_messages)
            # 第二层：智能上下文管理（token 预算）
            messages = await self.context_manager.build_context(task)

            # 3.2 注入 Skill 指令（Form 1 - 仅第一次迭代）
            if injected_instructions and iteration == 0:
                skill_instructions = "\n\n=== Available Skills ===\n\n"
                skill_instructions += "\n\n".join(injected_instructions)
                messages.append({"role": "system", "content": skill_instructions})

            # 3.3 添加累积消息
            if filtered_messages:
                messages.extend(filtered_messages)

            # 3.4 调用 LLM（流式输出）
            full_content = ""
            tool_calls = []

            async for chunk in self.llm_provider.stream_chat(messages, tools=self.all_tools):
                if chunk.type == "text":
                    full_content += chunk.content
                    # 发布思考过程事件（实时观测）
                    await self.publish_thinking(
                        content=chunk.content,
                        task_id=task.task_id,
                        metadata={"iteration": iteration}
                    )
                elif chunk.type == "tool_call_complete":
                    tool_calls.append(chunk.content)

            # 3.5 检查是否有工具调用
            if not tool_calls:
                if self.require_done_tool:
                    # 提醒 LLM 调用 done
                    accumulated_messages.append({
                        "role": "system",
                        "content": "Please call the 'done' tool when you have completed the task."
                    })
                    continue
                else:
                    break  # 直接结束

            # 3.6 执行工具调用
            for tool_call in tool_calls:
                tool_name = tool_call.get("name", "")
                tool_args = tool_call.get("arguments", {})

                # 发布工具调用事件
                await self.publish_tool_call(tool_name, tool_args, task.task_id)

                # 检查是否是 done tool
                if tool_name == "done":
                    await execute_done_tool(tool_args)  # 抛出 TaskComplete

                # 处理元工具
                if tool_name == "create_plan":
                    result = await self._execute_plan(tool_args, task)
                elif tool_name == "delegate_task":
                    result = await self._auto_delegate(tool_args, task)
                else:
                    # 执行普通工具
                    result = await self._execute_single_tool(tool_name, tool_args)

                # 发布工具执行结果事件
                await self.publish_tool_result(tool_name, result, task.task_id)

                # 累积消息
                accumulated_messages.append({"role": "assistant", "content": full_content})
                accumulated_messages.append({
                    "role": "tool",
                    "content": result,
                    "tool_call_id": tool_call.get("id", ""),
                    "tool_name": tool_name
                })

    except TaskComplete as e:
        # 正常完成
        task.status = TaskStatus.COMPLETED
        task.result = {"content": e.message, "completed_explicitly": True}
        await self._self_evaluate(task)
        self.memory.add_task(task)
        await self.memory.promote_tasks_async()
        return task

    # 循环正常结束（未调用 done）
    task.status = TaskStatus.COMPLETED
    task.result = {"content": final_content, "completed_explicitly": False}
    await self._self_evaluate(task)
    self.memory.add_task(task)
    await self.memory.promote_tasks_async()
    return task
```

**关键设计点**:

1. **两层上下文防护**:
   - 第一层：`_filter_ephemeral_messages()` - 过滤大输出工具的旧消息
   - 第二层：`TaskContextManager.build_context()` - 智能 token 预算分配

2. **流式输出与实时观测**:
   - LLM 输出通过 `stream_chat()` 实时流式返回
   - 每个 chunk 立即发布为 `node.thinking` 事件
   - 用户可以实时看到 Agent 的思考过程

3. **工具执行顺序**:
   - `done` tool → 立即完成任务
   - 元工具 (`create_plan`, `delegate_task`) → 特殊处理
   - 普通工具 → 通过 `_execute_single_tool()` 执行

4. **自我评估**:
   - 任务完成后，Agent 用自己的 LLM 评估结果质量
   - 评估维度：confidence, coverage, novelty
   - 评估结果附加到 `task.result["quality_metrics"]`

#### 1.2.4 AgentConfig (配置继承体系)

**位置**: `loom/config/agent.py`

**职责**:
- 定义 Agent 的运行时配置
- 支持配置继承（父→子）
- 支持增量修改（添加/移除）
- 符合分形架构的自相似性

**数据结构**:
```python
@dataclass
class AgentConfig:
    # Skill 配置
    enabled_skills: Set[str] = field(default_factory=set)
    disabled_skills: Set[str] = field(default_factory=set)

    # 工具配置
    extra_tools: Set[str] = field(default_factory=set)
    disabled_tools: Set[str] = field(default_factory=set)

    # 激活模式
    skill_activation_mode: str = "hybrid"  # hybrid, explicit, auto
```

**配置继承机制** (`inherit` 方法):

```python
@classmethod
def inherit(
    cls,
    parent: "AgentConfig",
    add_skills: Set[str] | None = None,
    remove_skills: Set[str] | None = None,
    add_tools: Set[str] | None = None,
    remove_tools: Set[str] | None = None,
) -> "AgentConfig":
    """从父配置继承，支持增量修改"""

    return cls(
        # Skills: 继承 + 添加 - 移除
        enabled_skills=((parent.enabled_skills | add_skills) - remove_skills),
        disabled_skills=parent.disabled_skills | remove_skills,

        # Tools: 继承 + 添加 - 移除
        extra_tools=((parent.extra_tools | add_tools) - remove_tools),
        disabled_tools=parent.disabled_tools | remove_tools,

        # 激活模式继承
        skill_activation_mode=parent.skill_activation_mode,
    )
```

**分形继承规则** (Phase 3: 12.5.3):

在创建子节点时，Agent 遵循以下继承规则：

| 组件 | 继承方式 | 说明 |
|------|---------|------|
| `skill_registry` | **共享** | 所有 Agent 共享同一个技能注册表 |
| `tool_registry` | **共享** | 所有 Agent 共享同一个工具注册表 |
| `event_bus` | **共享** | 所有 Agent 共享同一个事件总线 |
| `sandbox_manager` | **共享** | 父子节点共享沙盒管理器 |
| `config` | **继承** | 子节点继承父节点配置，可增量修改 |
| `_active_skills` | **独立** | 每个 Agent 独立维护已激活技能集合 |
| `fractal_memory` | **独立** | 每个 Agent 有独立的分形记忆实例 |

**使用示例**:

```python
# 1. 创建父 Agent
parent_config = AgentConfig(
    enabled_skills={"python-dev", "testing"},
    extra_tools={"git", "docker"}
)
parent_agent = app.create_agent("parent", config=parent_config)

# 2. 创建子 Agent（继承 + 增量修改）
child_config = AgentConfig.inherit(
    parent=parent_config,
    add_skills={"database-design"},  # 额外启用
    remove_skills={"testing"},       # 禁用某个技能
    add_tools={"postgres"}           # 额外工具
)
# 结果：enabled_skills = {"python-dev", "database-design"}
#      extra_tools = {"git", "docker", "postgres"}

# 3. 在分形委派中自动继承
# Agent 内部调用 _create_child_node() 时自动继承配置
child_agent = await parent_agent._create_child_node(
    subtask=subtask,
    context_hints=[],
    add_skills={"database-design"},  # 可选的增量修改
)
```

### 1.3 Agent Manager 体系总结

**核心流程图**:

```
用户请求
   │
   ▼
LoomApp.create_agent()
   │
   ├─ 注入全局依赖（EventBus, ToolRegistry, SkillRegistry, etc.）
   ├─ 创建 Agent 实例
   ├─ 初始化 LoomMemory（L1-L4）
   ├─ 初始化 FractalMemory
   ├─ 初始化 TaskContextManager
   └─ 存储到 Agent 池
   │
   ▼
Agent.execute_task(task)
   │
   ├─ BaseNode 生命周期钩子（on_start）
   ├─ 加载并激活相关 Skills
   ├─ Agent 核心循环（ReAct）
   │   ├─ 构建上下文（两层防护）
   │   ├─ 调用 LLM（流式输出）
   │   ├─ 执行工具调用
   │   └─ 累积消息
   ├─ 自我评估
   ├─ 记忆升级（L3→L4）
   └─ BaseNode 生命周期钩子（on_complete）
```

**关键设计决策**:

1. **单一 Agent 类** - 所有智能体能力统一到一个 Agent 类，避免类爆炸
2. **分层能力** - BaseNode 提供基础能力，Agent 提供高级能力
3. **配置继承** - 通过 AgentConfig 实现分形架构的配置继承
4. **共享 vs 独立** - 明确定义哪些组件共享，哪些独立
5. **事件驱动** - 所有观测和通信通过 EventBus 实现

---

## 2. Tool Manager 体系

### 2.1 核心职责

Tool Manager 体系负责**工具的注册、发现、执行与安全控制**，包括沙盒隔离、MCP 集成和并行执行优化。

### 2.2 核心组件架构

Tool Manager 体系由三层组成：

1. **ToolRegistry** - 应用级工具注册表（全局单例）
2. **SandboxToolManager** - 沙盒工具管理器（按作用域隔离）
3. **ToolExecutor** - 工具执行引擎（并行/串行优化）

**组件关系图**:
```
ToolRegistry (全局)
    │
    ├─ 注册 Python 函数
    ├─ 转换为 MCP 定义
    └─ 提供查询接口

SandboxToolManager (Agent 级)
    │
    ├─ SANDBOXED 工具（文件操作）
    ├─ SYSTEM 工具（bash, http）
    ├─ MCP 工具（外部服务）
    └─ CONTEXT 工具（记忆查询）

ToolExecutor
    │
    ├─ 判断只读/写入
    ├─ 并行执行只读工具
    └─ 串行执行写入工具
```

#### 2.2.1 ToolRegistry (工具注册表)

**位置**: `loom/tools/registry.py`

**核心数据结构**:
```python
class ToolRegistry:
    _tools: dict[str, Callable]                    # 工具名称 → 可调用对象
    _definitions: dict[str, MCPToolDefinition]     # 工具名称 → MCP 定义
```

**关键方法**:
```python
def register_function(self, func: Callable, name: str | None = None) -> MCPToolDefinition:
    """注册 Python 函数为工具

    流程：
    1. 获取工具名称（默认使用函数名）
    2. 使用 FunctionToMCP 转换器生成 MCP 定义
    3. 存储可调用对象和定义
    """
    tool_name = name or func.__name__
    definition = FunctionToMCP.convert(func, name=tool_name)
    self._tools[tool_name] = func
    self._definitions[tool_name] = definition
    return definition

def get_callable(self, name: str) -> Callable | None:
    """获取工具的可调用对象（用于执行）"""
    return self._tools.get(name)

def get_definition(self, name: str) -> MCPToolDefinition | None:
    """获取工具定义（用于 LLM）"""
    return self._definitions.get(name)
```

**使用场景**:
- LoomApp 启动时注册全局工具
- Agent 执行时通过 `tool_registry.get_callable()` 获取工具函数
- Agent 构建工具列表时通过 `tool_registry.get_definition()` 获取 MCP 定义

#### 2.2.2 SandboxToolManager (沙盒工具管理器)

**位置**: `loom/tools/sandbox_manager.py`

**核心职责**:
- 统一的工具注册和执行中心
- 按作用域隔离工具安全策略
- 自动沙盒化文件操作
- 集成 MCP 服务器

**工具作用域** (`ToolScope`):
```python
class ToolScope(Enum):
    SANDBOXED = "sandboxed"  # 文件操作，受沙盒约束（read_file, write_file, search）
    SYSTEM = "system"        # 系统操作，不受文件系统沙盒约束（bash, http）
    MCP = "mcp"              # 外部 MCP 工具
    CONTEXT = "context"      # 上下文查询工具（query_l1_memory, query_events）
```

**工具包装器** (`ToolWrapper`):
```python
@dataclass
class ToolWrapper:
    name: str
    func: Callable
    definition: MCPToolDefinition
    scope: ToolScope
    metadata: dict[str, Any]
    server_id: str | None = None  # For MCP tools

    async def execute(self, args: dict, sandbox: Sandbox | None = None) -> Any:
        """根据作用域应用相应的安全策略"""
        if self.scope == ToolScope.SANDBOXED and sandbox is not None:
            # 自动注入 sandbox 参数
            return await self._execute_sandboxed(args, sandbox)
        else:
            # 直接执行
            return await self._execute_direct(args)
```

**关键方法**:
```python
class SandboxToolManager:
    sandbox: Sandbox
    event_bus: EventBus | None
    _tools: dict[str, ToolWrapper]
    _mcp_adapter: MCPAdapter | None

    async def register_tool(
        self,
        name: str,
        func: Callable,
        definition: MCPToolDefinition,
        scope: ToolScope = ToolScope.SANDBOXED,
    ) -> None:
        """注册工具到管理器"""
        wrapper = ToolWrapper(name, func, definition, scope)
        self._tools[name] = wrapper
        # 发布工具注册事件
        if self.event_bus:
            await self.event_bus.publish(
                Task(action="tool.registered", parameters={"tool_name": name})
            )

    async def execute_tool(self, name: str, arguments: dict) -> Any:
        """执行工具（自动应用安全策略）"""
        wrapper = self._tools.get(name)
        if not wrapper:
            raise ValueError(f"Tool not found: {name}")

        # 根据作用域执行
        if wrapper.scope == ToolScope.SANDBOXED:
            result = await wrapper.execute(arguments, sandbox=self.sandbox)
        else:
            result = await wrapper.execute(arguments)

        return result
```

**MCP 集成**:
```python
async def register_mcp_server(self, server_id: str, server: Any) -> list[MCPToolDefinition]:
    """注册 MCP 服务器并自动发现工具"""
    if self._mcp_adapter is None:
        self._mcp_adapter = MCPAdapter(event_bus=self.event_bus)

    # 注册服务器
    await self._mcp_adapter.register_server(server_id, server)

    # 发现工具
    mcp_tools = await self._mcp_adapter.discover_tools(server_id)

    # 为每个 MCP 工具创建包装器
    for mcp_tool in mcp_tools:
        async def mcp_func(**kwargs):
            return await self._mcp_adapter.call_tool(mcp_tool.name, kwargs)

        wrapper = ToolWrapper(
            name=mcp_tool.name,
            func=mcp_func,
            definition=mcp_tool,
            scope=ToolScope.MCP,
            server_id=server_id,
        )
        self._tools[mcp_tool.name] = wrapper

    return mcp_tools
```

#### 2.2.3 ToolExecutor (工具执行引擎)

**位置**: `loom/tools/executor.py`

**核心职责**:
- 判断工具是否只读
- 并行执行只读工具（优化性能）
- 串行执行有副作用的工具（保证安全）

**只读工具判断**:
```python
class ToolExecutor:
    read_only_patterns = [
        r"^read_", r"^get_", r"^list_", r"^ls",
        r"^grep", r"^find", r"^search", r"^query",
        r"^fetch", r"^view"
    ]

    def is_read_only(self, tool_name: str) -> bool:
        """通过正则模式判断工具是否只读"""
        for pattern in self.read_only_patterns:
            if re.match(pattern, tool_name, re.IGNORECASE):
                return True
        return False
```

**批量执行策略**:
```python
async def execute_batch(
    self,
    tool_calls: list[dict[str, Any]],
    executor_func: Callable[[str, dict], Coroutine]
) -> list[ToolExecutionResult]:
    """批量执行工具调用

    策略：
    1. 将工具分为只读组和写入组
    2. 只读组内的工具并行执行（asyncio.gather）
    3. 写入工具单独一组，串行执行
    4. 按原始顺序返回结果
    """
    # 1. 分组
    groups = []
    current_group = []
    is_current_read = None

    for idx, call in enumerate(tool_calls):
        is_read = self.is_read_only(call.get("name", ""))

        if is_read:
            # 只读工具：可以合并到当前组
            if current_group and not is_current_read:
                groups.append(current_group)
                current_group = []
            current_group.append((idx, call))
            is_current_read = True
        else:
            # 写入工具：单独一组
            if current_group:
                groups.append(current_group)
                current_group = []
            groups.append([(idx, call)])
            is_current_read = False

    # 2. 执行各组
    results_map = {}
    for group in groups:
        is_read_group = self.is_read_only(group[0][1].get("name", ""))

        if is_read_group and len(group) > 1:
            # 并行执行只读组
            tasks = [self._safe_execute(idx, call, executor_func) for idx, call in group]
            group_results = await asyncio.gather(*tasks)
            for result in group_results:
                results_map[result.index] = result
        else:
            # 串行执行
            for idx, call in group:
                result = await self._safe_execute(idx, call, executor_func)
                results_map[result.index] = result

    # 3. 按原始顺序返回
    return [results_map[i] for i in range(len(tool_calls))]
```

### 2.3 Tool Manager 体系总结

**工具执行流程**:
```
Agent._execute_single_tool(tool_name, tool_args)
    │
    ├─ 检查是否是 done tool → 抛出 TaskComplete
    ├─ 检查是否是动态创建的工具 → DynamicToolExecutor
    ├─ 检查是否是上下文查询工具 → ContextToolExecutor
    ├─ 检查是否在 SandboxToolManager 中 → sandbox_manager.execute_tool()
    └─ 否则从 ToolRegistry 获取 → tool_registry.get_callable()
```

**关键设计决策**:

1. **三层架构** - ToolRegistry（全局）→ SandboxToolManager（Agent 级）→ ToolExecutor（执行优化）
2. **作用域隔离** - 通过 ToolScope 实现不同安全策略
3. **自动沙盒化** - SANDBOXED 工具自动注入 sandbox 参数
4. **MCP 无缝集成** - 通过 MCPAdapter 统一外部工具
5. **并行优化** - 只读工具并行执行，提升性能

---

## 3. Fractal Manager 体系

### 3.1 核心职责

Fractal Manager 体系负责**节点递归组合、统一接口、深度与预算控制、分形记忆作用域**，实现「在有限时间距离下的无限思考」。

### 3.2 核心设计理念

基于**科赫雪花**的分形理念：
- **自相似性** - 父子节点具有相同的能力结构
- **递归组合** - 节点可以无限嵌套，形成树形结构
- **最小必要原则** - 子节点只接收完成任务所需的最小上下文
- **双向流动** - 信息可以从父到子，也可以从子到父

### 3.3 核心组件

#### 3.3.1 FractalMemory (分形记忆)

**位置**: `loom/fractal/memory.py`

**核心职责**:
- 管理不同作用域的记忆（LOCAL, SHARED, INHERITED, GLOBAL）
- 处理父子节点间的记忆共享
- 提供统一的读写接口
- 使用 LoomMemory 作为底层存储

**记忆作用域** (`MemoryScope`):
```python
class MemoryScope(Enum):
    LOCAL = "local"        # 节点私有，不共享
    SHARED = "shared"      # 父子双向共享
    INHERITED = "inherited"  # 从父节点继承（只读）
    GLOBAL = "global"      # 全局共享（所有节点）
```

**访问策略** (`MemoryAccessPolicy`):
```python
ACCESS_POLICIES = {
    MemoryScope.LOCAL: MemoryAccessPolicy(
        readable=True, writable=True,
        propagate_up=False, propagate_down=False
    ),
    MemoryScope.SHARED: MemoryAccessPolicy(
        readable=True, writable=True,
        propagate_up=True, propagate_down=True
    ),
    MemoryScope.INHERITED: MemoryAccessPolicy(
        readable=True, writable=False,  # 只读
        propagate_up=False, propagate_down=True
    ),
    MemoryScope.GLOBAL: MemoryAccessPolicy(
        readable=True, writable=True,
        propagate_up=True, propagate_down=True
    ),
}
```

**记忆条目** (`MemoryEntry`):
```python
@dataclass
class MemoryEntry:
    id: str                      # 唯一标识
    content: Any                 # 记忆内容
    scope: MemoryScope           # 作用域
    version: int = 1             # 版本号（用于冲突检测）
    created_by: str = ""         # 创建者节点ID
    updated_by: str = ""         # 最后更新者节点ID
    parent_version: int | None = None  # 父版本号（用于追踪）
    metadata: dict[str, Any] = field(default_factory=dict)
```

**关键方法**:
```python
class FractalMemory:
    node_id: str
    parent_memory: Optional["FractalMemory"]
    base_memory: Optional["LoomMemory"]
    _memory_by_scope: dict[MemoryScope, dict[str, MemoryEntry]]

    async def write(self, entry_id: str, content: Any, scope: MemoryScope = MemoryScope.LOCAL) -> MemoryEntry:
        """写入记忆"""
        # 检查写权限
        policy = ACCESS_POLICIES[scope]
        if not policy.writable:
            raise PermissionError(f"Scope {scope} is read-only")

        # 如果已存在，更新并递增版本
        existing = self._memory_by_scope[scope].get(entry_id)
        if existing:
            existing.version += 1
            existing.content = content
            existing.updated_by = self.node_id
            return existing

        # 创建新记忆条目
        entry = MemoryEntry(
            id=entry_id,
            content=content,
            scope=scope,
            created_by=self.node_id,
            updated_by=self.node_id,
        )
        self._memory_by_scope[scope][entry_id] = entry
        return entry

    async def read(self, entry_id: str, search_scopes: list[MemoryScope] | None = None) -> MemoryEntry | None:
        """读取记忆（按优先级搜索：LOCAL > SHARED > INHERITED > GLOBAL）"""
        if search_scopes is None:
            search_scopes = list(MemoryScope)

        # 在本地作用域搜索
        for scope in search_scopes:
            if entry_id in self._memory_by_scope[scope]:
                return self._memory_by_scope[scope][entry_id]

        # 如果是 INHERITED 作用域，尝试从父节点读取
        if MemoryScope.INHERITED in search_scopes and self.parent_memory:
            parent_entry = await self.parent_memory.read(
                entry_id,
                search_scopes=[MemoryScope.SHARED, MemoryScope.GLOBAL, MemoryScope.INHERITED]
            )
            if parent_entry:
                # 创建只读副本并缓存
                inherited_entry = MemoryEntry(
                    id=parent_entry.id,
                    content=parent_entry.content,
                    scope=MemoryScope.INHERITED,
                    version=parent_entry.version,
                    created_by=parent_entry.created_by,
                    updated_by=parent_entry.updated_by,
                    parent_version=parent_entry.version,
                )
                self._memory_by_scope[MemoryScope.INHERITED][entry_id] = inherited_entry
                return inherited_entry

        return None
```

**使用场景**:
```python
# 父节点写入 SHARED 记忆
await parent_memory.write("task:goal", "Analyze codebase", scope=MemoryScope.SHARED)

# 子节点可以读取（自动继承）
goal = await child_memory.read("task:goal", search_scopes=[MemoryScope.INHERITED])

# 子节点写入 SHARED 记忆（向上传播）
await child_memory.write("finding:bug", "Found memory leak", scope=MemoryScope.SHARED)

# 父节点可以读取子节点的发现
bug = await parent_memory.read("finding:bug", search_scopes=[MemoryScope.SHARED])
```

