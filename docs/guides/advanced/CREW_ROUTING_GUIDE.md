# Crew 智能路由系统使用指南

## 概述

Loom Agent v0.1.7 引入了**智能路由系统（Intelligent Routing）**，为 Crew 多 Agent 协作提供了第四种工作模式：**Routed Mode（路由模式）**。

### 设计理念

- **递归是单 Agent 自身的能力**：ReflectionLoop、TreeOfThoughts、PlanExecutor 等递归控制模式用于增强单个 Agent 的推理能力
- **Crew 是控制这些 Agent 组合的能力**：Crew 负责编排和协调多个 Agent（包括使用递归控制的 Agent）
- **Router 提供智能任务分配**：根据任务特征和 Agent 能力，智能路由到最合适的 Agent

### 四种 Crew 模式

| 模式 | 描述 | 适用场景 |
|------|------|----------|
| **Sequential** | 顺序执行（A → B → C） | 有明确流程的任务 |
| **Parallel** | 并行执行（A + B + C） | 独立子任务 |
| **Coordinated** | 协调器智能分配 | 复杂任务分解 |
| **Routed** ✨ | 路由器智能分配 | 根据任务特征选择 Agent |

---

## 快速开始

### 基础路由示例

```python
import loom
from loom.patterns import Crew, Router, RoutingStrategy, AgentCapability, AgentType, ComplexityLevel

# 1. 创建不同能力的 Agents
simple_agent = loom.agent(
    name="simple",
    llm=llm
)

research_agent = loom.agent(
    name="researcher",
    llm=llm,
    tools=[search_tool],
    react_mode=True  # ReAct 推理
)

# ReflectionLoop 包装的 Agent（高质量输出）
from loom.patterns import ReflectionLoop
writer = loom.agent(name="writer", llm=llm)
writer_with_reflection = ReflectionLoop(agent=writer, max_iterations=3)

# 2. 创建 Crew（routed 模式）
crew = Crew(
    agents=[simple_agent, research_agent, writer_with_reflection],
    mode="routed",  # 启用路由模式
    routing_strategy=RoutingStrategy.AUTO  # 自动路由
)

# 3. 执行任务 - 自动路由
result = await crew.run("写一篇关于 AI 的文章")
# Router 自动分析：
# - 任务复杂度：medium
# - 所需能力：writing
# - 选择：writer_with_reflection（有 Reflection 能力，质量高）
```

---

## 核心组件

### 1. AgentCapability - Agent 能力描述

描述一个 Agent 的能力特征，用于路由决策。

```python
from loom.patterns import AgentCapability, AgentType, ComplexityLevel

capability = AgentCapability(
    # 基本信息
    agent_type=AgentType.REACT,
    capabilities=["research", "web_search"],

    # 能力特征
    has_tools=True,
    has_recursive_control=False,
    complexity_level=ComplexityLevel.MEDIUM,

    # 标签和元数据
    tags=["research", "information_gathering"],
    description="Research agent with web search capability",
    priority=5,  # 优先级（越高越优先）
)
```

#### AgentType 类型

```python
from loom.patterns import AgentType

AgentType.SIMPLE             # 简单对话
AgentType.REACT              # ReAct 推理
AgentType.REFLECTION         # 反思循环
AgentType.TREE_OF_THOUGHTS   # 思维树
AgentType.PLAN_EXECUTOR      # 规划执行
AgentType.CUSTOM             # 自定义
```

#### ComplexityLevel 复杂度

```python
from loom.patterns import ComplexityLevel

ComplexityLevel.SIMPLE   # 简单任务（1-2步）
ComplexityLevel.MEDIUM   # 中等任务（3-5步）
ComplexityLevel.COMPLEX  # 复杂任务（6+步）
ComplexityLevel.EXPERT   # 专家级任务（需要深度推理）
```

---

### 2. TaskClassifier - 任务分类器

分析任务特征，为路由提供决策依据。

```python
from loom.patterns import TaskClassifier

# 创建分类器
classifier = TaskClassifier()

# 分类任务
characteristics = classifier.classify("研究并分析 AI 的发展趋势")

print(f"复杂度: {characteristics.complexity}")  # ComplexityLevel.COMPLEX
print(f"估计步骤: {characteristics.estimated_steps}")  # 3-5
print(f"所需能力: {characteristics.required_capabilities}")  # ['research', 'analysis']
print(f"需要工具: {characteristics.requires_tools}")  # True
print(f"需要推理: {characteristics.requires_reasoning}")  # True
```

