# 执行策略 (Execution Strategy)

## 定义

**执行策略**定义组合节点如何协调子节点的执行。

## 可用策略

### 1. 并行策略 (ParallelStrategy)

所有子节点并行执行：

```python
from loom.fractal.strategies import ParallelStrategy

team = CompositeNode(
    children=[agent1, agent2, agent3],
    strategy=ParallelStrategy()
)

# 所有 agent 同时执行
results = await team.execute_task(task)
```

**适用场景**:
- 独立任务
- 需要加速
- 无依赖关系

---

### 2. 顺序策略 (SequentialStrategy)

按顺序执行子节点：

```python
from loom.fractal.strategies import SequentialStrategy

pipeline = CompositeNode(
    children=[agent1, agent2, agent3],
    strategy=SequentialStrategy()
)

# agent1 → agent2 → agent3
results = await pipeline.execute_task(task)
```

**适用场景**:
- 流水线任务
- 有依赖关系
- 需要传递中间结果

---

### 3. 选择策略 (SelectStrategy)

根据条件选择一个子节点执行：

```python
from loom.fractal.strategies import SelectStrategy

router = CompositeNode(
    children=[coder, writer, analyst],
    strategy=SelectStrategy(
        selector=lambda task: task.metadata.get("role")
    )
)

# 根据 task.role 选择执行哪个 agent
await router.execute_task(Task(metadata={"role": "coder"}))
```

**适用场景**:
- 智能路由
- 专业分工
- 条件分支

## 自定义策略

```python
from loom.fractal.strategies import ExecutionStrategy

class CustomStrategy(ExecutionStrategy):
    async def execute(
        self,
        children: list[Node],
        task: Task
    ) -> list[Task]:
        # 自定义执行逻辑
        results = []
        for child in children:
            result = await child.execute_task(task)
            results.append(result)
            if some_condition(result):
                break  # 提前终止
        return results
```

## 相关概念

- → [组合节点](Composite-Node)
- → [分形架构](Fractal-Architecture)

## 代码位置

- `loom/fractal/strategies.py`

## 反向链接

被引用于: [组合节点](Composite-Node) | [工作流](Workflow)
