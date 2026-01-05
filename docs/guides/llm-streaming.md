# LLM 流式工具调用使用指南

## 概述

Loom 0.3.6 增强了 LLM providers 层的流式工具调用处理能力，提供：

- ✅ **实时工具调用通知**: 工具调用开始时立即通知，无需等待完成
- ✅ **完整的事件类型**: 支持 7 种事件类型（text, tool_call_start, tool_call_delta, tool_call_complete, thought_injection, error, done）
- ✅ **自动 JSON 验证**: 验证工具参数的 JSON 格式
- ✅ **Token 使用统计**: 流式响应中包含 token usage
- ✅ **错误处理**: 统一的错误事件格式
- ✅ **重试机制**: 智能重试处理速率限制和网络错误

---

## 基础使用

### 1. 流式调用示例

```python
from loom.llm.providers import OpenAIProvider

# 创建 provider
provider = OpenAIProvider(
    model="gpt-4",
    api_key="sk-..."
)

# 定义工具
tools = [
    {
        "name": "search_knowledge",
        "description": "搜索知识库",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"}
            },
            "required": ["query"]
        }
    }
]

# 流式调用
messages = [{"role": "user", "content": "帮我查询订单状态"}]

async for chunk in provider.stream_chat(messages, tools):
    if chunk.type == "text":
        print(f"文本: {chunk.content}")

    elif chunk.type == "tool_call_start":
        print(f"工具调用开始: {chunk.content['name']}")

    elif chunk.type == "tool_call_complete":
        print(f"工具调用完成: {chunk.content}")

    elif chunk.type == "error":
        print(f"错误: {chunk.content['message']}")

    elif chunk.type == "done":
        print(f"完成: {chunk.metadata}")
```

---

## 事件类型详解

### 1. text - 文本内容增量

```python
StreamChunk(
    type="text",
    content="正在为您查询",
    metadata={}
)
```

### 2. tool_call_start - 工具调用开始

**触发时机**: 当 LLM 开始调用工具时（获得工具名称后立即发送）

```python
StreamChunk(
    type="tool_call_start",
    content={
        "id": "call_abc123",
        "name": "search_knowledge",
        "index": 0
    },
    metadata={}
)
```

### 3. tool_call_complete - 工具调用完成

**触发时机**: 工具调用参数完全接收并验证通过后

```python
StreamChunk(
    type="tool_call_complete",
    content={
        "id": "call_abc123",
        "name": "search_knowledge",
        "arguments": '{"query": "订单状态"}'
    },
    metadata={"index": 0}
)
```

### 4. error - 错误事件

```python
StreamChunk(
    type="error",
    content={
        "error": "invalid_tool_arguments",
        "message": "Tool arguments are not valid JSON",
        "tool_call": {...}
    },
    metadata={"index": 0}
)
```

### 5. done - 流结束

```python
StreamChunk(
    type="done",
    content="",
    metadata={
        "finish_reason": "tool_calls",
        "token_usage": {
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_tokens": 150
        }
    }
)
```

---

## 高级用法

### 1. 实时 UI 更新

```python
async def stream_with_ui_update(provider, messages, tools):
    """流式调用并实时更新 UI"""

    active_tools = {}  # 跟踪正在执行的工具

    async for chunk in provider.stream_chat(messages, tools):
        if chunk.type == "tool_call_start":
            tool_name = chunk.content["name"]
            tool_id = chunk.content["id"]

            # 立即显示工具调用状态
            active_tools[tool_id] = tool_name
            ui.show_tool_status(tool_name, "executing")

        elif chunk.type == "tool_call_complete":
            tool_id = chunk.content["id"]

            # 执行工具
            result = await execute_tool(chunk.content)

            # 更新 UI
            ui.show_tool_result(active_tools[tool_id], result)
            del active_tools[tool_id]

        elif chunk.type == "text":
            ui.append_text(chunk.content)

        elif chunk.type == "done":
            ui.show_token_usage(chunk.metadata.get("token_usage"))
```