#### TaskCharacteristics 属性

```python
class TaskCharacteristics:
    complexity: ComplexityLevel          # 复杂度
    estimated_steps: int                 # 估计步骤数
    required_capabilities: List[str]     # 所需能力
    required_tags: List[str]             # 所需标签
    task_type: str                       # 任务类型
    requires_tools: bool                 # 是否需要工具
    requires_reasoning: bool             # 是否需要推理
    requires_planning: bool              # 是否需要规划
```

---

### 3. Router - 智能路由器

将任务路由到最合适的 Agent。

```python
from loom.patterns import Router, RoutingStrategy

# 创建路由器
router = Router(
    strategy=RoutingStrategy.AUTO,  # 路由策略
    classifier=TaskClassifier(),     # 任务分类器
)

# 注册 Agents
router.register_agent(
    agent=simple_agent,
    capability=AgentCapability(
        agent_type=AgentType.SIMPLE,
        capabilities=["qa", "chat"],
        complexity_level=ComplexityLevel.SIMPLE
    )
)

router.register_agent(
    agent=research_agent,
    capability=AgentCapability(
        agent_type=AgentType.REACT,
        capabilities=["research", "web_search"],
        has_tools=True,
        complexity_level=ComplexityLevel.MEDIUM
    )
)

# 路由任务
result = await router.route("研究 AI 的发展趋势")

print(f"选择的 Agent: {result.agent.name}")
print(f"Agent 类型: {result.capability.agent_type}")
print(f"匹配分数: {result.score}")
print(f"选择原因: {result.reason}")
```

---

## 路由策略

Router 支持 7 种路由策略：

### 1. AUTO - 自动路由（推荐）

基于任务分析和能力匹配，自动选择最合适的 Agent。

```python
router = Router(strategy=RoutingStrategy.AUTO)

# 自动分析：
# - 任务复杂度
# - 所需能力
# - Agent 能力匹配度
# - 负载均衡
# - 优先级
```

**评分机制**：
- 基础分：复杂度匹配
- 加分：能力匹配、工具匹配、推理匹配
- 调整：优先级、负载均衡

### 2. RULE_BASED - 基于规则

根据预定义规则选择 Agent。

```python
router = Router(
    strategy=RoutingStrategy.RULE_BASED,
    rules={
        "研究": research_agent,
        "写作": writer_agent,
        "分析": analyst_agent,
    }
)

# 如果任务包含"研究"，路由到 research_agent
# 如果任务包含"写作"，路由到 writer_agent
```

### 3. LLM_BASED - 基于 LLM 决策

使用 LLM 分析任务并选择 Agent（更准确但更慢）。

```python
router = Router(
    strategy=RoutingStrategy.LLM_BASED,
    llm=coordinator_llm  # 用于决策的 LLM
)

# LLM 会分析：
# - 任务详细需求
# - 各 Agent 的能力
# - 选择最合适的 Agent
```

### 4. CAPABILITY_MATCH - 能力匹配

选择第一个匹配所需能力的 Agent。

```python
router = Router(strategy=RoutingStrategy.CAPABILITY_MATCH)

# 快速匹配，找到第一个能做的 Agent 即可
```

### 5. ROUND_ROBIN - 轮询

按顺序轮流分配任务给 Agents。

```python
router = Router(strategy=RoutingStrategy.ROUND_ROBIN)

# 负载均衡，平均分配任务
```

### 6. PRIORITY - 优先级

选择优先级最高的 Agent。

```python
router = Router(strategy=RoutingStrategy.PRIORITY)

# 总是选择 priority 最高的 Agent
```

### 7. LOAD_BALANCE - 负载均衡

选择当前负载最低的 Agent。

```python
router = Router(strategy=RoutingStrategy.LOAD_BALANCE)

# 避免某个 Agent 过载
```

---

## 在 Crew 中使用路由

### 方式 1：自动创建 Router

```python
crew = Crew(
    agents=[agent1, agent2, agent3],
    mode="routed",
    routing_strategy=RoutingStrategy.AUTO
)

# Crew 会自动：
# 1. 创建 Router
# 2. 注册所有 Agents
# 3. 推断每个 Agent 的能力
```

### 方式 2：提供预配置的 Router

