# Crew - 多 Agent 协作系统

**版本**: v0.1.9
**最后更新**: 2024-12-15

Crew 是 Loom 的多 Agent 协作框架，支持构建复杂的多 Agent 系统。

---

## 目录

1. [概述](#概述)
2. [快速开始](#快速开始)
3. [协作模式](#协作模式)
4. [创建 Crew](#创建-crew)
5. [核心特性](#核心特性)
6. [CrewRole 使用](#crewrole-使用)
7. [高级功能](#高级功能)
8. [最佳实践](#最佳实践)
9. [示例](#示例)

---

## 概述

### 什么是 Crew？

Crew 是一个多 Agent 协作框架，允许多个 Agent 协同工作完成复杂任务。

**核心特性**：
- 🔄 **四种协作模式**: Sequential、Parallel、Coordinated、Routed
- 🧠 **智能协调**: 自动任务分解和工作量缩放
- 🧭 **智能路由**: 基于能力匹配自动选择 Agent
- ⚡ **并行执行**: Agent 和工具级并行
- 📦 **上下文管理**: Artifact 存储大型结果
- 🛡️ **容错机制**: 四层错误恢复
- 📊 **可观测性**: 完整的决策追踪
- 🎯 **预设配置**: 生产就绪的配置模板

### 适用场景

- 研究 + 分析工作流
- 复杂决策系统
- 内容生成流水线
- 多步骤任务编排
- 需要专家协作的场景

---

## 快速开始

### 最简示例 - Sequential 模式

```python
import asyncio
import loom
from loom.builtin.llms import UnifiedLLM
from loom.patterns import Crew
from loom.core.message import Message

async def main():
    llm = UnifiedLLM(provider="openai", api_key="your-key")

    # 创建 Agents
    researcher = loom.agent(
        name="researcher",
        llm=llm,
        system_prompt="你是研究员，负责收集信息"
    )

    writer = loom.agent(
        name="writer",
        llm=llm,
        system_prompt="你是撰写员，负责整理成文章"
    )

    # 创建 Crew（顺序执行）
    crew = Crew(
        agents=[researcher, writer],
        mode="sequential"  # researcher → writer
    )

    # 执行任务
    result = await crew.run(Message(
        role="user",
        content="写一篇关于 AI Agent 的文章"
    ))
    print(result.content)

asyncio.run(main())
```

**输出**: writer 基于 researcher 的结果撰写的文章

---

## 协作模式

Crew 支持四种协作模式：

### 1. Sequential（顺序执行）

Agent 按顺序执行，后一个 Agent 接收前一个 Agent 的输出。

```
任务 → Agent1 → Agent2 → Agent3 → 结果
```

**适用场景**: 有明确流水线的任务（研究→分析→撰写）

**文件位置**: `loom/patterns/crew.py`

```python
crew = Crew(
    agents=[researcher, analyst, writer],
    mode="sequential"
)
```

### 2. Parallel（并行执行）

所有 Agent 同时执行相同任务，结果可聚合。

```
       ┌→ Agent1 →┐
任务 → ┼→ Agent2 →┼→ 聚合 → 结果
       └→ Agent3 →┘
```

**适用场景**: 需要多角度分析、投票机制

```python
crew = Crew(
    agents=[expert1, expert2, expert3],
    mode="parallel",
    aggregator=lambda results: "\n\n".join([r.content for r in results])
)
```

### 3. Coordinated（智能协调）

协调器 Agent 智能分配任务给其他 Agent。

```
任务 → Coordinator → [动态选择] → Agent1/Agent2/Agent3 → 结果
```

**适用场景**: 复杂任务需要智能决策、动态调度

```python
crew = Crew(
    agents=[expert1, expert2, expert3],
    mode="coordinated",
    coordinator=coordinator_agent  # 必需
)
```

### 4. Routed（智能路由）**v0.1.7+**

基于 Agent 能力自动路由任务。

```
任务 → Router → [能力匹配] → 最佳 Agent → 结果
```

**适用场景**: 根据任务类型自动选择最合适的 Agent

**文件位置**: `loom/patterns/routing.py`

```python
from loom.patterns import Crew, Router, AgentCapability, RoutingStrategy

# 定义 Agent 能力
capabilities = [
    AgentCapability(
        agent=researcher,
        capabilities=["research", "information_gathering"],
        complexity_level=ComplexityLevel.MEDIUM
    ),
    AgentCapability(
        agent=coder,
        capabilities=["coding", "debugging"],
        complexity_level=ComplexityLevel.COMPLEX
    ),
]

# 创建路由器
router = Router(
    agents_capabilities=capabilities,
    strategy=RoutingStrategy.AUTO  # AUTO/RULE_BASED/LLM_BASED
)

# 创建 Crew
crew = Crew(
    agents=[researcher, coder, writer],
    mode="routed",
    router=router
)
```

**路由策略**：
- `AUTO`: 自动选择最佳策略
- `RULE_BASED`: 基于规则匹配
- `LLM_BASED`: 使用 LLM 智能选择
- `CAPABILITY_BASED`: 基于能力分数
- `LOAD_BALANCED`: 负载均衡
- `RANDOM`: 随机选择（测试用）
- `ROUND_ROBIN`: 轮询

---

## 创建 Crew

### 方式 1: 直接使用 Agents（简单模式）

```python
import loom
from loom.patterns import Crew

# 创建 Agents
agent1 = loom.agent(name="agent1", llm=llm)
agent2 = loom.agent(name="agent2", llm=llm)

# 创建 Crew
crew = Crew(
    agents=[agent1, agent2],
    mode="sequential"
)
```

### 方式 2: 使用 CrewRole（灵活模式）

```python
from loom.patterns import Crew, CrewRole
from loom.builtin.tools import tool

# 定义工具
@tool(name="search")
async def search(query: str) -> str:
    return f"搜索结果: {query}"

# 定义角色
researcher_role = CrewRole(
    name="researcher",
    goal="收集和研究信息",
    tools=[search],
    system_prompt="你是专业研究员"
)

writer_role = CrewRole(
    name="writer",
    goal="撰写优质内容",
    system_prompt="你是资深撰稿人"
)

# 创建 Crew（Crew 会自动从 roles 创建 agents）
crew = Crew(
    roles=[researcher_role, writer_role],
    llm=llm,  # 为所有角色提供默认 LLM
    mode="sequential"
)
```

**CrewRole 的优势**:
- 每个角色可以有独立的工具
- 可以配置独立的 memory
- 可以设置知识库
- 更清晰的角色职责定义

---

## 核心特性

### 1. 智能协调器

自动分析任务复杂度并智能分配工作量：

```python
from loom.patterns import Crew, SmartCoordinator, ComplexityAnalyzer

# 创建智能协调器
coordinator = SmartCoordinator(llm=llm)
analyzer = ComplexityAnalyzer()

crew = Crew(
    agents=[agent1, agent2, agent3],
    mode="coordinated",
    coordinator=coordinator,
    use_smart_coordinator=True,       # 启用智能协调
    complexity_analyzer=analyzer      # 复杂度分析
)

# Crew 会自动：
# - 分析任务复杂度（SIMPLE/MEDIUM/COMPLEX）
# - 决定需要多少 agents
# - 智能分解子任务
# - 检测重复任务并去重
```

**复杂度级别**:
- `SIMPLE`: 1个 agent（90% 资源节省）
- `MEDIUM`: 2-4个 agents
- `COMPLEX`: 5+个 agents

### 2. 智能路由系统

基于 Agent 能力自动路由任务：

**文件位置**: `loom/patterns/routing.py`

```python
from loom.patterns import Router, AgentCapability, ComplexityLevel

# 定义能力
capabilities = [
    AgentCapability(
        agent=researcher,
        agent_type=AgentType.SIMPLE,
        capabilities=["research", "analysis"],
        has_tools=True,
        complexity_level=ComplexityLevel.MEDIUM,
        tags=["information", "data"],
        priority=10,
        avg_response_time=2.5,
        success_rate=0.95
    ),
]

router = Router(
    agents_capabilities=capabilities,
    strategy=RoutingStrategy.AUTO
)

# 自动选择最佳 Agent
best_agent = await router.route(task_message)
```

### 3. 并行执行

Agent 级和工具级双重并行：

```python
from loom.patterns import Crew, ParallelConfig

parallel_config = ParallelConfig(
    max_concurrent_agents=3,  # 最多3个agent并行
    max_concurrent_tools=5,   # 最多5个工具并行
    timeout=300               # 超时时间
)

crew = Crew(
    agents=[agent1, agent2, agent3, agent4],
    mode="parallel",
    enable_parallel=True,
    parallel_config=parallel_config
)
```

**性能提升**: 多任务场景速度提升 **90%**

### 4. Artifact 存储

自动管理大型结果，避免上下文堵塞：

```python
from loom.patterns import Crew, ArtifactStore

artifact_store = ArtifactStore(path="./artifacts")

crew = Crew(
    agents=[...],
    mode="sequential",
    artifact_store=artifact_store  # 启用 artifact 存储
)

# Crew 会自动：
# - 检测大型输出（> 1000 tokens）
# - 保存到文件
# - 在上下文中使用摘要
# - 支持 10x 更长的任务
```

### 5. 容错机制

四层自动错误恢复：

```python
from loom.patterns import Crew, RecoveryConfig

recovery_config = RecoveryConfig(
    max_retries=3,              # Level 1: 最多重试3次
    retry_delay=1.0,            # 指数退避延迟
    enable_fallback=True,       # Level 3: 启用降级
    enable_skip=True            # Level 4: 允许跳过
)

crew = Crew(
    agents=[...],
    enable_error_recovery=True,
    recovery_config=recovery_config
)
```

**恢复策略**:
- Level 1: 自动重试（指数退避）
- Level 2: 通知协调器重新分配
- Level 3: 降级到简化任务
- Level 4: 跳过失败任务继续

**成功率提升**: 60% → 95%

### 6. 完整可观测性

追踪所有决策和执行：

```python
from loom.patterns import Crew, CrewTracer, CrewEvaluator

tracer = CrewTracer()
evaluator = CrewEvaluator(llm=llm)

crew = Crew(
    agents=[...],
    enable_tracing=True,
    tracer=tracer,
    evaluator=evaluator
)

# 执行后查看
decisions = crew.get_decision_log()  # 决策日志
metrics = crew.get_evaluation()       # LLM 评估
```

---

## CrewRole 使用

### CrewRole 完整示例

```python
from loom.patterns import CrewRole
from loom.builtin.tools import tool
from loom.builtin.memory import InMemoryMemory

# 定义工具
@tool(name="search")
async def search(query: str) -> str:
    return f"搜索: {query}"

# 定义角色
researcher = CrewRole(
    name="researcher",
    goal="深入研究主题，收集全面信息",
    description="专业的研究员，擅长信息收集和事实核查",
    tools=[search],
    memory=InMemoryMemory(),
    system_prompt="""
你是一位专业研究员。

职责：
- 深入研究给定主题
- 收集准确、全面的信息
- 使用可靠来源
- 标注来源出处

方法：
1. 理解研究目标
2. 使用搜索工具收集信息
3. 验证信息准确性
4. 整理研究结果
    """,
    max_iterations=15,
    allow_delegation=False,
    verbose=True
)

# 使用
crew = Crew(
    roles=[researcher],
    llm=llm,
    mode="sequential"
)
```

### CrewRole 参数详解

```python
CrewRole(
    # 基本信息
    name="role_name",              # 角色名称（必需）
    goal="role_goal",              # 角色目标（必需）
    description="详细描述",         # 角色描述（可选）

    # Agent 配置
    system_prompt="系统提示",       # 自定义提示（可选）
    llm=custom_llm,                # 独立 LLM（可选）

    # 工具配置
    tools=[tool1, tool2],          # 角色专用工具

    # 记忆配置
    memory=InMemoryMemory(),       # 记忆系统
    memory_config={...},           # 记忆配置

    # 知识库
    knowledge_base={               # 角色知识
        "domain": "AI",
        "expertise": ["ML", "NLP"]
    },

    # 高级配置
    max_iterations=10,             # 最大迭代次数
    allow_delegation=False,        # 是否允许委托
    verbose=False,                 # 是否详细输出

    # 元数据
    metadata={"team": "research"}  # 自定义元数据
)
```

---

## 高级功能

### 1. 自定义聚合函数

在 parallel 模式中自定义结果聚合：

```python
def custom_aggregator(results: List[Message]) -> Message:
    """自定义聚合逻辑"""
    # 投票机制
    from collections import Counter
    contents = [r.content for r in results]
    vote = Counter(contents)
    winner = vote.most_common(1)[0][0]

    final_content = f"多数选择: {winner}\n\n详细结果:\n" + "\n---\n".join(contents)

    return Message(role="assistant", content=final_content)

crew = Crew(
    agents=[expert1, expert2, expert3],
    mode="parallel",
    aggregator=custom_aggregator
)
```

### 2. 流式输出

实时查看 Crew 执行过程：

```python
async def stream_crew():
    crew = Crew(agents=[...], mode="sequential")

    # 流式执行
    async for event in crew.run_stream(Message(role="user", content="任务")):
        if event.type == "agent_start":
            print(f"🚀 {event.agent_name} 开始")
        elif event.type == "agent_end":
            print(f"✅ {event.agent_name} 完成")
        elif event.type == "result":
            print(f"📊 结果: {event.content}")
```

---

## 最佳实践

### 1. 合理选择模式

```python
# ✅ Sequential - 有明确流水线
crew = Crew(
    agents=[researcher, analyst, writer],
    mode="sequential"
)

# ✅ Parallel - 需要多角度或投票
crew = Crew(
    agents=[expert1, expert2, expert3],
    mode="parallel"
)

# ✅ Coordinated - 复杂任务需要智能调度
crew = Crew(
    agents=[多个专家],
    mode="coordinated",
    coordinator=smart_coordinator
)

# ✅ Routed - 基于能力自动选择
crew = Crew(
    agents=[researcher, coder, writer],
    mode="routed",
    router=router
)
```

### 2. 明确角色职责

```python
# ✅ 每个角色有明确职责
researcher = CrewRole(
    name="researcher",
    goal="收集信息",  # 明确目标
    tools=[search],   # 专用工具
)

writer = CrewRole(
    name="writer",
    goal="撰写内容",  # 不同目标
    tools=[],         # 不需要工具
)

# ❌ 角色职责不清
agent = CrewRole(
    name="agent",
    goal="做所有事情",  # 太泛泛
)
```

### 3. 启用容错机制

```python
# ✅ 生产环境必须启用容错
crew = Crew(
    agents=[...],
    enable_error_recovery=True,
    recovery_config=RecoveryConfig(max_retries=3)
)

# ❌ 生产环境不启用容错
crew = Crew(agents=[...])  # 一个失败全部失败
```

---

## 示例

### 示例 1: 研究 + 分析 + 撰写

```python
import asyncio
import loom
from loom.builtin.llms import UnifiedLLM
from loom.builtin.tools import tool
from loom.patterns import Crew, CrewRole
from loom.core.message import Message

@tool(name="web_search")
async def web_search(query: str) -> str:
    """模拟网络搜索"""
    return f"关于 {query} 的搜索结果..."

async def main():
    llm = UnifiedLLM(provider="openai", api_key="...")

    # 定义角色
    researcher = CrewRole(
        name="researcher",
        goal="深入研究 AI Agent 主题",
        tools=[web_search],
        system_prompt="你是研究员，收集全面信息"
    )

    analyst = CrewRole(
        name="analyst",
        goal="分析研究结果，提取关键洞察",
        system_prompt="你是分析师，提取洞察和趋势"
    )

    writer = CrewRole(
        name="writer",
        goal="撰写高质量文章",
        system_prompt="你是撰稿人，写作专业文章"
    )

    # 创建 Crew
    crew = Crew(
        roles=[researcher, analyst, writer],
        llm=llm,
        mode="sequential"
    )

    # 执行
    result = await crew.run(Message(
        role="user",
        content="写一篇关于 AI Agent 的深度文章"
    ))
    print(result.content)

asyncio.run(main())
```

### 示例 2: 智能路由

```python
from loom.patterns import Crew, Router, AgentCapability, RoutingStrategy
from loom.patterns.routing import AgentType, ComplexityLevel

async def routing_example():
    llm = UnifiedLLM(provider="openai", api_key="...")

    # 创建专业 Agents
    researcher = loom.agent(name="researcher", llm=llm)
    coder = loom.agent(name="coder", llm=llm)
    writer = loom.agent(name="writer", llm=llm)

    # 定义能力
    capabilities = [
        AgentCapability(
            agent=researcher,
            agent_type=AgentType.SIMPLE,
            capabilities=["research", "analysis", "data_gathering"],
            complexity_level=ComplexityLevel.MEDIUM
        ),
        AgentCapability(
            agent=coder,
            agent_type=AgentType.REACT,
            capabilities=["coding", "debugging", "testing"],
            complexity_level=ComplexityLevel.COMPLEX
        ),
        AgentCapability(
            agent=writer,
            agent_type=AgentType.SIMPLE,
            capabilities=["writing", "editing", "content_creation"],
            complexity_level=ComplexityLevel.SIMPLE
        ),
    ]

    # 创建路由器
    router = Router(
        agents_capabilities=capabilities,
        strategy=RoutingStrategy.AUTO
    )

    # 创建 Crew
    crew = Crew(
        agents=[researcher, coder, writer],
        mode="routed",
        router=router
    )

    # 执行不同类型的任务
    tasks = [
        "研究 Python 最佳实践",
        "编写一个排序算法",
        "写一篇技术博客"
    ]

    for task in tasks:
        result = await crew.run(Message(role="user", content=task))
        print(f"任务: {task}\n结果: {result.content}\n")

asyncio.run(routing_example())
```

---

## 相关资源

- [Crew 智能路由指南](../advanced/CREW_ROUTING_GUIDE.md)
- [递归控制模式指南](../advanced/RECURSIVE_CONTROL_GUIDE.md)
- [架构设计](../../architecture/overview.md)
- [Patterns API 参考](../../api/patterns.md)

---

## 下一步

- 学习 [Skills 系统](../skills/overview.md)
- 了解 [架构设计](../../architecture/overview.md)
- 查看 [API 参考](../../api/patterns.md)

---

**构建强大的多 Agent 系统！** 🚀
