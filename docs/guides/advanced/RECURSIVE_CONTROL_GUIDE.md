# 递归控制模式使用指南

## 概述

基于**吴恩达的 Agent 四大范式**，Loom 实现了完善的递归控制模式，为 Agent 提供高级推理能力。

### 吴恩达 Agent 四大范式

1. **Reflection（反思）** - ✅ 已实现：`ReflectionLoop`
2. **Tool Use（工具使用）** - ✅ 已实现：`loom.agent(tools=[...])`
3. **Planning（规划）** - ✅ 已实现：`TreeOfThoughts`, `PlanExecutor`
4. **Multi-Agent（多智能体）** - ✅ 已实现：`Crew`

---

## 快速开始

```python
import loom
from loom.patterns import (
    ReflectionLoop,      # 反思循环
    TreeOfThoughts,      # 思维树
    PlanExecutor,        # 规划-执行
    SelfConsistency,     # 自洽性检查
)

# 创建 Agent
agent = loom.agent(
    name="assistant",
    llm="openai",
    api_key="sk-..."
)
```

---

## 1. Reflection（反思循环）

Agent 自我评估和改进输出，通过多次迭代优化结果。

### 原理

```
生成响应 → 评估质量 → 改进响应 → 重复 → 最终答案
```

### 使用示例

```python
from loom import Message
from loom.patterns import ReflectionLoop

# 创建反思循环
reflection = ReflectionLoop(
    agent=agent,
    max_iterations=3,           # 最多3次迭代
    improvement_threshold=0.8   # 达到0.8分即可停止
)

# 执行
message = Message(role="user", content="Write a professional email about...")
result = await reflection.run(message)

# 查看迭代历史
for iteration in reflection.iterations_history:
    print(f"Iteration {iteration['iteration']}: Score {iteration['score']:.2f}")
    print(f"Response: {iteration['response'][:100]}...\n")
```

### 自定义评估器

```python
async def custom_evaluator(response: str) -> float:
    """自定义评估逻辑"""
    # 检查长度
    if len(response) < 100:
        return 0.3
    # 检查关键词
    keywords = ["professional", "regards", "sincerely"]
    score = sum(1 for kw in keywords if kw in response.lower()) / len(keywords)
    return score

reflection = ReflectionLoop(
    agent=agent,
    max_iterations=5,
    evaluator=custom_evaluator  # 使用自定义评估器
)
```

### 适用场景

- ✅ 需要高质量输出的任务（写作、总结）
- ✅ 可以量化质量的场景
- ✅ 有明确改进方向的任务

---

## 2. Tree of Thoughts（思维树）

探索多条推理路径，评估和选择最佳路径。

### 原理

```
        问题
       /  |  \
      思1 思2 思3
     / |   |   | \
   ...评估...选择...
```

### 使用示例

```python
from loom.patterns import TreeOfThoughts

# 创建思维树
tot = TreeOfThoughts(
    agent=agent,
    branching_factor=3,           # 每个节点3个分支
    max_depth=5,                  # 最大深度5
    selection_strategy="best_first"  # 策略：best_first, beam_search, dfs
)

# 执行
message = Message(role="user", content="How can we solve climate change?")
result = await tot.run(message)

# 查看探索的节点
print(f"Total explored nodes: {len(tot.explored_nodes)}")
for node in tot.explored_nodes[:5]:
    print(f"Thought: {node.content}")
    print(f"Score: {node.score:.2f}")
    print(f"Depth: {node.depth}\n")
```

### 选择策略

**1. Best-First Search（最佳优先）**
```python
tot = TreeOfThoughts(agent=agent, selection_strategy="best_first")
# 特点：贪心，快速，可能陷入局部最优
```

**2. Beam Search（束搜索）**
```python
tot = TreeOfThoughts(agent=agent, selection_strategy="beam_search")
# 特点：平衡，保持多个候选路径
```

**3. Depth-First Search（深度优先）**
```python
tot = TreeOfThoughts(agent=agent, selection_strategy="dfs")
# 特点：彻底，探索完整路径，耗时长
```

### 自定义评估器

