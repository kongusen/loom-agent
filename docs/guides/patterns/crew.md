# Crew - 多 Agent 协作系统

**版本**: v0.1.6
**最后更新**: 2025-12-14

Crew 是 Loom 的多 Agent 协作框架，支持构建复杂的多 Agent 系统。

---

## 目录

1. [概述](#概述)
2. [快速开始](#快速开始)
3. [协作模式](#协作模式)
4. [创建 Crew](#创建-crew)
5. [v0.1.6 新特性](#v016-新特性)
6. [预设配置](#预设配置)
7. [CrewRole 使用](#crewrole-使用)
8. [高级功能](#高级功能)
9. [最佳实践](#最佳实践)
10. [示例](#示例)

---

## 概述

### 什么是 Crew？

Crew 是一个多 Agent 协作框架，允许多个 Agent 协同工作完成复杂任务。

**核心特性**：
- 🔄 **三种协作模式**: Sequential、Parallel、Coordinated
- 🧠 **智能协调** (v0.1.6): 自动任务分解和工作量缩放
- ⚡ **并行执行** (v0.1.6): Agent 和工具级并行
- 📦 **上下文管理** (v0.1.6): Artifact 存储大型结果
- 🛡️ **容错机制** (v0.1.6): 四层错误恢复
- 📊 **可观测性** (v0.1.6): 完整的决策追踪
- 🎯 **预设配置** (v0.1.6): 生产就绪的配置模板

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
from loom.builtin import OpenAILLM
from loom.patterns import Crew

async def main():
    llm = OpenAILLM(api_key="your-key")

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
    result = await crew.run("写一篇关于 AI Agent 的文章")
    print(result)

asyncio.run(main())
```

**输出**: writer 基于 researcher 的结果撰写的文章

---

## 协作模式

Crew 支持三种协作模式：

### 1. Sequential（顺序执行）

Agent 按顺序执行，后一个 Agent 接收前一个 Agent 的输出。

```
任务 → Agent1 → Agent2 → Agent3 → 结果
```

**适用场景**: 有明确流水线的任务（研究→分析→撰写）

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
    aggregator=lambda results: "\n\n".join(results)  # 可选聚合
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
from loom.builtin import tool

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

### 方式 3: 使用预设配置（推荐）

```python
from loom.patterns import Crew, CrewPresets

# 使用生产级预设
config = CrewPresets.production_ready(
    agents=[researcher, analyst, writer],
    coordinator=coordinator,
    llm=llm
)

crew = Crew.from_config(config, agents=[researcher, analyst, writer])
```

---

## v0.1.6 新特性

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

### 2. 并行执行

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

### 3. Artifact 存储

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

### 4. 容错机制

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

### 5. Checkpoint 系统

支持中断恢复：

```python
from loom.patterns import Crew, CheckpointManager

checkpoint_mgr = CheckpointManager(
    path="./checkpoints",
    enabled=True
)

crew = Crew(
    agents=[...],
    enable_checkpoint=True,
    checkpoint_manager=checkpoint_mgr
)

# 任务中断后可恢复
result = await crew.resume_from_checkpoint("checkpoint_id")
```

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

## 预设配置

v0.1.6 提供生产就绪的预设配置：

### 1. production_ready

完整的生产级配置：

```python
from loom.patterns import CrewPresets

config = CrewPresets.production_ready(
    agents=[...],
    coordinator=coordinator,
    llm=llm
)

# 包含：
# - 智能协调
# - 并行执行
# - Artifact 存储
# - 错误恢复
# - Checkpoint
# - 可观测性
```

### 2. fast_prototype

快速原型配置（最小功能）：

```python
config = CrewPresets.fast_prototype(agents=[...], llm=llm)

# 仅基础功能，适合快速测试
```

### 3. high_reliability

高可靠性配置（最强容错）：

```python
config = CrewPresets.high_reliability(
    agents=[...],
    coordinator=coordinator,
    llm=llm
)

# 包含：
# - 最大重试次数
# - 完整错误恢复
# - Checkpoint 启用
# - 详细追踪
```

---

## CrewRole 使用

### CrewRole 完整示例

```python
from loom.patterns import CrewRole
from loom.builtin import tool, InMemoryMemory

# 定义工具
@tool(name="search")
async def search(query: str) -> str:
    return f"搜索: {query}"

@tool(name="analyze")
async def analyze(data: str) -> str:
    return f"分析: {data}"

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

analyst = CrewRole(
    name="analyst",
    goal="分析数据，提取洞察",
    tools=[analyze],
    system_prompt="你是数据分析专家"
)

# 使用
crew = Crew(
    roles=[researcher, analyst],
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
def custom_aggregator(results: List[str]) -> str:
    """自定义聚合逻辑"""
    # 投票机制
    from collections import Counter
    vote = Counter(results)
    winner = vote.most_common(1)[0][0]
    return f"多数选择: {winner}\n\n详细结果:\n" + "\n---\n".join(results)

crew = Crew(
    agents=[expert1, expert2, expert3],
    mode="parallel",
    aggregator=custom_aggregator
)
```

### 2. 动态 Agent 选择

在 coordinated 模式中动态选择 agents：

```python
class SmartCoordinator(SimpleAgent):
    """智能协调器"""

    async def select_agents(self, task: str, available_agents: List[BaseAgent]):
        """根据任务选择合适的 agents"""
        # 分析任务
        analysis = await self.analyze_task(task)

        # 选择最合适的 agents
        selected = []
        if "research" in analysis:
            selected.append(researcher)
        if "code" in analysis:
            selected.append(coder)

        return selected

crew = Crew(
    agents=[researcher, coder, writer, analyst],
    mode="coordinated",
    coordinator=SmartCoordinator(llm=llm, ...)
)
```

### 3. 流式输出

实时查看 Crew 执行过程：

```python
async def stream_crew():
    crew = Crew(agents=[...], mode="sequential")

    # 流式执行
    async for event in crew.run_stream("任务"):
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
```

### 2. 使用预设配置

```python
# ✅ 生产环境使用 production_ready
config = CrewPresets.production_ready(...)
crew = Crew.from_config(config, agents=[...])

# ❌ 不要手动配置所有参数（除非必要）
crew = Crew(
    agents=[...],
    enable_parallel=True,
    parallel_config=...,  # 太繁琐
    enable_error_recovery=True,
    ...
)
```

### 3. 明确角色职责

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

### 4. 启用容错机制

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

### 5. 使用 Artifact 存储

```python
# ✅ 长任务启用 artifact 存储
crew = Crew(
    agents=[...],
    artifact_store=ArtifactStore(path="./artifacts")
)

# ❌ 大型结果直接传递（会堵塞上下文）
crew = Crew(agents=[...])  # 可能因上下文过大失败
```

---

## 示例

### 示例 1: 研究 + 分析 + 撰写

```python
import asyncio
import loom
from loom.builtin import OpenAILLM, tool
from loom.patterns import Crew, CrewRole

@tool(name="web_search")
async def web_search(query: str) -> str:
    """模拟网络搜索"""
    return f"关于 {query} 的搜索结果..."

async def main():
    llm = OpenAILLM(api_key="...")

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
    result = await crew.run("写一篇关于 AI Agent 的深度文章")
    print(result)

asyncio.run(main())
```

### 示例 2: 多专家投票系统

```python
async def voting_system():
    llm = OpenAILLM(api_key="...")

    # 创建多个专家
    expert1 = loom.agent(name="expert1", llm=llm, system_prompt="你是 AI 专家")
    expert2 = loom.agent(name="expert2", llm=llm, system_prompt="你是 ML 专家")
    expert3 = loom.agent(name="expert3", llm=llm, system_prompt="你是 NLP 专家")

    # 投票聚合函数
    def vote_aggregator(results: List[str]) -> str:
        from collections import Counter
        # 简化：选择多数
        votes = Counter(results)
        winner = votes.most_common(1)[0]
        return f"多数意见（{winner[1]}/3票）: {winner[0]}"

    # 创建投票 Crew
    crew = Crew(
        agents=[expert1, expert2, expert3],
        mode="parallel",
        aggregator=vote_aggregator
    )

    # 执行投票
    question = "GPT-4 和 Claude 哪个更适合代码生成？"
    result = await crew.run(question)
    print(result)

asyncio.run(voting_system())
```

### 示例 3: 生产级配置

```python
from loom.patterns import Crew, CrewPresets

async def production_crew():
    llm = OpenAILLM(api_key="...")

    # 创建 agents
    researcher = loom.agent(name="researcher", llm=llm, ...)
    analyst = loom.agent(name="analyst", llm=llm, ...)
    writer = loom.agent(name="writer", llm=llm, ...)
    coordinator = loom.agent(name="coordinator", llm=llm, ...)

    # 使用生产级预设
    config = CrewPresets.production_ready(
        agents=[researcher, analyst, writer],
        coordinator=coordinator,
        llm=llm
    )

    # 创建 Crew
    crew = Crew.from_config(
        config,
        agents=[researcher, analyst, writer]
    )

    # 执行
    result = await crew.run("复杂的生产任务")

    # 查看统计
    print("决策日志:", crew.get_decision_log())
    print("评估结果:", crew.get_evaluation())

asyncio.run(production_crew())
```

---

## 相关资源

- [SimpleAgent 指南](../agents/simple-agent.md)
- [工具开发](../tools/development.md)
- [Patterns API 参考](../../api/patterns.md)
- [示例代码](../../examples/)

---

## 下一步

- 学习 [Skills 系统](../skills/overview.md)
- 了解 [架构设计](../../architecture/overview.md)
- 查看 [API 参考](../../api/patterns.md)

---

**构建强大的多 Agent 系统！** 🚀
