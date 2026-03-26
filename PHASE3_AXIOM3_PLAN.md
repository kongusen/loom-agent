# Phase 3: 公理三信息增益门控实施方案

## 目标
将信息增益门控从"可选钩子"升级为"全链路默认机制"，过滤冗余输出。

---

## 3.1 核心变更：Agent 内部全部使用 publish_with_gain

### 当前问题
```python
# Agent 内部直接 emit
await self.event_bus.emit(TextDeltaEvent(text=chunk))
await self.event_bus.emit(ToolCallEvent(...))
```

**问题：**
- 所有事件无条件发布
- 冗余信息未过滤

### 新实现
```python
async def _emit_with_gain(self, event: AgentEvent, payload: str = "") -> bool:
    """带信息增益门控的事件发布"""

    # 获取当前上下文（用于计算 ΔH）
    context = self.partition_mgr.get_context()

    # 使用门控发布
    published = await self.event_bus.publish_with_gain(
        event,
        payload=payload or str(event),
        context=context
    )

    return published
```

### 替换所有 emit 调用
```python
# 之前
await self.event_bus.emit(TextDeltaEvent(text=chunk))

# 之后
await self._emit_with_gain(TextDeltaEvent(text=chunk), payload=chunk)
```

---

## 3.2 工具输出 ΔH 过滤

### 新增：_filter_tool_output()
```python
async def _filter_tool_output(self, tool_name: str, raw_output: str) -> str:
    """过滤工具输出的冗余信息"""

    # 获取当前上下文
    context = self.partition_mgr.get_context()

    # 计算信息增益
    delta_h = self.event_bus.info_calc.calculate_delta_h(raw_output, context)

    # 低增益：截断或总结
    if delta_h < 0.1:
        return f"[Tool {tool_name} executed, output redundant]"

    # 中等增益：保留关键部分
    if delta_h < 0.3:
        return self._summarize_output(raw_output, max_tokens=200)

    # 高增益：完整保留
    return raw_output

def _summarize_output(self, text: str, max_tokens: int) -> str:
    """总结输出（简单截断，可升级为 LLM 总结）"""
    truncated = self.tokenizer.truncate(text, max_tokens)
    if len(truncated) < len(text):
        return truncated + "\n[... output truncated for brevity]"
    return text
```

### 集成到工具执行
```python
async def _execute_tool(self, tc: ToolCall) -> str:
    """执行工具（带输出过滤）"""

    ctx = ToolContext(agent_id=self.id)
    raw_result = await self.tools.execute(tc, ctx, self.constraint_validator)

    # 公理三：过滤冗余输出
    filtered_result = await self._filter_tool_output(tc.name, raw_result)

    # 记录
    self._execution_trace.append(f"{tc.name} → {filtered_result[:100]}")

    # 更新 working
    working_content = self._build_working_state()
    self.partition_mgr.update_partition("working", working_content)

    return filtered_result
```

---

## 3.3 LLM 流式输出累积门控

### 新增：StreamGatingBuffer
```python
class StreamGatingBuffer:
    """流式输出的信息增益累积器"""

    def __init__(self, info_calc: InformationGainCalculator, threshold: float = 0.05):
        self.info_calc = info_calc
        self.threshold = threshold
        self.buffer = ""
        self.context = ""
        self.total_gain = 0.0

    def add_chunk(self, chunk: str, context: str) -> tuple[bool, str]:
        """添加 chunk，返回 (should_emit, accumulated_text)"""
        self.buffer += chunk
        self.context = context

        # 计算累积增益
        delta_h = self.info_calc.calculate_delta_h(self.buffer, context)

        # 增益足够：发布并清空
        if delta_h >= self.threshold:
            text = self.buffer
            self.buffer = ""
            self.total_gain += delta_h
            return True, text

        # 增益不足：继续累积
        return False, ""

    def flush(self) -> str:
        """强制输出剩余内容"""
        text = self.buffer
        self.buffer = ""
        return text
```