```python
# 手动创建和配置 Router
router = Router(strategy=RoutingStrategy.AUTO)

router.register_agent(
    agent=simple_agent,
    capability=AgentCapability(
        agent_type=AgentType.SIMPLE,
        capabilities=["qa"],
        complexity_level=ComplexityLevel.SIMPLE,
        priority=1
    )
)

router.register_agent(
    agent=expert_agent,
    capability=AgentCapability(
        agent_type=AgentType.TREE_OF_THOUGHTS,
        capabilities=["research", "analysis", "planning"],
        has_recursive_control=True,
        complexity_level=ComplexityLevel.EXPERT,
        priority=10
    )
)

# 使用预配置的 Router
crew = Crew(
    agents=[simple_agent, expert_agent],
    mode="routed",
    router=router  # 使用自定义 Router
)
```

### 方式 3：显式指定 Agent 能力

```python
from loom.patterns import AgentCapability

agent_capabilities = {
    simple_agent: AgentCapability(
        agent_type=AgentType.SIMPLE,
        capabilities=["qa", "chat"],
        complexity_level=ComplexityLevel.SIMPLE
    ),
    research_agent: AgentCapability(
        agent_type=AgentType.REACT,
        capabilities=["research", "web_search"],
        has_tools=True,
        complexity_level=ComplexityLevel.MEDIUM
    ),
}

crew = Crew(
    agents=[simple_agent, research_agent],
    mode="routed",
    agent_capabilities=agent_capabilities
)
```

---

## 实战示例

### 示例 1：混合使用递归控制和路由

```python
import loom
from loom.patterns import Crew, ReflectionLoop, TreeOfThoughts, AgentCapability, AgentType, ComplexityLevel

# Agent 1: 简单对话
simple_agent = loom.agent(name="simple", llm=llm)

# Agent 2: ReAct 研究
research_agent = loom.agent(
    name="researcher",
    llm=llm,
    tools=[search_tool],
    react_mode=True
)

# Agent 3: Reflection 写作
writer = loom.agent(name="writer", llm=llm)
writer_with_reflection = ReflectionLoop(agent=writer, max_iterations=3)

# Agent 4: ToT 专家分析
analyst = loom.agent(name="analyst", llm=llm)
analyst_with_tot = TreeOfThoughts(analyst=analyst, branching_factor=3)

# 创建 Crew
crew = Crew(
    agents=[simple_agent, research_agent, writer_with_reflection, analyst_with_tot],
    mode="routed",
    routing_strategy=RoutingStrategy.AUTO
)

# 测试不同任务
print("=== 简单问答 ===")
result1 = await crew.run("今天天气怎么样？")
# → simple_agent（最快，适合简单任务）

print("\n=== 研究任务 ===")
result2 = await crew.run("研究最新的 AI 技术进展")
# → research_agent（有 ReAct + 工具）

print("\n=== 写作任务 ===")
result3 = await crew.run("写一篇关于 AI 伦理的文章")
# → writer_with_reflection（有 Reflection，质量高）

print("\n=== 复杂分析 ===")
result4 = await crew.run("分析全球气候变化的影响并提出解决方案")
# → analyst_with_tot（有 ToT，深度推理）
```

### 示例 2：基于规则的路由

```python
from loom.patterns import RoutingStrategy

# 定义规则
router = Router(
    strategy=RoutingStrategy.RULE_BASED,
    rules={
        "研究": research_agent,
        "写作": writer_with_reflection,
        "分析": analyst_with_tot,
        "问答": simple_agent,
    }
)

crew = Crew(
    agents=[simple_agent, research_agent, writer_with_reflection, analyst_with_tot],
    mode="routed",
    router=router
)

# 规则匹配
result = await crew.run("研究并分析最新技术")
# 匹配"研究"→ research_agent

result = await crew.run("写一篇技术报告")
# 匹配"写作"→ writer_with_reflection
```

### 示例 3：优先级路由

```python
from loom.patterns import AgentCapability

# 设置优先级
agent_capabilities = {
    simple_agent: AgentCapability(
        capabilities=["qa"],
        priority=1  # 低优先级
    ),
    research_agent: AgentCapability(
        capabilities=["research"],
        priority=5  # 中优先级
    ),
    expert_agent: AgentCapability(
        capabilities=["expert_analysis"],
        priority=10  # 高优先级
    ),
}

crew = Crew(
    agents=[simple_agent, research_agent, expert_agent],
    mode="routed",
    routing_strategy=RoutingStrategy.PRIORITY,
    agent_capabilities=agent_capabilities
)

# 总是选择 expert_agent（优先级最高）
```

