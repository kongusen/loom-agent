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

### API 选择

Loom v0.0.5 推荐统一使用：

- **`loom.agent()`**（推荐）
  - 一致的 v0.0.5 能力与默认安全/控制特性
  - 支持 `compressor` 与高级选项
  - 适合原型与生产环境

### 基础使用

```python
import asyncio
from loom import agent
from loom.builtin.llms import OpenAILLM

async def main():
    # 创建 Agent（自动启用递归控制和上下文管理）
    my_agent = agent(
        llm=OpenAILLM(model="gpt-4"),
        tools={}
    )

    # 运行任务
    result = await my_agent.run("Hello, how are you?")
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
from loom.core.unified_coordination import CoordinationConfig

# 使用 CoordinationConfig 配置上下文管理
config = CoordinationConfig(
    deep_recursion_threshold=3,      # 深度递归阈值
    high_complexity_threshold=0.7,   # 高复杂度阈值
    max_execution_time=30.0,         # 最大执行时间
    max_token_usage=0.8              # 最大 token 使用率
)

agent = loom_agent(
    llm=OpenAILLM(model="gpt-4"),
    tools={"search": SearchTool()},
    config=config,
    max_iterations=50                # 最大迭代次数
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
from loom.core.unified_coordination import CoordinationConfig

config = CoordinationConfig(
    deep_recursion_threshold=3,      # 深度递归阈值
    high_complexity_threshold=0.7,   # 高复杂度阈值
    max_subagent_count=3             # 最大子代理数量
)

agent = loom_agent(
    llm=llm,
    tools=tools,
    config=config,
    max_iterations=50                # 最大迭代次数
)
```

### 自定义配置

根据任务需求调整阈值：

```python
from loom.core.unified_coordination import CoordinationConfig

# 严格模式（快速检测循环）
strict_config = CoordinationConfig(
    deep_recursion_threshold=2,      # 更低的递归深度阈值
    high_complexity_threshold=0.5,   # 更低的复杂度阈值
    max_execution_time=15.0,         # 更短的最大执行时间
    max_subagent_count=1             # 限制子代理数量
)

agent = loom_agent(
    llm=llm,
    tools=tools,
    config=strict_config,
    max_iterations=20                # 较低的最大迭代
)

# 宽松模式（允许更多尝试）
lenient_config = CoordinationConfig(
    deep_recursion_threshold=5,      # 更高的递归深度阈值
    high_complexity_threshold=0.8,   # 更高的复杂度阈值
    max_execution_time=60.0,         # 更长的最大执行时间
    max_subagent_count=5             # 允许更多子代理
)

agent = loom_agent(
    llm=llm,
    tools=tools,
    config=lenient_config,
    max_iterations=100               # 更高的最大迭代
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

### 调整递归控制

通过 `CoordinationConfig` 调整递归控制行为：

```python
from loom.core.unified_coordination import CoordinationConfig

# 更严格的递归控制
config = CoordinationConfig(
    deep_recursion_threshold=2,      # 深度为2时即触发
    high_complexity_threshold=0.5    # 复杂度阈值更低
)