### 2. 错误处理和重试

```python
from loom.llm.providers.retry_handler import retry_async, RetryConfig

# 配置重试
retry_config = RetryConfig(
    max_retries=3,
    initial_delay=1.0,
    exponential_base=2.0,
    retry_on_rate_limit=True
)

# 使用重试包装器
async def call_with_retry():
    return await retry_async(
        provider.chat,
        config=retry_config,
        messages=messages,
        tools=tools
    )
```

---

## 最佳实践

### 1. 工具调用状态跟踪

```python
class ToolCallTracker:
    """跟踪工具调用状态"""

    def __init__(self):
        self.pending = {}  # tool_id -> tool_name
        self.completed = {}  # tool_id -> result

    async def process_stream(self, stream):
        async for chunk in stream:
            if chunk.type == "tool_call_start":
                tool_id = chunk.content["id"]
                tool_name = chunk.content["name"]
                self.pending[tool_id] = tool_name
                yield chunk

            elif chunk.type == "tool_call_complete":
                tool_id = chunk.content["id"]
                if tool_id in self.pending:
                    del self.pending[tool_id]
                self.completed[tool_id] = chunk.content
                yield chunk

            else:
                yield chunk
```

### 2. Token 使用监控

```python
class TokenUsageMonitor:
    """监控 token 使用情况"""

    def __init__(self):
        self.total_tokens = 0
        self.total_cost = 0.0

    async def monitor_stream(self, stream, model="gpt-4"):
        async for chunk in stream:
            if chunk.type == "done":
                usage = chunk.metadata.get("token_usage")
                if usage:
                    self.total_tokens += usage["total_tokens"]
                    self.total_cost += self.calculate_cost(
                        usage, model
                    )
            yield chunk

    def calculate_cost(self, usage, model):
        # 根据模型计算成本
        rates = {
            "gpt-4": {"input": 0.03, "output": 0.06},
            "gpt-3.5-turbo": {"input": 0.001, "output": 0.002}
        }
        rate = rates.get(model, rates["gpt-4"])
        return (
            usage["prompt_tokens"] * rate["input"] / 1000 +
            usage["completion_tokens"] * rate["output"] / 1000
        )
```

---

## 性能优化建议

1. **并行工具调用**: 启用 `parallel_tool_calls=True` 提高效率
2. **流式优先**: 对于长响应，始终使用流式 API 提升用户体验
3. **错误恢复**: 实现错误处理逻辑，避免单个工具失败导致整体失败
4. **Token 预算**: 监控 token 使用，避免超出预算

---

## 故障排查

### 问题 1: 工具调用参数不完整

**症状**: 收到 `invalid_tool_arguments` 错误

**原因**: LLM 返回的 JSON 格式不正确或被截断

**解决方案**:
```python
# 捕获错误并重试
async for chunk in stream:
    if chunk.type == "error":
        if chunk.content["error"] == "invalid_tool_arguments":
            # 记录错误
            logger.error(f"Invalid tool args: {chunk.content}")
            # 可以选择重新调用或使用默认参数
```

### 问题 2: 流式响应中断

**症状**: 流突然停止，没有收到 `done` 事件

**原因**: 网络超时或 API 错误

**解决方案**:
```python
# 使用超时控制
import asyncio

try:
    async with asyncio.timeout(30):  # 30秒超时
        async for chunk in stream:
            process_chunk(chunk)
except asyncio.TimeoutError:
    logger.error("Stream timeout")
```

---

## 总结

改进后的流式工具调用处理提供了：

1. **更好的用户体验**: 实时通知工具调用状态
2. **更强的可靠性**: 自动 JSON 验证和错误处理
3. **更完整的监控**: Token 使用统计和详细的事件类型
4. **更灵活的扩展**: 通用的响应处理器基类支持其他 LLM 提供商

这些改进使得 Loom 框架能够更好地支持复杂的智能体应用场景。
