# A5: 认知调度公理 (Cognitive Orchestration Axiom)

> **公理陈述**: Cognition = Orchestration(N1, N2, ..., Nk)

## 设计理念

A5层实现不同的编排模式，认知通过节点间的编排交互涌现。
"思考"即是"调度"。

## 核心组件

### 1. Orchestrator (`base.py`)
编排器抽象基类：
- `add_node()`: 添加节点
- `remove_node()`: 移除节点
- `orchestrate()`: 编排执行任务

### 2. RouterOrchestrator (`router.py`)
路由编排器 - 智能路由模式：
- 根据能力匹配选择节点
- 单节点执行
- 快速决策

### 3. CrewOrchestrator (`crew.py`)
团队编排器 - 多节点协作模式：
- 并行执行
- 结果聚合
- 协同工作

## 与公理系统的关系

- **A5（认知调度）**: 认知 = 编排(节点1, 节点2, ...)
- **涌现属性**: 认知不在单个节点内，而是在交互中涌现
- **编排模式**: Router/Crew/Fractal等不同模式

## 使用示例

```python
from loom.orchestration import RouterOrchestrator, CrewOrchestrator
from loom.protocol import Task

# 路由模式
router = RouterOrchestrator(nodes=[node1, node2])
result = await router.orchestrate(task)

# 团队模式
crew = CrewOrchestrator(nodes=[node1, node2, node3])
result = await crew.orchestrate(task)
```
