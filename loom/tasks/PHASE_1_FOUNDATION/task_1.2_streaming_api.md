# Task 1.2: 重构 Agent.execute() 为流式接口

**状态**: ⏳ 待开始
**优先级**: P0
**预计时间**: 1-2 天
**依赖**: Task 1.1 (AgentEvent 模型) ✅

---

## 📋 任务概述

### 目标

将 `Agent.execute()` 方法改为返回 `AsyncGenerator[AgentEvent, None]`，实现全链路流式架构。

### 为什么需要这个任务？

**当前问题**:
```python
# Loom 1.0 - 非流式
result = await agent.run(prompt)  # 等待完成，无实时进度
print(result)
```

**期望结果**:
```python
# Loom 2.0 - 流式
async for event in agent.execute(prompt):
    if event.type == AgentEventType.LLM_DELTA:
        print(event.content, end="", flush=True)
    elif event.type == AgentEventType.TOOL_PROGRESS:
        print(f"\n[Tool] {event.metadata['status']}")
```

---

## 📐 详细步骤

### Step 1: 修改 Agent 接口

**文件**: `loom/components/agent.py`

**当前代码** (简化):
```python
class Agent:
    async def run(self, input: str) -> str:
        """Execute agent and return final response"""
        return await self.executor.execute(input)
```

**修改为**:
```python
class Agent:
    async def execute(self, input: str) -> AsyncGenerator[AgentEvent, None]:
        """
        Execute agent with streaming events.

        Yields:
            AgentEvent: Events representing execution progress

        Example:
            ```python
            async for event in agent.execute("Your prompt"):
                if event.type == AgentEventType.LLM_DELTA:
                    print(event.content, end="")
            ```
        """
        # 初始化 turn state
        turn_state = TurnState(turn_counter=0, turn_id=str(uuid.uuid4()))

        # 创建初始消息
        messages = [Message(role="user", content=input)]

        # 调用 executor 的流式接口
        async for event in self.executor.execute_stream(messages, turn_state):
            yield event

    async def run(self, input: str) -> str:
        """
        Execute agent and return final response (backward compatible).

        This is a convenience method that wraps execute() and extracts
        the final response.

        Args:
            input: User input

        Returns:
            Final response text
        """
        final_content = ""

        async for event in self.execute(input):
            # Accumulate LLM deltas
            if event.type == AgentEventType.LLM_DELTA:
                final_content += event.content or ""

            # Return on finish
            elif event.type == AgentEventType.AGENT_FINISH:
                return event.content or final_content

            # Raise on error
            elif event.type == AgentEventType.ERROR:
                raise event.error

        return final_content
```

**新增数据类**:
```python
from dataclasses import dataclass

@dataclass
class TurnState:
    """State for recursive agent execution"""
    turn_counter: int
    turn_id: str
    compacted: bool = False
    max_iterations: int = 10
```

---

### Step 2: 修改 AgentExecutor 接口

**文件**: `loom/core/agent_executor.py`

**当前代码** (简化):
```python
class AgentExecutor:
    async def execute(self, user_input: str) -> str:
        """Execute agent and return final response"""
        # ... 复杂的逻辑
        return final_response
```

