# Loom Agent v0.1 迁移指南

**从 v0.0.x 升级到 v0.1.0**

本指南帮助您将现有代码迁移到 Loom Agent v0.1.0。这是一次**重大架构升级**，完全重构了LLM接口和Agent API。

---

## 🎯 核心变更

### 1. **统一LLM接口** - 从4个方法简化到1个

**之前 (v0.0.x)**:
```python
class BaseLLM(ABC):
    async def generate(...) -> str
    async def stream(...) -> AsyncGenerator[str, None]
    async def generate_with_tools(...) -> Dict
    async def stream_with_tools(...) -> AsyncGenerator[str, None]
```

**现在 (v0.1.0)**:
```python
@runtime_checkable
class BaseLLM(Protocol):
    @property
    def model_name(self) -> str: ...

    async def stream(
        self,
        messages: List[Dict],
        tools: Optional[List[Dict]] = None,
        response_format: Optional[Dict] = None,
        **kwargs
    ) -> AsyncGenerator[LLMEvent, None]: ...
```

### 2. **Agent API简化** - 2个清晰的入口

**之前 (v0.0.x)**:
```python
# 混乱的多个方法
agent.run()      # 非流式
agent.stream()   # 旧流式 → StreamEvent
agent.astream()  # 别名
agent.execute()  # 新流式 → AgentEvent
```

**现在 (v0.1.0)**:
```python
# 只有2个清晰的方法
agent.run()      # 非流式 → str
agent.execute()  # 流式 → AsyncGenerator[AgentEvent]
agent.ainvoke()  # run()的LangChain风格别名
```

### 3. **统一事件格式** - LLMEvent

**之前 (v0.0.x)**:
```python
# stream() 返回字符串
async for chunk in llm.stream(messages):
    print(chunk)  # str

# StreamEvent (已废弃)
async for event in agent.stream(input):
    if event.type == "text":
        print(event.content)
```

**现在 (v0.1.0)**:
```python
# 统一的 LLMEvent 字典
async for event in llm.stream(messages):
    if event["type"] == "content_delta":
        print(event["content"])
    elif event["type"] == "tool_calls":
        handle_tools(event["tool_calls"])
    elif event["type"] == "finish":
        print(f"Done: {event['finish_reason']}")
```

---

## 📋 迁移清单

### ✅ Agent使用者

#### 1. **更新流式输出代码**

**之前**:
```python
async for chunk in agent.stream("请求"):
    print(chunk, end="")
```

**之后**:
```python
from loom.core.events import AgentEventType

async for event in agent.execute("请求"):
    if event.type == AgentEventType.LLM_DELTA:
        print(event.content, end="")
    elif event.type == AgentEventType.AGENT_FINISH:
        break
```

#### 2. **删除 StreamEvent 导入**

**之前**:
```python
from loom.core.types import StreamEvent  # ❌ 已删除
```

**之后**:
```python
from loom.core.events import AgentEvent, AgentEventType  # ✅ 使用这个
```

#### 3. **更新事件处理**

**之前**:
```python
if event.type == "text":
    print(event.content)
elif event.type == "tool_call":
    print(event.tool_name)
```

**之后**:
```python
if event.type == AgentEventType.LLM_DELTA:
    print(event.content)
elif event.type == AgentEventType.TOOL_EXECUTION_START:
    print(event.metadata.get('tool_name'))
elif event.type == AgentEventType.TOOL_RESULT:
    print(event.tool_result.content)
```

### ✅ LLM实现者

#### 1. **从ABC改为Protocol**

**之前**:
```python
from loom.interfaces.llm import BaseLLM

class MyLLM(BaseLLM):  # 需要继承
    async def generate(...): ...
    async def stream(...): ...
    async def generate_with_tools(...): ...
    async def stream_with_tools(...): ...
```

**之后**:
```python
# 不需要继承！只需实现Protocol
class MyLLM:
    @property
    def model_name(self) -> str:
        return "my-model"

    async def stream(
        self,
        messages: List[Dict],
        tools: Optional[List[Dict]] = None,
        response_format: Optional[Dict] = None,
        **kwargs
    ) -> AsyncGenerator[LLMEvent, None]:
        # 处理所有情况：文本、工具、JSON
        async for chunk in api_stream:
            yield {"type": "content_delta", "content": chunk}

        if tool_calls:
            yield {"type": "tool_calls", "tool_calls": tool_calls}

        yield {"type": "finish", "finish_reason": "stop"}
```

#### 2. **统一所有LLM调用**

**之前**:
```python
# 需要根据是否有工具选择不同方法
if tools:
    result = await llm.generate_with_tools(messages, tools)
else:
    result = await llm.generate(messages)
```

**之后**:
```python
# 统一使用 stream()
async for event in llm.stream(messages, tools=tools):
    if event["type"] == "content_delta":
        content += event["content"]
    elif event["type"] == "tool_calls":
        tool_calls = event["tool_calls"]
```

