"""
Lexicon Agent Framework v2.0

基于Claude Code分析的智能体框架，实现上下文工程和多智能体协调
"""

# 导出主要类型
from .types import (
    AgentEvent, AgentEventType, ToolCall, ToolResult, 
    ToolSafetyLevel, Agent, ManagedContext, SessionState
)

# 导出核心组件
from .core.context import ContextRetrievalEngine, ContextProcessor, ContextManager
from .core.agent import AgentController
from .core.orchestration import OrchestrationEngine, AgentCoordinator
from .core.tools import ToolRegistry, IntelligentToolScheduler, ToolExecutor
from .core.streaming import StreamingProcessor, PerformanceOptimizer, StreamingPipeline

# 导出主框架接口
from .main import (
    LexiconAgent, 
    create_agent, 
    quick_chat,
    create_development_agent,
    create_production_agent,
    create_minimal_agent,
    create_custom_llm_agent
)

# 设置包版本
__version__ = "2.0.0"

__all__ = [
    # 主框架接口
    "LexiconAgent", "create_agent", "quick_chat",
    "create_development_agent", "create_production_agent", 
    "create_minimal_agent", "create_custom_llm_agent",
    
    # 主要类型
    "AgentEvent", "AgentEventType", "ToolCall", "ToolResult", 
    "ToolSafetyLevel", "Agent", "ManagedContext", "SessionState",
    
    # 核心组件
    "ContextRetrievalEngine", "ContextProcessor", "ContextManager",
    "AgentController", "OrchestrationEngine", "AgentCoordinator",
    "ToolRegistry", "IntelligentToolScheduler", "ToolExecutor",
    "StreamingProcessor", "PerformanceOptimizer", "StreamingPipeline"
]