**修改为**:
```python
class AgentExecutor:
    async def execute_stream(
        self,
        messages: List[Message],
        turn_state: TurnState
    ) -> AsyncGenerator[AgentEvent, None]:
        """
        Execute agent with streaming events.

        Args:
            messages: Conversation history
            turn_state: Current turn state

        Yields:
            AgentEvent: Events representing execution progress
        """

        # Phase 0: Iteration check
        yield AgentEvent(
            type=AgentEventType.ITERATION_START,
            iteration=turn_state.turn_counter,
            turn_id=turn_state.turn_id
        )

        if turn_state.turn_counter >= turn_state.max_iterations:
            yield AgentEvent(type=AgentEventType.MAX_ITERATIONS_REACHED)
            return

        # Phase 1: Context assembly
        yield AgentEvent.phase_start("context_assembly")

        system_prompt = self.system_prompt_builder.build()
        # TODO: 后续任务会替换为 ContextAssembler

        yield AgentEvent.phase_end(
            "context_assembly",
            tokens_used=self._count_tokens(system_prompt)
        )

        # Phase 2: RAG retrieval (if enabled)
        if self.context_retriever:
            yield AgentEvent(type=AgentEventType.RETRIEVAL_START)

            retrieved_docs = await self.context_retriever.retrieve(
                messages[-1].content
            )

            for doc in retrieved_docs:
                yield AgentEvent(
                    type=AgentEventType.RETRIEVAL_PROGRESS,
                    metadata={
                        "doc_title": doc.metadata.get("title", "Unknown"),
                        "relevance_score": doc.metadata.get("score", 0.0)
                    }
                )

            yield AgentEvent(type=AgentEventType.RETRIEVAL_COMPLETE)

            # TODO: 正确注入 RAG 上下文（Task 1.3）

        # Phase 3: LLM call
        yield AgentEvent(type=AgentEventType.LLM_START)

        # 构建完整消息
        full_messages = [
            Message(role="system", content=system_prompt),
            *messages
        ]

        # 流式调用 LLM
        llm_response = ""
        tool_calls = []

        async for chunk in self.llm.stream(full_messages, tools=self.tools):
            if chunk.get("type") == "text_delta":
                text = chunk["content"]
                llm_response += text
                yield AgentEvent.llm_delta(text)

            elif chunk.get("type") == "tool_calls":
                tool_calls = chunk["tool_calls"]
                yield AgentEvent(
                    type=AgentEventType.LLM_TOOL_CALLS,
                    metadata={"tool_count": len(tool_calls)}
                )

        yield AgentEvent(type=AgentEventType.LLM_COMPLETE)

        # Phase 4: Tool execution (if needed)
        if tool_calls:
            yield AgentEvent(type=AgentEventType.TOOL_CALLS_START)

            tool_results = []

            for tool_call in tool_calls:
                # TODO: 后续会使用 ToolOrchestrator（Task 2.1）
                # 现在简单顺序执行

                tool = self.tools[tool_call.name]

                yield AgentEvent(
                    type=AgentEventType.TOOL_EXECUTION_START,
                    tool_call=ToolCall(
                        id=tool_call.id,
                        name=tool_call.name,
                        arguments=tool_call.arguments
                    )
                )

                try:
                    result_content = await tool.execute(tool_call.arguments)

                    result = ToolResult(
                        tool_call_id=tool_call.id,
                        tool_name=tool_call.name,
                        content=result_content,
                        is_error=False
                    )

                    yield AgentEvent.tool_result(result)
                    tool_results.append(result)

                except Exception as e:
                    result = ToolResult(
                        tool_call_id=tool_call.id,
                        tool_name=tool_call.name,
                        content=str(e),
                        is_error=True
                    )

                    yield AgentEvent(
                        type=AgentEventType.TOOL_ERROR,
                        tool_result=result,
                        error=e
                    )
                    tool_results.append(result)

            # Phase 5: Recursion (if tools were executed)
            # 创建新消息包含工具结果
            new_messages = [
                *messages,
                Message(role="assistant", content=llm_response, tool_calls=tool_calls),
                *[Message(role="tool", content=r.content, tool_call_id=r.tool_call_id)
                  for r in tool_results]
            ]

            # 递归调用
            new_turn_state = TurnState(
                turn_counter=turn_state.turn_counter + 1,
                turn_id=turn_state.turn_id
            )

            async for event in self.execute_stream(new_messages, new_turn_state):
                yield event

        else:
            # Phase 5: Finish (no tools)
            yield AgentEvent.agent_finish(llm_response)

    # 保留向后兼容方法
    async def execute(self, user_input: str) -> str:
        """Legacy method - wraps execute_stream"""
        messages = [Message(role="user", content=user_input)]
        turn_state = TurnState(turn_counter=0, turn_id=str(uuid.uuid4()))

        final_response = ""
        async for event in self.execute_stream(messages, turn_state):
            if event.type == AgentEventType.AGENT_FINISH:
                return event.content or final_response
            elif event.type == AgentEventType.LLM_DELTA:
                final_response += event.content or ""

        return final_response
```

---

### Step 3: 修改 LLM 接口（可选）

**文件**: `loom/interfaces/llm.py`

如果 LLM 接口不支持流式工具调用，可以添加 fallback：

```python
class BaseLLM(ABC):
    # 现有方法...

    async def stream(
        self,
        messages: List[Dict],
        tools: List[Dict] = None
    ) -> AsyncGenerator[Dict, None]:
        """
        Stream LLM response.

        Yields:
            Dict with one of:
            - {"type": "text_delta", "content": "..."}
            - {"type": "tool_calls", "tool_calls": [...]}
        """
        # Default implementation: fallback to non-streaming
        response = await self.generate_with_tools(messages, tools)

        # Yield as single chunk
        if "tool_calls" in response:
            yield {"type": "tool_calls", "tool_calls": response["tool_calls"]}
        else:
            yield {"type": "text_delta", "content": response["content"]}
```

---

## 🧪 测试要求

### 单元测试

**文件**: `tests/unit/test_streaming_api.py`

测试用例：

1. ✅ `test_agent_execute_returns_generator` - 验证返回类型
2. ✅ `test_agent_run_backward_compatible` - 验证向后兼容
3. ✅ `test_llm_delta_events` - 验证 LLM 流式事件
4. ✅ `test_tool_execution_events` - 验证工具执行事件
5. ✅ `test_iteration_events` - 验证迭代事件
6. ✅ `test_error_propagation` - 验证错误处理