---

## 🔧 常见迁移场景

### 场景1: 简单的文本生成

**之前**:
```python
result = await agent.run("你好")
print(result)
```

**之后**:
```python
# 完全不变！run() 依然可用
result = await agent.run("你好")
print(result)
```

### 场景2: 流式输出到UI

**之前**:
```python
async for chunk in agent.stream("讲个故事"):
    ui.append_text(chunk)
```

**之后**:
```python
from loom.core.events import AgentEventType

async for event in agent.execute("讲个故事"):
    if event.type == AgentEventType.LLM_DELTA:
        ui.append_text(event.content)
    elif event.type == AgentEventType.TOOL_RESULT:
        ui.show_tool(event.tool_result.tool_name)
```

### 场景3: FastAPI流式响应

**之前**:
```python
@app.get("/stream")
async def stream_endpoint(query: str):
    async def generator():
        async for chunk in agent.stream(query):
            yield f"data: {chunk}\n\n"

    return StreamingResponse(generator())
```

**之后**:
```python
from loom.core.events import AgentEventType

@app.get("/stream")
async def stream_endpoint(query: str):
    async def generator():
        async for event in agent.execute(query):
            if event.type == AgentEventType.LLM_DELTA:
                yield f"data: {event.content}\n\n"
            elif event.type == AgentEventType.AGENT_FINISH:
                yield "data: [DONE]\n\n"
                break

    return StreamingResponse(generator(), media_type="text/event-stream")
```

### 场景4: 实现自定义LLM

**之前**:
```python
class MyLLM(BaseLLM):
    async def generate(self, messages):
        # 实现
        pass

    async def stream(self, messages):
        # 实现
        pass

    async def generate_with_tools(self, messages, tools):
        # 实现
        pass

    async def stream_with_tools(self, messages, tools):
        # 实现
        pass
```

**之后**:
```python
class MyLLM:
    @property
    def model_name(self) -> str:
        return "my-model"

    async def stream(self, messages, tools=None, **kwargs):
        # 一个方法处理所有情况
        async for chunk in my_api.stream(messages):
            yield {"type": "content_delta", "content": chunk}

        yield {"type": "finish", "finish_reason": "stop"}
```

---

## 🚀 新特性

### 1. 运行时Protocol验证

```python
from loom.interfaces.llm import validate_llm

llm = MyLLM()
validate_llm(llm)  # 自动检查是否实现了Protocol
```

### 2. 统一事件流

```python
# LLMEvent 涵盖所有场景
{
    "type": "content_delta",  # 文本增量
    "content": "Hello"
}
{
    "type": "tool_calls",  # 工具调用
    "tool_calls": [...]
}
{
    "type": "finish",  # 完成标记
    "finish_reason": "stop"
}
```

### 3. 更好的类型安全

```python
# TypedDict 提供类型提示
from loom.interfaces.llm import LLMEvent

async def process_stream(stream: AsyncGenerator[LLMEvent, None]):
    async for event in stream:
        # IDE 自动提示 event 的结构
        if event["type"] == "content_delta":
            print(event["content"])
```

---

## ❓ 常见问题

### Q: 旧的 `stream()` 方法还能用吗？

**A**: 不能。`agent.stream()` 和 `agent.astream()` 已被完全删除。请使用 `agent.execute()`。

### Q: StreamEvent 在哪里？

**A**: `StreamEvent` 已被删除。请使用 `AgentEvent` (从 `loom.core.events` 导入)。

### Q: 我的自定义LLM还需要继承BaseLLM吗？

**A**: 不需要！只要实现 `model_name` 属性和 `stream()` 方法即可。这就是Protocol的优势。

### Q: 如何判断我的LLM是否兼容？

**A**: 使用运行时验证：
```python
from loom.interfaces.llm import is_llm

if is_llm(my_llm):
    print("兼容!")
else:
    print("需要更新")
```

### Q: 为什么要做这个改变？

**A**: 主要原因：
1. **简化**: 从4个方法减少到1个方法
2. **统一**: 所有LLM操作返回相同格式
3. **灵活**: Protocol支持鸭子类型，无需继承
4. **类型安全**: 运行时验证 + 静态类型检查
5. **一致性**: 消除分支逻辑，代码更清晰

---

## 📚 更多资源

- **完整文档**: [docs/user/user-guide.md](user/user-guide.md)
- **API参考**: [docs/user/api-reference.md](user/api-reference.md)
- **示例代码**: [examples/](../examples/)
- **GitHub**: https://github.com/kongusen/loom-agent

---

## 💡 需要帮助？

如果在迁移过程中遇到问题：

1. **检查文档**: 查看 [用户指南](user/user-guide.md)
2. **查看示例**: 参考 [examples/](../examples/) 目录
3. **提交Issue**: https://github.com/kongusen/loom-agent/issues
4. **联系支持**: wanghaishan0210@gmail.com

---

**祝您迁移顺利！** 🎉
