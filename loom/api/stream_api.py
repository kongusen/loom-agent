"""
Stream API - 流式观测API

基于公理A2（事件主权）和定理T2（完全可观测性）：
提供HTTP/SSE接口供前端订阅节点事件。

设计原则：
1. 标准化 - 使用标准HTTP/SSE协议
2. 扁平化 - 前端直接订阅，无需层级
3. 实时性 - 事件即时推送

API端点：
- GET /stream/nodes/{node_id} - 订阅特定节点的所有事件
- GET /stream/thinking - 订阅所有思考过程事件
- GET /stream/events - 订阅所有节点事件
"""

from loom.events import EventBus
from loom.events.stream_converter import EventStreamConverter


class StreamAPI:
    """
    流式观测API

    提供HTTP/SSE端点供前端订阅节点事件。
    """

    def __init__(self, event_bus: EventBus):
        """
        初始化API

        Args:
            event_bus: 事件总线
        """
        self.event_bus = event_bus
        self.converter = EventStreamConverter(event_bus)

    async def stream_node_events(self, node_id: str):
        """
        订阅特定节点的所有事件

        Args:
            node_id: 节点ID

        Yields:
            SSE格式的事件流
        """
        async for sse_event in self.converter.stream_node_events(node_id):
            yield sse_event

    async def stream_thinking_events(self, node_id: str | None = None):
        """
        订阅思考过程事件

        Args:
            node_id: 可选的节点ID过滤

        Yields:
            SSE格式的事件流
        """
        async for sse_event in self.converter.stream_thinking_events(node_id):
            yield sse_event

    async def stream_all_events(self, action_pattern: str = "node.*"):
        """
        订阅所有节点事件

        Args:
            action_pattern: 事件动作模式

        Yields:
            SSE格式的事件流
        """
        async for sse_event in self.converter.subscribe_and_stream(action_pattern):
            yield sse_event


# ==================== FastAPI集成示例 ====================

"""
使用FastAPI集成示例：

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from loom.api.stream_api import StreamAPI
from loom.events import EventBus

app = FastAPI()
event_bus = EventBus()
stream_api = StreamAPI(event_bus)

@app.get("/stream/nodes/{node_id}")
async def stream_node(node_id: str):
    '''订阅特定节点的所有事件'''
    return StreamingResponse(
        stream_api.stream_node_events(node_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )

@app.get("/stream/thinking")
async def stream_thinking(node_id: str = None):
    '''订阅思考过程事件'''
    return StreamingResponse(
        stream_api.stream_thinking_events(node_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )

@app.get("/stream/events")
async def stream_all(pattern: str = "node.*"):
    '''订阅所有节点事件'''
    return StreamingResponse(
        stream_api.stream_all_events(pattern),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )
```

前端订阅示例：

```javascript
// 订阅特定节点的所有事件
const eventSource = new EventSource('/stream/nodes/agent-1');

eventSource.addEventListener('node.start', (e) => {
    const data = JSON.parse(e.data);
    console.log('Node started:', data);
});

eventSource.addEventListener('node.thinking', (e) => {
    const data = JSON.parse(e.data);
    console.log('Thinking:', data.parameters.content);
});

eventSource.addEventListener('node.complete', (e) => {
    const data = JSON.parse(e.data);
    console.log('Node completed:', data);
});

eventSource.addEventListener('node.error', (e) => {
    const data = JSON.parse(e.data);
    console.error('Node error:', data);
});
```
"""
