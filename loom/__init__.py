"""
Loom - 基于递归状态机的 AI Agent 框架

核心特性：
- 🔄 递归状态机：Agent = recursive function
- 💬 统一消息架构：Message 携带所有状态
- 🧠 智能上下文管理：Memory 集成、压缩支持
- 🤝 智能协作编排：Crew 多智能体系统
- 🔧 工具构建能力：@tool 装饰器、MCP 兼容

核心依赖：
- Python >= 3.11
- Pydantic >= 2.5.0

快速开始：
```python
import loom
from loom import Message, tool

# 定义工具
@tool(name="calculator")
async def calculator(expression: str) -> float:
    return eval(expression)

# 创建 Agent（支持主流 LLM）
agent = loom.agent(
    name="assistant",
    llm="deepseek",      # 支持：openai, deepseek, qwen, kimi 等
    api_key="sk-...",
    tools=[calculator]
)

# 使用
message = Message(role="user", content="What's 2+2?")
response = await agent.run(message)
print(response.content)
```

版本：v0.1.6
"""

from typing import List, Optional, Union, Dict, Any
from loom.agents import Agent

# ============================================================================
# Agent 工厂函数
# ============================================================================

def agent(
    name: str,
    llm: Union[str, Dict[str, Any], "BaseLLM"],
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    base_url: Optional[str] = None,
    tools: Optional[List["BaseTool"]] = None,
    system_prompt: Optional[str] = None,
    context_manager: Optional["ContextManager"] = None,
    max_recursion_depth: int = 20,
    skills_dir: Optional[str] = None,
    enable_skills: bool = True,
    react_mode: bool = False,  # 新增：ReAct 模式开关
    **llm_kwargs: Any,
) -> Agent:
    """
    创建 Loom Agent 实例（工厂函数）

    Args:
        name: Agent 名称
        llm: LLM 配置，支持三种方式：
            - 字符串：提供商名称（如 "openai", "deepseek", "qwen", "custom"）
            - 字典：详细配置 {"provider": "openai", "api_key": "...", ...}
            - BaseLLM 实例：直接使用
        api_key: API 密钥（当 llm 是字符串时必需）
        model: 模型名称（可选，使用默认模型）
        base_url: API 基础 URL（可选，用于自定义服务或代理）
        tools: 工具列表
        system_prompt: 系统提示词（可选）
        context_manager: Context 管理器（可选）
        max_recursion_depth: 最大递归深度
        skills_dir: 技能目录路径（可选，默认 ./skills）
        enable_skills: 是否启用技能系统
        react_mode: 是否启用 ReAct 模式（推理-行动循环，适合复杂推理任务）
        **llm_kwargs: 其他 LLM 参数（temperature, max_tokens 等）

    Returns:
        Agent 实例

    Example::

        # 标准模式（默认）
        import loom
        agent = loom.agent(
            name="assistant",
            llm="deepseek",
            api_key="sk-..."
        )

        # ReAct 模式（适合需要多步推理的任务）
        agent = loom.agent(
            name="researcher",
            llm="openai",
            api_key="sk-...",
            tools=[search_tool, calculator],
            react_mode=True  # 启用推理-行动循环
        )

        # 使用代理或自定义服务
        agent = loom.agent(
            name="assistant",
            llm="openai",
            api_key="sk-...",
            base_url="https://your-proxy.com/v1"
        )

        # 详细配置
        agent = loom.agent(
            name="assistant",
            llm="qwen",
            api_key="sk-...",
            model="qwen-turbo",
            temperature=0.7,
            max_tokens=2000
        )

        # 字典配置
        agent = loom.agent(
            name="assistant",
            llm={
                "provider": "openai",
                "api_key": "sk-...",
                "model": "gpt-4",
                "temperature": 0.7
            }
        )

        # LLM 实例
        from loom.builtin import UnifiedLLM
        llm = UnifiedLLM(api_key="sk-...", provider="openai")
        agent = loom.agent(name="assistant", llm=llm)
    """
    return Agent(
        name=name,
        llm=llm,
        api_key=api_key,
        model=model,
        base_url=base_url,
        tools=tools,
        system_prompt=system_prompt,
        context_manager=context_manager,
        max_recursion_depth=max_recursion_depth,
        skills_dir=skills_dir,
        enable_skills=enable_skills,
        react_mode=react_mode,  # 传递 react_mode
        **llm_kwargs,
    )

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
# Builtin - 核心实现 + 主流 LLM 支持
# ============================================================================

from loom.builtin import (
    # Tools（核心，无依赖）
    tool,
    ToolBuilder,
    # Memory（核心，无依赖）
    InMemoryMemory,
    PersistentMemory,
    # LLMs（需要 pip install openai）
    UnifiedLLM,
    OpenAILLM,
    DeepSeekLLM,
    QwenLLM,
    KimiLLM,
    ZhipuLLM,
    DoubaoLLM,
    YiLLM,
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

__version__ = "0.1.9"
__author__ = "Loom Team"

# ============================================================================
# Public API - 公开 API
# ============================================================================

__all__ = [
    # ========================================================================
    # Agent 工厂函数
    # ========================================================================
    "agent",

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
    # Builtin - 核心实现 + 主流 LLM 支持
    # ========================================================================
    # Tools（核心，无依赖）
    "tool",
    "ToolBuilder",
    # Memory（核心，无依赖）
    "InMemoryMemory",
    "PersistentMemory",
    # LLMs（需要 pip install openai）
    "UnifiedLLM",
    "OpenAILLM",
    "DeepSeekLLM",
    "QwenLLM",
    "KimiLLM",
    "ZhipuLLM",
    "DoubaoLLM",
    "YiLLM",

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
