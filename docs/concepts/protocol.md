# 协议优先架构与事件总线 (Protocol-First Architecture & Event Bus)

Loom 依赖于**协议优先 (Protocol-First)** 的设计哲学。这意味着交互模式是由显式的接口 (Protocols) 和数据契约定义的，而不是具体的类继承。

## 为什么要协议优先？

1.  **解耦**: 只要满足协议，你可以替换整个 Memory 系统或 Node 实现，而不会破坏其他部分。
2.  **互操作性**: 不同的系统（即使是非 Python 系统）只要遵守数据契约 (CloudEvents) 就可以交互。
3.  **测试**: Mock 实现变得轻而易举。

## 通用事件总线 (The Universal Event Bus)

Loom 中的所有通信都发生在 **通用事件总线** 上。Agent **不** 直接调用彼此的方法。它们发布事件。

### CloudEvents 标准

我们使用 [CNCF CloudEvents](https://cloudevents.io/) 规范作为所有消息的标准。

```json
{
    "specversion": "1.0",
    "type": "node.request",
    "source": "/loom/agent/manager",
    "subject": "/loom/agent/worker",
    "id": "A234-1234-1234",
    "time": "2023-11-02T12:00:00Z",
    "datacontenttype": "application/json",
    "data": {
        "instruction": "分析这个数据集",
        "context": {...}
    }
}
```

### 事件类型
*   `node.request`: 执行工作的请求。
*   `node.response`: 工作的结果。
*   `node.error`: 发生了错误。
*   `system.heartbeat`: 健康检查。

## 核心协议

### `NodeProtocol`
定义一个可以处理事件的实体。
```python
class NodeProtocol(Protocol):
    async def process(self, event: CloudEvent) -> CloudEvent: ...
```

### `MemoryProtocol`
定义如何存储和检索数据。
```python
class MemoryProtocol(Protocol):
    async def save(self, key: str, value: Any): ...
    async def load(self, key: str) -> Any: ...
```

### `TransferProtocol` (MCP)
**模型上下文协议 (Model Context Protocol, MCP)** 定义了工具如何被发现和调用。Loom Agents 使用 MCP 来：
*   列出可用工具 (`list_tools`).
*   调用工具 (`call_tool`).
*   读取资源 (`read_resource`).

这个标准允许 Loom 连接到 **任何** 兼容 MCP 的服务器（例如，数据库 MCP，Slack MCP），而无需编写自定义集成代码。
