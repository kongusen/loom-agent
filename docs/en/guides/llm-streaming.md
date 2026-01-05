# LLM Streaming Tool Call Guide

## Overview

Loom 0.3.6 enhances the streaming tool call handling capabilities of the LLM providers layer, offering:

- ✅ **Real-time Tool Call Notifications**: Immediate notification when a tool call starts, without awaiting completion.
- ✅ **Comprehensive Event Types**: Support for 7 event types (`text`, `tool_call_start`, `tool_call_delta`, `tool_call_complete`, `thought_injection`, `error`, `done`).
- ✅ **Automatic JSON Validation**: Validates the JSON format of tool parameters.
- ✅ **Token Usage Statistics**: Includes token usage in the streaming response.
- ✅ **Error Handling**: Unified error event format.
- ✅ **Retry Mechanism**: Intelligent retry logic for rate limits and network errors.

---

## Basic Usage

### 1. Streaming Call Example

```python
from loom.llm.providers import OpenAIProvider

# Create provider
provider = OpenAIProvider(
    model="gpt-4",
    api_key="sk-..."
)

# Define tools
tools = [
    {
        "name": "search_knowledge",
        "description": "Search knowledge base",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"}
            },
            "required": ["query"]
        }
    }
]

# Streaming call
messages = [{"role": "user", "content": "Check my order status"}]

async for chunk in provider.stream_chat(messages, tools):
    if chunk.type == "text":
        print(f"Text: {chunk.content}")

    elif chunk.type == "tool_call_start":
        print(f"Tool Call Start: {chunk.content['name']}")

    elif chunk.type == "tool_call_complete":
        print(f"Tool Call Complete: {chunk.content}")

    elif chunk.type == "error":
        print(f"Error: {chunk.content['message']}")

    elif chunk.type == "done":
        print(f"Done: {chunk.metadata}")
```

---

## Event Types Detail

### 1. text - Incremental Text Content

```python
StreamChunk(
    type="text",
    content="Checking for you",
    metadata={}
)
```

### 2. tool_call_start - Tool Call Start

**Trigger**: When the LLM starts calling a tool (sent immediately after acquiring the tool name).

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

### 3. tool_call_complete - Tool Call Complete

**Trigger**: After all tool call parameters are received and validated.

```python
StreamChunk(
    type="tool_call_complete",
    content={
        "id": "call_abc123",
        "name": "search_knowledge",
        "arguments": '{"query": "order status"}'
    },
    metadata={"index": 0}
)
```

### 4. error - Error Event

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

### 5. done - Stream End

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

## Advanced Usage

### 1. Real-time UI Updates

```python
async def stream_with_ui_update(provider, messages, tools):
    """Stream call with real-time UI updates"""

    active_tools = {}  # Track active tools

    async for chunk in provider.stream_chat(messages, tools):
        if chunk.type == "tool_call_start":
            tool_name = chunk.content["name"]
            tool_id = chunk.content["id"]

            # Immediately display tool status
            active_tools[tool_id] = tool_name
            ui.show_tool_status(tool_name, "executing")

        elif chunk.type == "tool_call_complete":
            tool_id = chunk.content["id"]

            # Execute tool
            result = await execute_tool(chunk.content)

            # Update UI
            ui.show_tool_result(active_tools[tool_id], result)
            del active_tools[tool_id]

        elif chunk.type == "text":
            ui.append_text(chunk.content)

        elif chunk.type == "done":
            ui.show_token_usage(chunk.metadata.get("token_usage"))
```

### 2. Error Handling and Retry

```python
from loom.llm.providers.retry_handler import retry_async, RetryConfig

# Configure retry
retry_config = RetryConfig(
    max_retries=3,
    initial_delay=1.0,
    exponential_base=2.0,
    retry_on_rate_limit=True
)

# Use retry wrapper
async def call_with_retry():
    return await retry_async(
        provider.chat,
        config=retry_config,
        messages=messages,
        tools=tools
    )
```

---

## Best Practices

### 1. Tool Call Status Tracking

```python
class ToolCallTracker:
    """Track tool call status"""

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

### 2. Token Usage Monitoring

```python
class TokenUsageMonitor:
    """Monitor token usage"""

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
        # Calculate cost based on model
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

## Performance Optimization Tips

1. **Parallel Tool Calls**: Enable `parallel_tool_calls=True` for better efficiency.
2. **Stream First**: Always use streaming API for long responses to improve user experience.
3. **Error Recovery**: Implement error handling logic to prevent single tool failures from crashing the whole process.
4. **Token Budget**: Monitor token usage to avoid exceeding budgets.

---

## Troubleshooting

### Issue 1: Incomplete Tool Call Arguments

**Symptom**: Receiving `invalid_tool_arguments` error.

**Cause**: LLM returns incorrect or truncated JSON.

**Solution**:
```python
# Catch error and retry
async for chunk in stream:
    if chunk.type == "error":
        if chunk.content["error"] == "invalid_tool_arguments":
            # Log error
            logger.error(f"Invalid tool args: {chunk.content}")
            # Optionally retry or use default arguments
```

### Issue 2: Stream Interruption

**Symptom**: Stream stops suddenly without receiving `done` event.

**Cause**: Network timeout or API error.

**Solution**:
```python
# Use timeout control
import asyncio

try:
    async with asyncio.timeout(30):  # 30 seconds timeout
        async for chunk in stream:
            process_chunk(chunk)
except asyncio.TimeoutError:
    logger.error("Stream timeout")
```

---

## Summary

The improved streaming tool call handling provides:

1. **Better User Experience**: Real-time notification of tool call status.
2. **Higher Reliability**: Automatic JSON validation and error handling.
3. **More Complete Monitoring**: Token usage statistics and detailed event types.
4. **Flexible Extension**: Universal response handler base class supports other LLM providers.

These improvements allow the Loom framework to better support complex agent application scenarios.