### 示例 4：负载均衡路由

```python
from loom.patterns import RoutingStrategy

crew = Crew(
    agents=[agent1, agent2, agent3],
    mode="routed",
    routing_strategy=RoutingStrategy.LOAD_BALANCE
)

# 10 个任务平均分配
tasks = [f"任务 {i+1}" for i in range(10)]
results = []

for task in tasks:
    result = await crew.run(task)
    results.append(result)

# 查看负载统计
stats = crew.router.get_stats()
print(f"负载分布: {stats['load_stats']}")
# 输出: {'simple': 3, 'medium': 3, 'complex': 4}
```

---

## Router API 详解

### Router.register_agent()

注册 Agent 到路由器。

```python
router.register_agent(
    agent=my_agent,
    capability=AgentCapability(...)  # 可选，会自动推断
)
```

**自动推断能力**：
- 检查 `agent.tools` → `has_tools=True`
- 检查 `agent.react_mode` → `agent_type=REACT`
- 检查类名（ReflectionLoop, TreeOfThoughts 等）→ `has_recursive_control=True`

### Router.route()

路由任务到合适的 Agent。

```python
result = await router.route("任务描述")

# RoutingResult 属性
result.agent            # 选择的 Agent
result.capability       # Agent 能力
result.score            # 匹配分数（0-1）
result.reason           # 选择原因
```

### Router.get_stats()

获取路由统计信息。

```python
stats = router.get_stats()

# 统计信息
stats['total_agents']   # 总 Agent 数
stats['strategy']       # 路由策略
stats['load_stats']     # 负载分布
```

---

## TaskClassifier API 详解

### 基于规则的分类（默认）

```python
classifier = TaskClassifier()
characteristics = classifier.classify("研究 AI")
```

**关键词检测**：
- capabilities: research, writing, analysis, coding, calculation, translation, qa
- requires_tools: 搜索, 查找, 获取, 调用
- requires_reasoning: 分析, 推理, 思考, 判断
- requires_planning: 计划, 规划, 步骤, 流程

### 基于 LLM 的分类（更准确）

```python
classifier = TaskClassifier(
    llm=llm_agent,
    use_llm=True
)

characteristics = classifier.classify("复杂任务")
# LLM 会提供更准确的分类
```

---

## 最佳实践

### 1. 何时使用 Routed 模式

**推荐使用**：
```python
# ✅ 有多种类型的任务
crew = Crew(agents=[...], mode="routed")

# ✅ 不确定哪个 Agent 最合适
crew = Crew(agents=[...], mode="routed")

# ✅ 需要自适应选择
crew = Crew(agents=[...], mode="routed")
```

**不推荐使用**：
```python
# ❌ 任务流程固定 → 用 sequential
crew = Crew(agents=[...], mode="sequential")

# ❌ 需要所有 Agent 参与 → 用 parallel
crew = Crew(agents=[...], mode="parallel")

# ❌ 需要复杂任务分解 → 用 coordinated
crew = Crew(agents=[...], mode="coordinated")
```

### 2. 选择合适的路由策略

```python
# 简单场景 → ROUND_ROBIN 或 CAPABILITY_MATCH
router = Router(strategy=RoutingStrategy.ROUND_ROBIN)

# 一般场景 → AUTO（推荐）
router = Router(strategy=RoutingStrategy.AUTO)

# 复杂场景 → LLM_BASED
router = Router(strategy=RoutingStrategy.LLM_BASED, llm=llm)

# 特定规则 → RULE_BASED
router = Router(strategy=RoutingStrategy.RULE_BASED, rules={...})
```

### 3. 合理设置 Agent 能力

```python
# 明确能力特征
capability = AgentCapability(
    agent_type=AgentType.REACT,
    capabilities=["research", "analysis"],  # 明确列出
    has_tools=True,
    complexity_level=ComplexityLevel.MEDIUM,
    priority=5,  # 设置优先级
    description="Research agent with web search"  # 添加描述
)
```

### 4. 监控路由决策

```python
# 启用追踪
crew = Crew(
    agents=[...],
    mode="routed",
    enable_tracing=True
)

result = await crew.run("任务")

# 查看路由决策
print(f"选择的 Agent: {result.metadata['routing']['selected_agent']}")
print(f"Agent 类型: {result.metadata['routing']['agent_type']}")
print(f"匹配分数: {result.metadata['routing']['score']}")
print(f"原因: {result.metadata['routing']['reason']}")
```