```python
async def problem_solving_evaluator(thought: str) -> float:
    """评估思维步骤的质量"""
    # 分析思维步骤
    if "because" in thought.lower():  # 有因果推理
        score = 0.7
    elif "therefore" in thought.lower():  # 有逻辑结论
        score = 0.8
    else:
        score = 0.5
    return score

tot = TreeOfThoughts(
    agent=agent,
    evaluator=problem_solving_evaluator
)
```

### 适用场景

- ✅ 复杂问题求解
- ✅ 需要探索多种方案
- ✅ 创造性任务（头脑风暴）
- ✅ 战略规划

---

## 3. Plan-and-Execute（规划-执行）

先制定完整计划，再逐步执行。

### 原理

```
任务 → 制定计划 → 执行步骤1 → 执行步骤2 → ... → 汇总结果
            ↓                                    ↑
         失败? → 重新规划 ────────────────────────┘
```

### 使用示例

```python
from loom.patterns import PlanExecutor

# 创建规划执行器
executor = PlanExecutor(
    agent=agent,
    allow_replan=True,    # 允许重新规划
    max_replans=2         # 最多重新规划2次
)

# 执行
message = Message(role="user", content="Research and write a report on quantum computing")
result = await executor.run(message)

# 查看计划和执行结果
print("Plan:")
for i, step in enumerate(executor.current_plan.steps):
    print(f"{i+1}. {step}")

print("\nExecution Results:")
for result in executor.execution_results:
    status = "✓" if result.success else "✗"
    print(f"{status} {result.step}")
    print(f"   {result.result[:100]}...\n")
```

### 高级用法：预定义计划

```python
from loom.patterns import Plan

# 手动创建计划
plan = Plan(steps=[
    "Step 1: Gather requirements",
    "Step 2: Design architecture",
    "Step 3: Implement core features",
    "Step 4: Test and validate",
    "Step 5: Deploy to production"
])

executor = PlanExecutor(agent=agent)
executor.current_plan = plan  # 使用预定义计划

result = await executor.run(message)
```

### 适用场景

- ✅ 多步骤任务
- ✅ 需要系统化方法的场景
- ✅ 有明确流程的任务
- ✅ 需要容错和重试的场景

---

## 4. Self-Consistency（自洽性检查）

生成多个候选答案，通过投票选择最佳答案。

### 原理

```
问题 → 生成答案1
     → 生成答案2
     → 生成答案3
     → 生成答案4
     → 生成答案5
     ↓
   投票/一致性检查 → 最佳答案
```

### 使用示例

```python
from loom.patterns import SelfConsistency

# 创建自洽性检查
consistency = SelfConsistency(
    agent=agent,
    num_samples=5,              # 生成5个样本
    selection_method="vote"     # 方法：vote 或 similarity
)

# 执行
message = Message(role="user", content="What is 25 × 36?")
result = await consistency.run(message)

# 查看所有样本
print("Generated samples:")
for i, sample in enumerate(consistency.samples):
    print(f"Sample {i+1}: {sample}")
```

### 选择方法

**1. 投票（Vote）**
```python
consistency = SelfConsistency(agent=agent, selection_method="vote")
# 使用 Agent 判断哪个答案最可靠
```

**2. 相似度（Similarity）**
```python
consistency = SelfConsistency(agent=agent, selection_method="similarity")
# 选择最接近平均值的答案
```

### 适用场景

- ✅ 需要高置信度的答案
- ✅ 数学、逻辑问题
- ✅ 事实性问题
- ✅ 多答案场景（选择题）

---

## 5. 组合使用

将多种模式组合使用，发挥更强大的能力。

### 示例 1：Reflection + Planning

```python
# 先规划，再反思改进
executor = PlanExecutor(agent=agent)
initial_result = await executor.run(message)

# 对结果进行反思改进
reflection = ReflectionLoop(agent=agent, max_iterations=2)
final_result = await reflection.run(initial_result)
```

### 示例 2：ToT + Self-Consistency

```python
# 用思维树探索方案，用自洽性验证
tot = TreeOfThoughts(agent=agent, branching_factor=3, max_depth=3)
tot_result = await tot.run(message)

# 验证ToT的结果
consistency = SelfConsistency(agent=agent, num_samples=5)
verified_result = await consistency.run(tot_result)
```

### 示例 3：Multi-Agent + Recursive Control