```python
import pytest
from loom import Agent
from loom.core.events import AgentEventType, EventCollector

@pytest.mark.asyncio
async def test_agent_execute_returns_generator():
    """Test that execute() returns AsyncGenerator"""
    agent = Agent(llm=mock_llm, tools=[])

    result = agent.execute("test")

    # Should be async generator
    assert hasattr(result, '__aiter__')

@pytest.mark.asyncio
async def test_agent_run_backward_compatible():
    """Test that run() still works"""
    agent = Agent(llm=mock_llm, tools=[])

    result = await agent.run("test")

    # Should return string
    assert isinstance(result, str)

@pytest.mark.asyncio
async def test_llm_delta_events():
    """Test LLM streaming produces delta events"""
    agent = Agent(llm=streaming_mock_llm, tools=[])
    collector = EventCollector()

    async for event in agent.execute("test"):
        collector.add(event)

    # Should have LLM_START, LLM_DELTA, LLM_COMPLETE
    assert any(e.type == AgentEventType.LLM_START for e in collector.events)
    assert any(e.type == AgentEventType.LLM_DELTA for e in collector.events)
    assert any(e.type == AgentEventType.LLM_COMPLETE for e in collector.events)

    # Reconstructed content should match
    llm_content = collector.get_llm_content()
    assert len(llm_content) > 0
```

### 集成测试

**文件**: `tests/integration/test_agent_streaming.py`

测试真实场景：

1. ✅ End-to-end 流式执行
2. ✅ 工具调用 + 递归
3. ✅ RAG 集成（如果启用）
4. ✅ 错误恢复

---

## ✅ 验收标准

| 标准 | 要求 | 检查 |
|------|------|------|
| API 修改 | `execute()` 返回 `AsyncGenerator[AgentEvent]` | [ ] |
| 向后兼容 | `run()` 方法仍工作 | [ ] |
| 事件产生 | 产生所有必需事件类型 | [ ] |
| 测试覆盖 | ≥ 80% 覆盖率 | [ ] |
| 所有测试通过 | 单元 + 集成测试 | [ ] |
| 文档更新 | 更新 API 文档和示例 | [ ] |
| 性能 | 无明显性能下降 | [ ] |

---

## 📋 实施检查清单

### 代码修改

- [ ] 修改 `loom/components/agent.py`
  - [ ] 新增 `execute()` 方法（返回 AsyncGenerator）
  - [ ] 修改 `run()` 为包装方法（向后兼容）
  - [ ] 添加 `TurnState` 数据类

- [ ] 修改 `loom/core/agent_executor.py`
  - [ ] 新增 `execute_stream()` 方法
  - [ ] 产生所有必需事件
  - [ ] 保留 `execute()` 向后兼容

- [ ] 修改 `loom/interfaces/llm.py` （可选）
  - [ ] 添加 `stream()` 方法

### 测试

- [ ] 创建 `tests/unit/test_streaming_api.py`
  - [ ] 6+ 个单元测试
  - [ ] Mock LLM 和 Tools

- [ ] 创建 `tests/integration/test_agent_streaming.py`
  - [ ] End-to-end 测试
  - [ ] 真实 LLM 集成（可选）

- [ ] 运行所有测试
  ```bash
  pytest tests/unit/test_streaming_api.py -v
  pytest tests/integration/test_agent_streaming.py -v
  pytest tests/ -v  # 确保没有破坏现有测试
  ```

### 文档

- [ ] 更新 `docs/api_reference.md`
  - [ ] 记录新的 `execute()` API
  - [ ] 记录事件流模式

- [ ] 更新 `README.md`
  - [ ] 添加流式 API 示例

- [ ] 创建 `examples/streaming_example.py`
  - [ ] 基础流式示例
  - [ ] 工具执行示例
  - [ ] 错误处理示例

### 完成

- [ ] 创建 `docs/TASK_1.2_COMPLETION_SUMMARY.md`
- [ ] 更新 `LOOM_2.0_DEVELOPMENT_PLAN.md`
- [ ] 更新 `loom/tasks/README.md`
- [ ] 代码审查
- [ ] 合并到主分支

---

## 🔗 参考资源

- [Task 1.1: AgentEvent 模型](task_1.1_agent_events.md)
- [AgentEvent 使用指南](../../../docs/agent_events_guide.md)
- [Claude Code 控制流程](../../../cc分析/Control%20Flow.md)

---

## 📝 注意事项

### 关键决策

1. **递归 vs 循环**: 当前使用递归实现多轮对话，后续可能改为循环（Task 3.3）
2. **工具执行**: 暂时顺序执行，Task 2.1 会改为智能并行
3. **RAG 注入**: 暂时保留原有逻辑，Task 1.3 会修复

### 潜在问题

1. **性能**: 流式可能引入轻微延迟，需要性能测试
2. **错误处理**: 确保错误正确传播到事件流
3. **内存**: 大量事件可能占用内存，需要考虑事件限流

---

**创建日期**: 2025-10-25
**预计开始**: 2025-10-26
**预计完成**: 2025-10-27