---

## 与其他模式对比

| 特性 | Sequential | Parallel | Coordinated | **Routed** |
|------|-----------|----------|-------------|------------|
| **执行方式** | 顺序 | 并行 | 协调分解 | **智能路由** |
| **任务分配** | 固定顺序 | 所有参与 | Coordinator 分配 | **Router 匹配** |
| **适用场景** | 流程固定 | 独立子任务 | 复杂任务分解 | **任务类型多样** |
| **Agent 选择** | 全部 | 全部 | 部分 | **单个（最合适）** |
| **灵活性** | 低 | 低 | 中 | **高** |
| **效率** | 中 | 高 | 中 | **高** |
| **成本** | 高 | 高 | 高 | **低** |

---

## 性能对比

### 任务分配效率

| 策略 | 分析时间 | 准确度 | 适用场景 |
|------|---------|--------|----------|
| **AUTO** | 快（< 1ms） | 高（80-90%） | 一般场景 |
| **RULE_BASED** | 极快（< 0.1ms） | 高（如果规则正确） | 明确规则 |
| **LLM_BASED** | 慢（1-3s） | 很高（90-95%） | 复杂决策 |
| **CAPABILITY_MATCH** | 快（< 0.5ms） | 中（70-80%） | 简单匹配 |

### 成本对比

```python
# Sequential: 所有 Agent 都执行 = 高成本
crew_sequential = Crew(agents=[a1, a2, a3], mode="sequential")
# 成本 = cost(a1) + cost(a2) + cost(a3)

# Routed: 只有 1 个 Agent 执行 = 低成本
crew_routed = Crew(agents=[a1, a2, a3], mode="routed")
# 成本 = cost(selected_agent)
```

---

## 故障排除

### 问题 1：路由选择不准确

**原因**：Agent 能力描述不准确

**解决方案**：
```python
# 显式指定 Agent 能力
agent_capabilities = {
    agent1: AgentCapability(
        capabilities=["research", "analysis"],  # 明确列出
        complexity_level=ComplexityLevel.MEDIUM
    ),
}

crew = Crew(agents=[agent1], mode="routed", agent_capabilities=agent_capabilities)
```

### 问题 2：总是选择同一个 Agent

**原因**：优先级设置问题或策略选择问题

**解决方案**：
```python
# 方案 1：使用 AUTO 策略（考虑负载均衡）
crew = Crew(agents=[...], mode="routed", routing_strategy=RoutingStrategy.AUTO)

# 方案 2：使用 LOAD_BALANCE 策略
crew = Crew(agents=[...], mode="routed", routing_strategy=RoutingStrategy.LOAD_BALANCE)

# 方案 3：调整优先级
agent_capabilities = {
    agent1: AgentCapability(priority=5),
    agent2: AgentCapability(priority=5),  # 相同优先级
}
```

### 问题 3：路由器未初始化

**原因**：在非 routed 模式下尝试使用 router

**解决方案**：
```python
# 确保 mode="routed"
crew = Crew(
    agents=[...],
    mode="routed",  # 必需！
    routing_strategy=RoutingStrategy.AUTO
)
```

---

## 总结

✅ **Routed 模式特性**：
- 智能任务分配到最合适的 Agent
- 支持 7 种路由策略
- 自动推断 Agent 能力
- 降低成本（只执行必要的 Agent）
- 提高效率（选择最合适的 Agent）

✅ **与递归控制无缝集成**：
- Crew 可以路由到使用 ReflectionLoop 的 Agent
- Crew 可以路由到使用 TreeOfThoughts 的 Agent
- Crew 可以路由到使用 PlanExecutor 的 Agent
- Router 自动识别递归控制能力

✅ **生产就绪**：
- 完善的错误处理
- 可观测性支持（Tracer）
- 性能监控（负载统计）
- 灵活的配置选项

---

**版本**: v0.1.9 
**日期**: 2025-12-15
**参考**: Andrew Ng - Agentic Design Patterns

**相关文档**：
- [RECURSIVE_CONTROL_GUIDE.md](RECURSIVE_CONTROL_GUIDE.md) - 递归控制模式
- [REACT_MODE_GUIDE.md](REACT_MODE_GUIDE.md) - ReAct 模式