```python
from loom.patterns import Crew

# 研究员：使用思维树探索
researcher = loom.agent(name="researcher", llm="openai", api_key="...")
tot = TreeOfThoughts(agent=researcher)

# 撰写员：使用反思改进
writer = loom.agent(name="writer", llm="deepseek", api_key="...")
reflection = ReflectionLoop(agent=writer)

# 组合在 Crew 中
async def research_and_write(task: str):
    # 1. 研究（使用ToT）
    research_msg = Message(role="user", content=f"Research: {task}")
    research_result = await tot.run(research_msg)

    # 2. 撰写（使用Reflection）
    write_msg = Message(role="user", content=f"Write based on: {research_result.content}")
    final_result = await reflection.run(write_msg)

    return final_result

result = await research_and_write("The future of AI")
```

---

## 与 ReAct 模式的关系

| 模式 | 层级 | 特点 |
|------|------|------|
| **Direct** | 基础 | 直接响应 |
| **ReAct** | 中级 | 推理+工具使用（已通过 `react_mode` 实现） |
| **Reflection** | 高级 | 自我改进（递归控制） |
| **ToT** | 高级 | 探索多路径（递归控制） |
| **Plan-Execute** | 高级 | 系统化执行（递归控制） |

### ReAct 模式（已实现）

```python
# ReAct: 推理+行动
agent = loom.agent(
    name="researcher",
    llm="openai",
    api_key="...",
    tools=[search_tool],
    react_mode=True  # 启用 ReAct
)
```

### 递归控制模式（新增）

```python
# Reflection: 反思改进
reflection = ReflectionLoop(agent=agent)
result = await reflection.run(message)

# ToT: 思维树探索
tot = TreeOfThoughts(agent=agent)
result = await tot.run(message)

# Plan-Execute: 规划执行
executor = PlanExecutor(agent=agent)
result = await executor.run(message)
```

---

## 最佳实践

### 1. 选择合适的模式

```python
# 简单任务 → Direct
agent = loom.agent(...)

# 需要工具 → ReAct
agent = loom.agent(..., react_mode=True)

# 需要高质量 → Reflection
reflection = ReflectionLoop(agent=agent)

# 复杂问题 → ToT
tot = TreeOfThoughts(agent=agent)

# 多步骤任务 → Plan-Execute
executor = PlanExecutor(agent=agent)

# 需要验证 → Self-Consistency
consistency = SelfConsistency(agent=agent)
```

### 2. 控制成本

```python
# 限制迭代次数
reflection = ReflectionLoop(agent=agent, max_iterations=2)  # 降低成本

# 减少分支因子
tot = TreeOfThoughts(agent=agent, branching_factor=2)  # 降低探索成本

# 减少样本数
consistency = SelfConsistency(agent=agent, num_samples=3)  # 降低验证成本
```

### 3. 监控和调试

```python
# 查看中间过程
reflection = ReflectionLoop(agent=agent)
result = await reflection.run(message)

# 检查迭代历史
for iteration in reflection.iterations_history:
    print(f"Iteration {iteration['iteration']}: {iteration['score']}")

# 查看ToT探索的节点
tot = TreeOfThoughts(agent=agent)
result = await tot.run(message)
print(f"Explored {len(tot.explored_nodes)} nodes")

# 查看执行计划
executor = PlanExecutor(agent=agent)
result = await executor.run(message)
for step in executor.current_plan.steps:
    print(f"- {step}")
```

---

## 性能对比

| 模式 | 成本 | 速度 | 质量 | 适用场景 |
|------|------|------|------|---------|
| **Direct** | ⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | 简单任务 |
| **ReAct** | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | 工具使用 |
| **Reflection** | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | 高质量输出 |
| **ToT** | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | 复杂问题 |
| **Plan-Execute** | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | 多步骤任务 |
| **Self-Consistency** | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | 验证答案 |

---

## 总结

✅ **四大范式完整实现**：
- Reflection（反思）- `ReflectionLoop`
- Tool Use（工具使用）- `loom.agent(tools=...)`
- Planning（规划）- `TreeOfThoughts`, `PlanExecutor`
- Multi-Agent（多智能体）- `Crew`

✅ **灵活组合**：可以自由组合不同模式

✅ **易于扩展**：可以自定义评估器和策略

✅ **生产就绪**：完善的错误处理和监控

---

**版本**: v0.1.9 
**日期**: 2025-12-15
**参考**: 吴恩达 - Agentic Design Patterns
