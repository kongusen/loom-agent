# 组合节点 (Composite Node)

## 定义

**组合节点**是将多个子节点组合为一个虚拟节点的组件，对外表现为单一节点。

## 核心特性

### 1. 接口一致性

```python
# 单个 Agent
agent = Agent(node_id="assistant")

# 组合节点
team = CompositeNode(
    node_id="team",
    children=[agent1, agent2, agent3]
)

# 对调用者完全相同
await agent.execute_task(task)
await team.execute_task(task)
```

### 2. 执行策略

```python
from loom.fractal.strategies import (
    ParallelStrategy,
    SequentialStrategy,
    SelectStrategy
)

# 并行执行
team = CompositeNode(
    children=[a, b, c],
    strategy=ParallelStrategy()
)

# 顺序执行
pipeline = CompositeNode(
    children=[a, b, c],
    strategy=SequentialStrategy()
)

# 选择执行
router = CompositeNode(
    children=[a, b, c],
    strategy=SelectStrategy(
        selector=lambda task: task.metadata.get("target")
    )
)
```

### 3. 记忆继承

子节点自动继承父节点的共享记忆：

```python
parent = CompositeNode(
    node_id="parent",
    memory=parent_memory  # SHARED/GLOBAL 记忆
)

child = Agent(
    node_id="child",
    memory=child_memory  # 自动继承 parent 的 SHARED/GLOBAL
)
```

## 使用场景

### 场景 1: 研究小组

```python
research_team = CompositeNode(
    node_id="research_team",
    children=[
        Agent(node_id="researcher"),
        Agent(node_id="writer"),
        Agent(node_id="editor")
    ],
    strategy=SequentialStrategy()  # 研究员→撰稿人→编辑
)
```

### 场景 2: 并行处理

```python
parallel_team = CompositeNode(
    node_id="parallel_team",
    children=[
        Agent(node_id="worker1"),
        Agent(node_id="worker2"),
        Agent(node_id="worker3")
    ],
    strategy=ParallelStrategy()  # 并行执行
)
```

## 相关概念

- → [分形架构](Fractal-Architecture)
- → [执行策略](Execution-Strategy)

## 代码位置

- `loom/fractal/composite.py`
- `loom/fractal/strategies.py`

## 反向链接

被引用于: [分形架构](Fractal-Architecture) | [工作流](Workflow)
