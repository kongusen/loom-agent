# 上下文管理 (Context Management)

## 定义

**上下文管理**是智能构建 LLM 上下文的系统，自动管理 Token 预算和信息优先级。

## 核心问题

LLM 的上下文窗口有限：
- GPT-3.5: 4K/16K tokens
- GPT-4: 8K/32K tokens
- Claude-3: 200K tokens

但相关信息可能很多，需要智能选择。

## 解决方案

### 1. 多源上下文

```python
from loom.memory.task_context import TaskContextManager

sources = [
    MemoryContextSource(memory),      # 从记忆检索
    EventBusContextSource(event_bus)  # 从事件检索
]

context_manager = TaskContextManager(
    sources=sources,
    max_tokens=4000  # Token 预算
)
```

### 2. 智能分配

```python
# 自动构建上下文
messages = await context_manager.build_context(task)

# 内部逻辑：
# 1. 添加系统提示词 (system)
# 2. 从记忆检索相关内容 (user/assistant)
# 3. 添加当前任务 (user)
# 4. Token 超限时自动压缩
```

### 3. Ephemeral 过滤

```python
# 标记大输出的工具为 ephemeral
tool = {
    "name": "web_search",
    "_ephemeral": 2  # 只保留最近 2 次输出
}

# Agent 自动过滤旧的 ephemeral 工具输出
```

## 相关概念

- → [代谢记忆](Metabolic-Memory)
- → [记忆分层](Memory-Layers)

## 代码位置

- `loom/memory/task_context.py`

## 反向链接

被引用于: [Agent API](API-Agent) | [代谢记忆](Metabolic-Memory)
