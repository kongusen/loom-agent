# 分形节点 (Fractal Node)

## 定义

**分形节点**是 Loom 的基本构建单元，所有组件(Agent、Tool、Memory、Workflow)都是节点。

## 核心接口

所有节点都实现 `NodeProtocol`:

```python
class NodeProtocol(Protocol):
    node_id: str
    node_type: str

    async def execute_task(self, task: Task) -> Task:
        """执行任务"""
        ...
```

## 节点类型

| 类型 | node_type | 用途 |
|------|-----------|------|
| Agent | "agent" | 智能体 |
| CompositeNode | "composite" | 组合节点 |
| Tool | "tool" | 工具 |
| Memory | "memory" | 记忆 |

## 基本能力

所有节点都具备：
- **事件发布**: `publish_event()`
- **记忆存储**: `memory.add()`
- **任务执行**: `execute_task()`

## 相关概念

- → [分形架构](Fractal-Architecture)
- → [组合节点](Composite-Node)

## 代码位置

- `loom/orchestration/base_node.py`
- `loom/fractal/node.py`

## 反向链接

被引用于: [分形架构](Fractal-Architecture) | [Agent API](API-Agent)
