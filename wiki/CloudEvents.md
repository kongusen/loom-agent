# CloudEvents

## 定义

**CloudEvents** 是 CNCF 标准的事件格式规范，Loom 使用它确保事件互操作性。

## 事件格式

```python
{
    "specversion": "1.0",
    "type": "loom.node.thinking",
    "source": "/node/researcher",
    "id": "evt-123456",
    "time": "2024-01-27T10:00:00Z",
    "data": {
        "content": "Let me analyze...",
        "task_id": "task-789"
    }
}
```

## 必需字段

| 字段 | 类型 | 说明 |
|------|------|------|
| specversion | string | CloudEvents 规范版本 (默认 "1.0") |
| type | string | 事件类型 |
| source | string | 事件源 (URI 格式) |
| id | string | 事件唯一 ID |

## 可选字段

| 字段 | 类型 | 说明 |
|------|------|------|
| time | string | 事件时间戳 (RFC3339) |
| data | any | 事件数据 |
| datacontenttype | string | 数据类型 (如 "application/json") |

## Loom 事件类型

### 节点事件
- `loom.node.created`
- `loom.node.started`
- `loom.node.thinking`
- `loom.node.completed`
- `loom.node.failed`

### 工具事件
- `loom.tool.called`
- `loom.tool.succeeded`
- `loom.tool.failed`

### 记忆事件
- `loom.memory.read`
- `loom.memory.write`
- `loom.memory.evict`

## 相关概念

- → [事件总线](Event-Bus)

## 外部资源

- [CloudEvents 规范](https://github.com/cloudevents/spec)

## 代码位置

- `loom/protocol/events.py`

## 反向链接

被引用于: [事件总线](Event-Bus)
