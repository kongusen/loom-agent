# 分形递归 (Fractal Recursion)

## 定义

**分形递归**是指任意层级的节点组合，在行为上与单个节点完全一致的特性。

## 核心思想

分形(Fractal)是一种"自相似"的结构：局部与整体相似。在 Loom 中，这意味着：

- 1个 Agent 是一个节点
- 100个 Agent 组成的团队也是一个节点
- 团队之团队还是一个节点

无论组合多深，接口始终一致。

## 数学基础

分形递归满足递归关系：

```
f(1) = Agent
f(n) = CompositeNode(f(n-1), ...)
```

其中 f(n) 表示 n 层组合后的节点，仍然是一个节点。

## 示例

```python
# 0层组合：单个 Agent
agent = Agent(node_id="assistant")

# 1层组合：团队
team = CompositeNode(
    node_id="team",
    children=[agent]
)

# 2层组合：部门
dept = CompositeNode(
    node_id="dept",
    children=[team]
)

# 所有都可以用相同方式调用
await agent.execute_task(task)
await team.execute_task(task)
await dept.execute_task(task)
```

## 相关概念

- → [公理系统](Axiomatic-System) (A3: 分形递归公理)
- → [分形架构](Fractal-Architecture) (完整架构)
- → [组合节点](Composite-Node) (实现)

## 代码位置

- `loom/fractal/node.py`
- `loom/fractal/composite.py`

## 反向链接

被引用于: [分形架构](Fractal-Architecture) | [公理系统](Axiomatic-System)