### 集成到流式处理
```python
async def run(self, user_input: str, goal: str = "") -> AsyncGenerator[AgentEvent, None]:
    """主循环（带流式门控）"""

    # 初始化门控缓冲
    stream_buffer = StreamGatingBuffer(self.event_bus.info_calc)

    # ... 构建消息

    # 流式调用
    async for chunk in self.provider.stream(params):
        context = self.partition_mgr.get_context()
        should_emit, text = stream_buffer.add_chunk(chunk.text, context)

        if should_emit:
            # 只发布高增益的累积文本
            await self._emit_with_gain(TextDeltaEvent(text=text), payload=text)

    # 刷新剩余
    remaining = stream_buffer.flush()
    if remaining:
        await self._emit_with_gain(TextDeltaEvent(text=remaining), payload=remaining)
```

---

## 3.4 配置化门控阈值

### 新增：GatingConfig
```python
# loom/config/gating.py

@dataclass
class GatingConfig:
    """信息增益门控配置"""

    # 事件发布阈值
    event_threshold: float = 0.1

    # 工具输出阈值
    tool_output_low: float = 0.1   # 低于此值：丢弃
    tool_output_mid: float = 0.3   # 低于此值：总结

    # 流式输出阈值
    stream_threshold: float = 0.05

    # 是否启用门控
    enabled: bool = True
```

### Agent 集成
```python
def __init__(self, ..., gating_config: GatingConfig | None = None):
    # ...
    self.gating_config = gating_config or GatingConfig()

    # 配置 EventBus 阈值
    self.event_bus.info_calc.threshold = self.gating_config.event_threshold
```

---

## 3.5 测试验证

```python
# tests/unit/test_gating_integration.py

async def test_low_gain_event_not_published():
    """验证低增益事件被过滤"""
    agent = Agent(provider=MockProvider())

    # 设置高阈值
    agent.gating_config.event_threshold = 0.5

    published_events = []
    agent.event_bus.on_all(lambda e: published_events.append(e))

    # 发布低增益事件（重复内容）
    await agent._emit_with_gain(
        TextDeltaEvent(text="hello"),
        payload="hello"
    )
    await agent._emit_with_gain(
        TextDeltaEvent(text="hello"),  # 重复
        payload="hello"
    )

    # 第二次应被过滤
    assert len(published_events) == 1

async def test_tool_output_filtered():
    """验证工具输出被过滤"""
    agent = Agent(provider=MockProvider())

    # 模拟冗余输出
    redundant_output = "OK\n" * 100  # 重复内容

    filtered = await agent._filter_tool_output("test_tool", redundant_output)

    # 应被截断或标记为冗余
    assert len(filtered) < len(redundant_output)

async def test_stream_gating_accumulates():
    """验证流式输出累积门控"""
    buffer = StreamGatingBuffer(InformationGainCalculator(), threshold=0.1)

    # 添加小 chunk（增益不足）
    should_emit, _ = buffer.add_chunk("a", "context")
    assert not should_emit

    # 继续添加直到增益足够
    for char in "bcdefghij":
        should_emit, text = buffer.add_chunk(char, "context")
        if should_emit:
            assert len(text) > 1  # 累积了多个字符
            break
```

---

## 3.6 实施检查清单

- [ ] 实现 `_emit_with_gain()` 方法
- [ ] 替换所有 `emit()` 为 `_emit_with_gain()`
- [ ] 实现 `_filter_tool_output()` 和 `_summarize_output()`
- [ ] 集成工具输出过滤到 `_execute_tool()`
- [ ] 实现 StreamGatingBuffer 类
- [ ] 集成流式门控到 `run()` 方法
- [ ] 添加 GatingConfig 配置类
- [ ] 编写门控集成测试
- [ ] 验证冗余输出被正确过滤

---

**下一步：Phase 4 公理四进化闭环方案**