agent = loom_agent(
    llm=llm,
    tools=tools,
    config=config
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

### 配置上下文管理

通过 `CoordinationConfig` 配置上下文管理策略：

```python
from loom.core.unified_coordination import CoordinationConfig

config = CoordinationConfig(
    deep_recursion_threshold=3,      # 深度递归阈值
    high_complexity_threshold=0.7,   # 高复杂度阈值
    context_cache_size=100,           # 上下文组件缓存大小
    max_token_usage=0.8              # 最大 token 使用率
)

agent = loom_agent(
    llm=llm,
    tools=tools,
    config=config,
    max_iterations=50
)

# 自动功能：
# - 工具结果保证传递到下一轮
# - Token 使用率监控
# - 递归深度 > threshold 时调整策略
# - 智能上下文组装
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

### 1. 自定义 CoordinationConfig

```python
from loom.core.unified_coordination import CoordinationConfig

# 创建自定义配置
config = CoordinationConfig(
    # 任务分析阈值
    deep_recursion_threshold=3,      # 深度递归阈值
    high_complexity_threshold=0.7,    # 高复杂度阈值
    completion_score_threshold=0.8,  # 任务完成度阈值
    
    # 缓存配置
    context_cache_size=200,           # 上下文组件缓存大小（增加到200）
    subagent_pool_size=10,            # 子代理池大小（增加到10）
    
    # 事件处理配置
    event_batch_size=20,              # 事件批处理大小（增加到20）
    event_batch_timeout=0.1,          # 事件批处理超时时间（增加到0.1秒）
    
    # 性能目标
    max_execution_time=60.0,          # 最大执行时间（增加到60秒）
    max_token_usage=0.9,              # 最大 token 使用率（增加到90%）
    min_cache_hit_rate=0.5,           # 最小缓存命中率（降低到50%）
    max_subagent_count=5             # 最大子代理数量（增加到5）
)

# 使用自定义配置
agent = loom_agent(
    llm=llm,
    tools=tools,
    config=config
)
```

### 2. 组合配置优化

```python
from loom.core.unified_coordination import CoordinationConfig

# 创建优化的配置
config = CoordinationConfig(
    # 递归控制
    deep_recursion_threshold=3,      # 深度递归阈值
    high_complexity_threshold=0.7,    # 高复杂度阈值
    
    # 上下文管理
    context_cache_size=150,           # 上下文缓存大小
    max_token_usage=0.85,             # 最大 token 使用率
    
    # 事件处理
    event_batch_size=15,              # 事件批处理大小
    event_batch_timeout=0.05,         # 事件批处理超时
    
    # 性能目标
    max_execution_time=30.0,          # 最大执行时间
    max_subagent_count=3              # 最大子代理数量
)

# 使用优化配置
agent = loom_agent(
    llm=OpenAILLM(model="gpt-4"),
    tools=tools,
    config=config,
    max_iterations=30                 # 最大迭代次数
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
from loom.core.unified_coordination import CoordinationConfig

# 短时任务（快速响应）
quick_config = CoordinationConfig(
    deep_recursion_threshold=2,      # 较低的递归深度阈值
    high_complexity_threshold=0.5,   # 较低的复杂度阈值
    max_execution_time=10.0,         # 较短的最大执行时间
    max_subagent_count=1             # 限制子代理数量
)

# 复杂任务（允许更多尝试）
complex_config = CoordinationConfig(
    deep_recursion_threshold=5,      # 较高的递归深度阈值
    high_complexity_threshold=0.8,   # 较高的复杂度阈值
    max_execution_time=60.0,         # 较长的最大执行时间
    max_subagent_count=5             # 允许更多子代理
)

# 研究任务（最大灵活性）
research_config = CoordinationConfig(
    deep_recursion_threshold=10,      # 很高的递归深度阈值
    high_complexity_threshold=0.9,   # 很高的复杂度阈值
    max_execution_time=120.0,        # 很长的最大执行时间
    max_subagent_count=10            # 允许大量子代理
)
```

### 2. Token 限制设置

```python
from loom.core.unified_coordination import CoordinationConfig

# 根据 LLM 模型设置合理的配置
model_configs = {
    "gpt-3.5-turbo": CoordinationConfig(
        max_token_usage=0.7,         # 4K 上下文，使用70%
        context_cache_size=50        # 较小的缓存
    ),
    "gpt-4": CoordinationConfig(
        max_token_usage=0.8,         # 8K 上下文，使用80%
        context_cache_size=100        # 中等缓存
    ),
    "gpt-4-32k": CoordinationConfig(
        max_token_usage=0.85,        # 32K 上下文，使用85%
        context_cache_size=200        # 较大缓存
    ),
    "claude-2": CoordinationConfig(
        max_token_usage=0.9,         # 100K 上下文，使用90%
        context_cache_size=500        # 很大缓存
    ),
}

model = "gpt-4"
agent = loom_agent(
    llm=OpenAILLM(model=model),
    tools=tools,
    config=model_configs[model],
    max_iterations=50
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
from loom.core.unified_coordination import CoordinationConfig

# 1. 使用并行工具执行（只读工具）
class SearchTool(BaseTool):
    is_read_only = True  # 标记为只读，允许并行

# 2. 根据任务复杂度调整配置
if task_is_simple:
    config = CoordinationConfig(
        deep_recursion_threshold=2,
        max_subagent_count=1,
        max_execution_time=10.0
    )
    max_iterations = 10
elif task_is_complex:
    config = CoordinationConfig(
        deep_recursion_threshold=5,
        max_subagent_count=5,
        max_execution_time=60.0,
        context_cache_size=200
    )
    max_iterations = 50
else:
    config = CoordinationConfig(
        deep_recursion_threshold=3,
        max_subagent_count=3,
        max_execution_time=30.0
    )
    max_iterations = 30

agent = loom_agent(
    llm=llm,
    tools=tools,
    config=config,
    max_iterations=max_iterations
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
