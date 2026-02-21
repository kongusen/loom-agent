# Memory

三层记忆系统让 Agent 具备多轮对话上下文能力。

## 三层架构

| 层级 | 类 | 作用 |
|------|-----|------|
| L1 | `SlidingWindow` | 滑动窗口，保存近期对话消息 |
| L2 | `WorkingMemory` | 工作记忆，按重要性存储关键信息 |
| L3 | `PersistentStore` | 持久化存储，长期记忆 |

## 基础用法

```python
from loom import Agent, AgentConfig, MemoryManager
from loom import SlidingWindow, WorkingMemory

memory = MemoryManager(
    l1=SlidingWindow(token_budget=2000),
    l2=WorkingMemory(token_budget=500),
)

agent = Agent(
    provider=provider,
    config=AgentConfig(max_steps=2),
    memory=memory,
)
```

## 效果对比

无记忆 Agent 每轮独立，无法关联上下文：

```python
# 无记忆 — 无法记住上文
agent1 = Agent(provider=provider, config=AgentConfig(max_steps=2))
await agent1.run("我叫小明，我是Python开发者")
r1 = await agent1.run("我叫什么名字？")
# → 无法回答（每轮独立）
```

有记忆 Agent 保持对话连贯：

```python
# 有记忆 — 记住上下文
agent2 = Agent(provider=provider, memory=memory)
await agent2.run("我叫小明，我是Python开发者")
r2 = await agent2.run("我叫什么名字？我的职业是什么？")
# → "你叫小明，职业是Python开发者"
```

## 查看记忆状态

```python
print(len(memory.l1.get_messages()))  # L1 消息数
l2_entries = await memory.l2.retrieve()
print(len(l2_entries))                # L2 条目数
```

## API 参考

```python
memory = MemoryManager(l1=..., l2=..., l3=...)
await memory.add_message(message)
memory.l1.get_messages() -> list[Message]
await memory.l2.retrieve() -> list[MemoryEntry]
```

> 完整示例：[`examples/demo/05_memory.py`](../examples/demo/05_memory.py)
