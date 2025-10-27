# Loom 0.0.3 API 暴露现状分析和改进方案

## 🔍 当前暴露状况分析

### ✅ 已暴露的能力

1. **基础 Agent API**
   ```python
   from loom import agent, Agent
   agent = agent(provider="openai", model="gpt-4o")
   ```

2. **工具系统**
   ```python
   from loom import tool
   @tool()
   def my_tool(): pass
   ```

3. **LLM 配置**
   ```python
   from loom import LLMConfig, LLMProvider
   ```

4. **基础组件**
   ```python
   from loom import InMemoryMemory, PersistentMemory
   ```

### ❌ 未完全暴露的 Loom 0.0.3 核心能力

1. **统一协调机制** - `UnifiedExecutionContext`, `IntelligentCoordinator`
2. **TT 递归执行** - `AgentExecutor.tt()` 方法
3. **事件流处理** - `AgentEvent`, `AgentEventType`
4. **智能上下文组装** - `ContextAssembler`
5. **任务处理器** - `TaskHandler`
6. **性能优化** - 缓存、批处理、blake2b 哈希

## 🚀 完整 API 暴露方案

### 1. 更新 `loom/__init__.py`

```python
# 现有导入
from .components.agent import Agent
from .agent import agent, agent_from_env
from .tooling import tool

# Loom 0.0.3 核心能力
from .core.agent_executor import AgentExecutor
from .core.unified_coordination import (
    UnifiedExecutionContext,
    IntelligentCoordinator,
    CoordinationConfig
)
from .core.events import AgentEvent, AgentEventType
from .core.turn_state import TurnState
from .core.execution_context import ExecutionContext
from .core.context_assembly import ContextAssembler, ComponentPriority
from .core.task_handler import TaskHandler

# 性能优化组件
from .core.caching import CacheManager
from .core.batch_processor import BatchProcessor

__all__ = [
    # 现有 API
    "Agent", "agent", "tool", "agent_from_env",
    
    # Loom 0.0.3 核心 API
    "AgentExecutor",
    "UnifiedExecutionContext", 
    "IntelligentCoordinator",
    "CoordinationConfig",
    "AgentEvent",
    "AgentEventType", 
    "TurnState",
    "ExecutionContext",
    "ContextAssembler",
    "ComponentPriority",
    "TaskHandler",
    
    # 性能优化 API
    "CacheManager",
    "BatchProcessor",
]
```

### 2. 创建 Loom 0.0.3 专用 API

```python
# loom/v0_0_3/__init__.py
"""
Loom 0.0.3 专用 API - 统一协调和性能优化
"""

from ..core.agent_executor import AgentExecutor
from ..core.unified_coordination import (
    UnifiedExecutionContext,
    IntelligentCoordinator, 
    CoordinationConfig
)
from ..core.events import AgentEvent, AgentEventType
from ..core.turn_state import TurnState
from ..core.execution_context import ExecutionContext
from ..core.context_assembly import ContextAssembler, ComponentPriority
from ..core.task_handler import TaskHandler

def create_unified_agent(
    llm,
    tools=None,
    config=None,
    execution_id=None,
    **kwargs
):
    """创建使用统一协调机制的 Agent"""
    if config is None:
        config = CoordinationConfig()
    
    unified_context = UnifiedExecutionContext(
        execution_id=execution_id or f"agent_{int(time.time())}",
        config=config
    )
    
    return AgentExecutor(
        llm=llm,
        tools=tools or {},
        unified_context=unified_context,
        enable_unified_coordination=True,
        **kwargs
    )

def create_tt_executor(
    llm,
    tools=None,
    max_iterations=50,
    **kwargs
):
    """创建支持 TT 递归执行的 AgentExecutor"""
    return AgentExecutor(
        llm=llm,
        tools=tools or {},
        max_iterations=max_iterations,
        **kwargs
    )

__all__ = [
    "AgentExecutor",
    "UnifiedExecutionContext",
    "IntelligentCoordinator", 
    "CoordinationConfig",
    "AgentEvent",
    "AgentEventType",
    "TurnState", 
    "ExecutionContext",
    "ContextAssembler",
    "ComponentPriority",
    "TaskHandler",
    "create_unified_agent",
    "create_tt_executor",
]
```

### 3. 创建开发者友好的 API 包装器

