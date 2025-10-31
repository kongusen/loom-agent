# Loom Agent v0.0.5 使用指南

## 目录

1. [快速开始](#快速开始)
2. [核心功能](#核心功能)
3. [递归控制](#递归控制)
4. [上下文管理](#上下文管理)
5. [事件系统](#事件系统)
6. [工具系统](#工具系统)
7. [高级用法](#高级用法)
8. [最佳实践](#最佳实践)

---

## 快速开始

### 安装

```bash
pip install loom-agent[openai]
```

### 基础使用

```python
import asyncio
from loom.api.v0_0_3 import loom_agent
from loom.builtin.llms import OpenAILLM

async def main():
    # 创建 Agent（自动启用递归控制和上下文管理）
    agent = loom_agent(
        llm=OpenAILLM(model="gpt-4"),
        tools={}
    )

    # 运行任务
    result = await agent.run("Hello, how are you?")
    print(result)

asyncio.run(main())
```

---

## 核心功能

### 1. 自动递归控制（Phase 2）

Loom v0.0.4 自动检测和防止无限循环：

```python
from loom.api.v0_0_3 import loom_agent
from loom.builtin.llms import OpenAILLM

# 默认启用递归控制
agent = loom_agent(
    llm=OpenAILLM(model="gpt-4"),
    tools={"search": SearchTool()}
)

# 自动检测：
# - 重复工具调用（同一工具被连续调用）
# - 循环模式（输出重复）
# - 错误率过高
# - 迭代次数超限

result = await agent.run("Complex task")
```

**检测条件：**
- 重复工具调用：同一工具连续调用 3 次（可配置）
- 循环模式：输出模式在 5 个窗口内重复（可配置）
- 错误率：错误率超过 50%（可配置）
- 最大迭代：默认 50 次（可配置）

### 2. 智能上下文管理（Phase 3）

自动管理消息上下文，确保工具结果传递：

```python
from loom.builtin.compressor import SimpleCompressor

agent = loom_agent(
    llm=OpenAILLM(model="gpt-4"),
    tools={"search": SearchTool()},
    compressor=SimpleCompressor(),    # 启用压缩
    max_context_tokens=8000            # Token 限制
)

# 自动功能：
# - 工具结果保证传递到下一轮
# - Token 超限时自动压缩
# - 递归深度 > 3 时添加提示
# - 实时 Token 估算

result = await agent.run("Long multi-step task")
```

---

## 递归控制

### 默认配置

递归控制默认启用，使用合理的默认值：

```python
# 默认配置（无需显式设置）
agent = loom_agent(llm=llm, tools=tools)

# 等同于：
from loom.core.recursion_control import RecursionMonitor

agent = loom_agent(
    llm=llm,
    tools=tools,
    enable_recursion_control=True,  # 默认启用
    recursion_monitor=RecursionMonitor(
        max_iterations=50,          # 最大迭代次数
        duplicate_threshold=3,      # 重复工具阈值
        loop_detection_window=5,    # 循环检测窗口
        error_threshold=0.5         # 错误率阈值
    )
)
```

### 自定义配置

根据任务需求调整阈值：

```python
from loom.core.recursion_control import RecursionMonitor

# 严格模式（快速检测循环）
strict_monitor = RecursionMonitor(
    max_iterations=20,       # 较低的最大迭代
    duplicate_threshold=2,   # 2次重复即终止
    error_threshold=0.3      # 更低的错误容忍度
)

agent = loom_agent(
    llm=llm,
    tools=tools,
    recursion_monitor=strict_monitor
)

# 宽松模式（允许更多尝试）
lenient_monitor = RecursionMonitor(
    max_iterations=100,      # 更高的最大迭代
    duplicate_threshold=5,   # 允许更多重复
    error_threshold=0.7      # 更高的错误容忍度
)
```

### 监控递归事件

```python
from loom.core.events import AgentEventType

async for event in agent.stream("Complex task"):
    if event.type == AgentEventType.RECURSION_TERMINATED:
        # 递归被终止
        reason = event.metadata["reason"]
        iteration = event.metadata["iteration"]
        tool_history = event.metadata["tool_call_history"]

        print(f"⚠️ 递归终止")
        print(f"   原因: {reason}")
        print(f"   迭代: {iteration}")
        print(f"   工具历史: {tool_history[-5:]}")
```

### 禁用递归控制

某些场景下可能需要禁用：

```python
agent = loom_agent(
    llm=llm,
    tools=tools,
    enable_recursion_control=False  # 完全禁用
)
```

---

## 上下文管理

### 默认行为

上下文管理自动处理消息传递：

```python
# 默认行为（无需配置）
agent = loom_agent(llm=llm, tools=tools)

# 自动执行：
# 1. 工具结果添加到下一轮消息
# 2. 估算 Token 使用量
# 3. 检查是否超过 max_context_tokens
# 4. 深度 > 3 时添加递归提示
```

### 启用自动压缩

长时间对话或多步任务建议启用压缩：

```python
from loom.builtin.compressor import SimpleCompressor

compressor = SimpleCompressor()

agent = loom_agent(
    llm=llm,
    tools=tools,
    compressor=compressor,
    max_context_tokens=8000  # GPT-4 的合理限制
)

# 自动压缩触发条件：
# - 消息估算 Token 数 > max_context_tokens
# - 保留最近的消息和系统消息
# - 发出 COMPRESSION_APPLIED 事件
```

### 监控上下文事件

```python
async for event in agent.stream("Long task"):
    if event.type == AgentEventType.COMPRESSION_APPLIED:
        # 上下文被压缩
        tokens_before = event.metadata["tokens_before"]
        tokens_after = event.metadata["tokens_after"]
        saved = tokens_before - tokens_after

        print(f"📉 上下文压缩")
        print(f"   压缩前: {tokens_before} tokens")
        print(f"   压缩后: {tokens_after} tokens")
        print(f"   节省: {saved} tokens ({saved/tokens_before*100:.0f}%)")

    elif event.type == AgentEventType.RECURSION:
        # 递归调用
        depth = event.metadata["depth"]
        message_count = event.metadata["message_count"]

        print(f"🔄 递归 {depth}")
        print(f"   消息数: {message_count}")
```

### 递归深度提示

深度超过 3 时，自动添加提示帮助 LLM：

```python
# 深度 4 时的自动提示示例：
"""
🔄 Recursion Status:
- Depth: 4/50 (8% of maximum)
- Remaining iterations: 46

Please review the tool results above and make meaningful progress
towards completing the task. Avoid calling the same tool repeatedly
with the same arguments unless necessary. If you have enough
information, please provide your final answer.
"""
```

---

## 事件系统

### 所有事件类型

```python
from loom.core.events import AgentEventType

# 迭代事件
AgentEventType.ITERATION_START      # 迭代开始
AgentEventType.ITERATION_END        # 迭代结束

# 递归控制事件
AgentEventType.RECURSION_TERMINATED # 递归终止（NEW）

# 上下文管理事件
AgentEventType.COMPRESSION_APPLIED  # 压缩应用（NEW）

# LLM 事件
AgentEventType.LLM_START           # LLM 调用开始
AgentEventType.LLM_DELTA           # 流式输出
AgentEventType.LLM_COMPLETE        # LLM 调用完成
AgentEventType.LLM_TOOL_CALLS      # LLM 请求工具调用

# 工具事件
AgentEventType.TOOL_CALLS_START     # 工具调用开始
AgentEventType.TOOL_EXECUTION_START # 单个工具开始
AgentEventType.TOOL_PROGRESS        # 工具进度
AgentEventType.TOOL_RESULT          # 工具结果
AgentEventType.TOOL_ERROR           # 工具错误
AgentEventType.TOOL_CALLS_COMPLETE  # 所有工具完成

# Agent 事件
AgentEventType.RECURSION           # 递归调用（增强：包含 message_count）
AgentEventType.AGENT_FINISH        # Agent 完成
AgentEventType.MAX_ITERATIONS_REACHED  # 达到最大迭代次数
AgentEventType.ERROR               # 错误
```

### 事件流式处理

```python
async for event in agent.stream(prompt):
    match event.type:
        case AgentEventType.ITERATION_START:
            print(f"开始迭代 {event.iteration}")

        case AgentEventType.LLM_DELTA:
            print(event.content, end="", flush=True)

        case AgentEventType.TOOL_EXECUTION_START:
            tool_name = event.metadata.get("tool_name", "unknown")
            print(f"\n调用工具: {tool_name}")

        case AgentEventType.TOOL_RESULT:
            content = event.tool_result.content
            print(f"工具结果: {content[:100]}...")

        case AgentEventType.RECURSION_TERMINATED:
            reason = event.metadata["reason"]
            print(f"\n⚠️ 检测到循环: {reason}")

        case AgentEventType.COMPRESSION_APPLIED:
            saved = event.metadata["tokens_before"] - event.metadata["tokens_after"]
            print(f"\n📉 压缩节省 {saved} tokens")

        case AgentEventType.AGENT_FINISH:
            print(f"\n✅ 完成: {event.content}")
```

### 事件收集器

```python
from loom.core.events import EventCollector

collector = EventCollector()

async for event in agent.stream(prompt):
    collector.add(event)

# 分析事件
llm_content = collector.get_llm_content()      # 重建完整 LLM 输出
tool_results = collector.get_tool_results()    # 获取所有工具结果
errors = collector.get_errors()                # 获取所有错误
final_response = collector.get_final_response()  # 获取最终响应

print(f"LLM 生成: {llm_content}")
print(f"工具调用: {len(tool_results)} 次")
print(f"错误: {len(errors)} 个")
print(f"最终结果: {final_response}")
```

---

## 工具系统

### 创建工具

```python
from loom import tool
from pydantic import BaseModel, Field

# 方式 1: 使用装饰器
@tool(description="搜索信息")
async def search(query: str) -> str:
    """搜索信息"""
    # 实现搜索逻辑
    return f"搜索结果: {query}"

# 方式 2: 使用 Pydantic 参数模型
class SearchArgs(BaseModel):
    query: str = Field(description="搜索查询")
    max_results: int = Field(default=10, description="最大结果数")

@tool(description="高级搜索")
async def advanced_search(query: str, max_results: int = 10) -> dict:
    """执行高级搜索"""
    return {
        "query": query,
        "results": ["result1", "result2"],
        "count": max_results
    }

# 使用工具
agent = loom_agent(
    llm=llm,
    tools={
        "search": search(),
        "advanced_search": advanced_search()
    }
)
```

### 工具元数据

```python
from loom.interfaces.tool import BaseTool

class CustomTool(BaseTool):
    name: str = "custom_tool"
    description: str = "自定义工具"
    args_schema: type[BaseModel] = CustomToolArgs

    # 新增元数据（Loom 0.0.3+）
    is_read_only: bool = True        # 只读工具（可并行）
    category: str = "general"        # 类别
    requires_confirmation: bool = False  # 是否需要确认

    async def run(self, **kwargs) -> str:
        return "工具执行结果"
```

### 工具执行监控

```python
async for event in agent.stream(prompt):
    if event.type == AgentEventType.TOOL_EXECUTION_START:
        tool_name = event.metadata["tool_name"]
        print(f"🔧 开始: {tool_name}")

    elif event.type == AgentEventType.TOOL_RESULT:
        result = event.tool_result
        print(f"✅ 完成: {result.tool_name}")
        print(f"   结果: {result.content[:100]}")
        print(f"   耗时: {result.execution_time_ms}ms")

    elif event.type == AgentEventType.TOOL_ERROR:
        result = event.tool_result
        print(f"❌ 错误: {result.tool_name}")
        print(f"   信息: {result.content}")
```

---

## 高级用法

### 1. 自定义 Compressor

```python
from loom.interfaces.compressor import BaseCompressor
from loom.core.types import Message

class CustomCompressor(BaseCompressor):
    def should_compress(self, current_tokens: int, max_tokens: int) -> bool:
        """判断是否需要压缩"""
        return current_tokens > max_tokens * 0.8  # 80% 时触发

    async def compress(self, messages: List[Message]):
        """执行压缩"""
        # 自定义压缩逻辑
        # 例如：保留系统消息和最近 N 条消息
        system_msgs = [m for m in messages if m.role == "system"]
        recent_msgs = [m for m in messages if m.role != "system"][-5:]

        compressed = system_msgs + recent_msgs

        metadata = CompressorMetadata(
            original_tokens=len(messages) * 100,  # 估算
            compressed_tokens=len(compressed) * 100,
            compression_ratio=len(compressed) / len(messages),
            original_message_count=len(messages),
            compressed_message_count=len(compressed),
            key_topics=["topic1", "topic2"]
        )

        return compressed, metadata

# 使用自定义 compressor
agent = loom_agent(
    llm=llm,
    tools=tools,
    compressor=CustomCompressor()
)
```

### 2. 组合 Phase 2 和 Phase 3

```python
from loom.core.recursion_control import RecursionMonitor
from loom.builtin.compressor import SimpleCompressor

# 创建严格的递归控制
monitor = RecursionMonitor(
    max_iterations=30,
    duplicate_threshold=2,
    error_threshold=0.3
)

# 创建压缩器
compressor = SimpleCompressor()

# 组合使用
agent = loom_agent(
    llm=OpenAILLM(model="gpt-4"),
    tools=tools,
    # 递归控制
    recursion_monitor=monitor,
    enable_recursion_control=True,
    # 上下文管理
    compressor=compressor,
    max_context_tokens=6000
)

# 监控所有优化
async for event in agent.stream("Complex long task"):
    if event.type == AgentEventType.RECURSION_TERMINATED:
        print(f"⚠️ 循环检测: {event.metadata['reason']}")

    elif event.type == AgentEventType.COMPRESSION_APPLIED:
        print(f"📉 上下文压缩")

    elif event.type == AgentEventType.AGENT_FINISH:
        print(f"✅ 完成: {event.content}")
```

### 3. 实时统计

```python
from dataclasses import dataclass

@dataclass
class ExecutionStats:
    iterations: int = 0
    tool_calls: int = 0
    compressions: int = 0
    terminations: int = 0
    tokens_saved: int = 0

stats = ExecutionStats()

async for event in agent.stream(prompt):
    if event.type == AgentEventType.ITERATION_START:
        stats.iterations += 1

    elif event.type == AgentEventType.TOOL_RESULT:
        stats.tool_calls += 1

    elif event.type == AgentEventType.COMPRESSION_APPLIED:
        stats.compressions += 1
        stats.tokens_saved += (
            event.metadata["tokens_before"] -
            event.metadata["tokens_after"]
        )

    elif event.type == AgentEventType.RECURSION_TERMINATED:
        stats.terminations += 1

    elif event.type == AgentEventType.AGENT_FINISH:
        print(f"\n📊 执行统计:")
        print(f"   迭代次数: {stats.iterations}")
        print(f"   工具调用: {stats.tool_calls}")
        print(f"   压缩次数: {stats.compressions}")
        print(f"   终止次数: {stats.terminations}")
        print(f"   节省 Token: {stats.tokens_saved}")
```

---

## 最佳实践

### 1. 递归控制配置

```python
# 短时任务（快速响应）
quick_monitor = RecursionMonitor(
    max_iterations=10,
    duplicate_threshold=2
)

# 复杂任务（允许更多尝试）
complex_monitor = RecursionMonitor(
    max_iterations=50,
    duplicate_threshold=4,
    error_threshold=0.6
)

# 研究任务（最大灵活性）
research_monitor = RecursionMonitor(
    max_iterations=100,
    duplicate_threshold=5,
    error_threshold=0.7
)
```

### 2. Token 限制设置

```python
# 根据 LLM 模型设置合理的限制
token_limits = {
    "gpt-3.5-turbo": 4000,      # 4K 上下文
    "gpt-4": 8000,               # 8K 上下文
    "gpt-4-32k": 32000,          # 32K 上下文
    "claude-2": 100000,          # 100K 上下文
}

model = "gpt-4"
agent = loom_agent(
    llm=OpenAILLM(model=model),
    tools=tools,
    compressor=SimpleCompressor(),
    max_context_tokens=token_limits[model]
)
```

### 3. 错误处理

```python
from loom.core.events import AgentEventType

try:
    async for event in agent.stream(prompt):
        if event.type == AgentEventType.ERROR:
            error = event.error
            print(f"错误: {error}")
            # 根据错误类型处理

        elif event.type == AgentEventType.TOOL_ERROR:
            tool_name = event.tool_result.tool_name
            error_msg = event.tool_result.content
            print(f"工具 {tool_name} 错误: {error_msg}")
            # 继续执行或中断

        elif event.type == AgentEventType.RECURSION_TERMINATED:
            reason = event.metadata["reason"]
            # 记录循环检测
            print(f"检测到循环: {reason}")

except Exception as e:
    print(f"执行异常: {e}")
```

### 4. 性能优化

```python
# 1. 使用并行工具执行（只读工具）
class SearchTool(BaseTool):
    is_read_only = True  # 标记为只读，允许并行

# 2. 启用压缩（长对话）
if expected_iterations > 10:
    compressor = SimpleCompressor()
else:
    compressor = None

# 3. 调整递归阈值
if task_is_simple:
    max_iterations = 10
elif task_is_complex:
    max_iterations = 50
else:
    max_iterations = 30

agent = loom_agent(
    llm=llm,
    tools=tools,
    compressor=compressor,
    recursion_monitor=RecursionMonitor(max_iterations=max_iterations)
)
```

### 5. 监控和调试

```python
import logging

# 启用日志
logging.basicConfig(level=logging.INFO)

# 收集详细事件
events = []
async for event in agent.stream(prompt):
    events.append(event)

    # 实时输出关键事件
    if event.type in [
        AgentEventType.RECURSION_TERMINATED,
        AgentEventType.COMPRESSION_APPLIED,
        AgentEventType.TOOL_ERROR,
        AgentEventType.ERROR
    ]:
        print(f"[{event.type.value}] {event.metadata}")

# 事后分析
print(f"\n总事件数: {len(events)}")
print(f"迭代次数: {len([e for e in events if e.type == AgentEventType.ITERATION_START])}")
print(f"工具调用: {len([e for e in events if e.type == AgentEventType.TOOL_RESULT])}")
```

---

## 总结

Loom Agent v0.0.5 提供了两大核心优化：

1. **递归控制** - 自动检测和防止无限循环
2. **上下文管理** - 智能管理消息传递和压缩

这些功能：
- ✅ 默认启用，无需配置
- ✅ 100% 向后兼容
- ✅ 可通过事件监控
- ✅ 完全可配置
- ✅ 性能开销 < 5ms

立即开始使用，享受更稳定、更智能的 AI Agent 开发体验！
