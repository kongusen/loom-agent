"""
Loom - 基于递归状态机的 AI Agent 框架

核心特性：
- 🔄 递归状态机：Agent = recursive function
- 💬 统一消息架构：Message 携带所有状态
- 🧠 智能上下文管理：自动压缩、Memory 集成
- 🤝 智能协作编排：Crew 多智能体系统
- 🔧 工具构建能力：@tool 装饰器、MCP 兼容

快速开始：
```python
from loom import SimpleAgent, Message
from loom.builtin import OpenAILLM, tool

# 定义工具
@tool(name="calculator")
async def calculator(expression: str) -> float:
    return eval(expression)

# 创建 Agent
agent = SimpleAgent(
    name="assistant",
    llm=OpenAILLM(api_key="..."),
    tools=[calculator]
)

# 使用
message = Message(role="user", content="What's 2+2?")
response = await agent.run(message)
print(response.content)
```

版本：v0.1.6
"""

# ============================================================================
# Core Components - 核心组件
# ============================================================================

from loom.core import (
    # Message
    Message,
    # Agent Protocol
    BaseAgent,
    create_agent,
    # Executor
    AgentExecutor,
    # Context
    ContextManager,
    create_context_manager,
    # Errors
    LoomError,
    AgentError,
    ExecutionError,
    ToolError,
    RecursionError,
    ContextError,
    LLMError,
)

# ============================================================================
# Agents - Agent 实现
# ============================================================================

from loom.agents import (
    SimpleAgent,
)

# ============================================================================
# Builtin - 内置实现
# ============================================================================

from loom.builtin import (
    # LLMs
    OpenAILLM,
    # Tools
    tool,
    ToolBuilder,
    # Memory
    InMemoryMemory,
    PersistentMemory,
    # Compression
    StructuredCompressor,
    CompressionConfig,
)

# ============================================================================
# Patterns - 高级模式
# ============================================================================

from loom.patterns import (
    # Crew 基础
    Crew,
    CrewRole,
    sequential_crew,
    parallel_crew,
    coordinated_crew,
    # 智能协调
    SmartCoordinator,
    TaskComplexity,
    SubTask,
    # 并行执行
    ParallelExecutor,
    ParallelConfig,
    # 容错恢复
    ErrorRecovery,
    RecoveryConfig,
    # 可观测性
    CrewTracer,
    CrewEvaluator,
    # 预设
    CrewPresets,
)

# ============================================================================
# Interfaces - 协议定义
# ============================================================================

from loom.interfaces import (
    BaseLLM,
    BaseTool,
    BaseMemory,
    BaseCompressor,
)

# ============================================================================
# Version - 版本信息
# ============================================================================

__version__ = "0.1.6"
__author__ = "Loom Team"

# ============================================================================
# Public API - 公开 API
# ============================================================================

__all__ = [
    # ========================================================================
    # Core - 核心
    # ========================================================================
    "Message",
    "BaseAgent",
    "create_agent",
    "AgentExecutor",
    "ContextManager",
    "create_context_manager",

    # ========================================================================
    # Agents - Agent 实现
    # ========================================================================
    "SimpleAgent",

    # ========================================================================
    # Builtin - 内置实现
    # ========================================================================
    # LLMs
    "OpenAILLM",
    # Tools
    "tool",
    "ToolBuilder",
    # Memory
    "InMemoryMemory",
    "PersistentMemory",
    # Compression
    "StructuredCompressor",
    "CompressionConfig",

    # ========================================================================
    # Patterns - 高级模式（Crew）
    # ========================================================================
    "Crew",
    "CrewRole",
    "sequential_crew",
    "parallel_crew",
    "coordinated_crew",
    "SmartCoordinator",
    "TaskComplexity",
    "SubTask",
    "ParallelExecutor",
    "ParallelConfig",
    "ErrorRecovery",
    "RecoveryConfig",
    "CrewTracer",
    "CrewEvaluator",
    "CrewPresets",

    # ========================================================================
    # Interfaces - 协议
    # ========================================================================
    "BaseLLM",
    "BaseTool",
    "BaseMemory",
    "BaseCompressor",

    # ========================================================================
    # Errors - 错误
    # ========================================================================
    "LoomError",
    "AgentError",
    "ExecutionError",
    "ToolError",
    "RecursionError",
    "ContextError",
    "LLMError",

    # ========================================================================
    # Version - 版本
    # ========================================================================
    "__version__",
]