```python
# loom/api/v0_0_3.py
"""
Loom 0.0.3 开发者 API - 简化统一协调使用
"""

import asyncio
from typing import List, Optional, Dict, Any, AsyncGenerator
from ..core.agent_executor import AgentExecutor
from ..core.unified_coordination import (
    UnifiedExecutionContext,
    IntelligentCoordinator,
    CoordinationConfig
)
from ..core.events import AgentEvent, AgentEventType
from ..core.turn_state import TurnState
from ..core.execution_context import ExecutionContext
from ..core.types import Message

class LoomAgent:
    """Loom 0.0.3 统一协调 Agent"""
    
    def __init__(
        self,
        llm,
        tools: Optional[Dict[str, Any]] = None,
        config: Optional[CoordinationConfig] = None,
        execution_id: Optional[str] = None,
        **kwargs
    ):
        self.config = config or CoordinationConfig()
        self.unified_context = UnifiedExecutionContext(
            execution_id=execution_id or f"loom_agent_{int(time.time())}",
            config=self.config
        )
        
        self.executor = AgentExecutor(
            llm=llm,
            tools=tools or {},
            unified_context=self.unified_context,
            enable_unified_coordination=True,
            **kwargs
        )
    
    async def run(self, input_text: str) -> str:
        """运行 Agent 并返回最终结果"""
        turn_state = TurnState.initial(max_iterations=self.executor.max_iterations)
        context = ExecutionContext.create(correlation_id=f"run_{int(time.time())}")
        messages = [Message(role="user", content=input_text)]
        
        final_content = ""
        async for event in self.executor.tt(messages, turn_state, context):
            if event.type == AgentEventType.AGENT_FINISH:
                final_content = event.content or ""
                break
            elif event.type == AgentEventType.ERROR:
                raise event.error
        
        return final_content
    
    async def stream(self, input_text: str) -> AsyncGenerator[AgentEvent, None]:
        """流式执行 Agent"""
        turn_state = TurnState.initial(max_iterations=self.executor.max_iterations)
        context = ExecutionContext.create(correlation_id=f"stream_{int(time.time())}")
        messages = [Message(role="user", content=input_text)]
        
        async for event in self.executor.tt(messages, turn_state, context):
            yield event
    
    async def execute_with_events(self, input_text: str) -> List[AgentEvent]:
        """执行并返回所有事件"""
        events = []
        async for event in self.stream(input_text):
            events.append(event)
        return events

def create_loom_agent(
    llm,
    tools: Optional[Dict[str, Any]] = None,
    config: Optional[CoordinationConfig] = None,
    **kwargs
) -> LoomAgent:
    """创建 Loom 0.0.3 Agent"""
    return LoomAgent(llm=llm, tools=tools, config=config, **kwargs)
```

### 4. 更新主 API 入口

```python
# loom/__init__.py 更新
from .api.v0_0_3 import LoomAgent, create_loom_agent

# 添加便捷函数
def loom_agent(
    llm,
    tools=None,
    config=None,
    **kwargs
):
    """创建 Loom 0.0.3 统一协调 Agent"""
    return create_loom_agent(llm=llm, tools=tools, config=config, **kwargs)

__all__ = [
    # 现有 API
    "Agent", "agent", "tool", "agent_from_env",
    
    # Loom 0.0.3 API
    "LoomAgent", "loom_agent", "create_loom_agent",
    "AgentExecutor", "UnifiedExecutionContext", "IntelligentCoordinator",
    "CoordinationConfig", "AgentEvent", "AgentEventType",
    "TurnState", "ExecutionContext", "ContextAssembler",
    "ComponentPriority", "TaskHandler",
]
```

## 📚 开发者使用示例

### 1. 基础使用

```python
import loom
from loom.builtin.llms import MockLLM

# 使用 Loom 0.0.3 统一协调
agent = loom.loom_agent(
    llm=MockLLM(),
    tools={"calculator": CalculatorTool()}
)

result = await agent.run("计算 2+2")
print(result)
```

### 2. 流式执行

```python
async for event in agent.stream("分析这个数据"):
    if event.type == loom.AgentEventType.LLM_DELTA:
        print(event.content, end="", flush=True)
    elif event.type == loom.AgentEventType.TOOL_EXECUTION_START:
        print(f"\n[工具] {event.tool_call.name}")
```

### 3. 高级配置

```python
from loom import CoordinationConfig, UnifiedExecutionContext

config = CoordinationConfig(
    deep_recursion_threshold=5,
    high_complexity_threshold=0.8,
    context_cache_size=200,
    event_batch_size=15,
    event_batch_timeout=0.03
)

agent = loom.loom_agent(
    llm=llm,
    config=config,
    execution_id="my_analysis"
)
```

### 4. 直接使用 AgentExecutor

```python
from loom import AgentExecutor, TurnState, ExecutionContext, Message

executor = AgentExecutor(llm=llm, tools=tools)
turn_state = TurnState.initial(max_iterations=10)
context = ExecutionContext.create()
messages = [Message(role="user", content="Hello")]

async for event in executor.tt(messages, turn_state, context):
    print(f"Event: {event.type} - {event.content}")
```

## 🎯 实施建议

### 1. 立即实施
- 更新 `loom/__init__.py` 暴露核心 API
- 创建 `loom/api/v0_0_3.py` 开发者友好接口
- 更新文档和示例

### 2. 向后兼容
- 保持现有 `loom.agent()` API 不变
- 新增 `loom.loom_agent()` 作为 Loom 0.0.3 入口
- 提供迁移指南

### 3. 文档更新
- 创建 Loom 0.0.3 专用文档
- 提供完整的使用示例
- 更新 API 参考文档

## 📋 总结

**当前状况**: Loom 0.0.3 的核心能力**部分暴露**，但开发者无法充分利用统一协调、TT 递归、事件流等高级特性。

**改进方案**: 通过完整的 API 暴露，让开发者能够：
1. ✅ 使用统一协调机制
2. ✅ 享受性能优化
3. ✅ 利用事件流处理
4. ✅ 配置智能上下文组装
5. ✅ 实现高级任务处理

这样，Loom 0.0.3 的强大能力就能完全为开发者所用了！🚀
