# A3: 分形自相似公理 (Fractal Self-Similarity Axiom)

> **公理陈述**: ∀node ∈ System: structure(node) ≅ structure(System)

## 设计理念

A3层实现节点的递归组合能力，支持分形结构。
节点可以包含其他节点，形成树状/分形结构。

## 核心组件

### 1. NodeContainer (`container.py`)
节点容器 - 实现单节点包装：
- `set_child()`: 设置子节点（单个）
- `execute_task()`: 委托给子节点执行
- 实现NodeProtocol，可被递归组合
- **注意**: 容器只支持单个子节点，多节点编排请使用 Orchestrator

### 2. FractalOrchestrator (`orchestrator.py`)
分形编排器 - 递归任务分解：
- `execute()`: 执行分形编排
- 任务分解策略（可自定义）
- 并行执行子任务
- 结果聚合

## 与公理系统的关系

- **A3（分形自相似）**: 节点结构与系统结构同构
- **递归组合**: 容器可以包含容器
- **透明性**: 容器和叶子节点实现相同接口

## 分形特性

**自相似性**:
```
System = Node₁ + Node₂ + ... + Nodeₙ
Node = SubNode₁ + SubNode₂ + ... + SubNodeₘ
```

**递归深度**: 理论上无限，实践中受限于资源

## 使用示例

```python
from loom.fractal import NodeContainer, FractalOrchestrator
from loom.agent.card import AgentCard, AgentCapability

# 创建容器
container = NodeContainer(
    node_id="container1",
    agent_card=AgentCard(
        agent_id="container1",
        name="Container",
        description="A container node",
        capabilities=[AgentCapability.MULTI_AGENT]
    )
)

# 设置子节点（单个）
container.set_child(child_node)

# 多节点编排请使用 Orchestrator
from loom.orchestration import CrewOrchestrator
orchestrator = CrewOrchestrator(nodes=[child_node1, child_node2])
result = await orchestrator.orchestrate(task)
```
