"""
Loom Agent Framework - 统一入口

提供简洁、体系化的能力暴露接口。
"""

__version__ = "0.3.8"

# ============================================================================
# 高层 API（推荐使用）
# ============================================================================

from loom.api.loom import Loom, LoomConfig
from loom.builder import LoomBuilder

# ============================================================================
# 配置类（统一导出）
# ============================================================================
from loom.config import (
    AgentConfig,
    ContextConfig,
    CurationConfig,
    ExecutionConfig,
    FractalConfig,
    GrowthStrategy,
    GrowthTrigger,
    NodeRole,
)

# ============================================================================
# LLM
# ============================================================================
from loom.llm import LLMProvider, OpenAIProvider

# ============================================================================
# Memory
# ============================================================================
from loom.memory.core import LoomMemory
from loom.memory.types import MemoryTier, MemoryType, MemoryUnit

# ============================================================================
# 核心类
# ============================================================================
from loom.node.agent import AgentNode
from loom.node.fractal import FractalAgentNode
from loom.node.tool import ToolNode
from loom.patterns import PATTERNS, get_pattern, list_patterns

# ============================================================================
# 导出列表
# ============================================================================

__all__ = [
    # 版本
    "__version__",
    # 高层 API
    "Loom",
    "LoomBuilder",
    "LoomConfig",
    # 模式系统
    "PATTERNS",
    "get_pattern",
    "list_patterns",
    # 核心类
    "AgentNode",
    "FractalAgentNode",
    "ToolNode",
    # 配置类
    "AgentConfig",
    "FractalConfig",
    "ExecutionConfig",
    "ContextConfig",
    "CurationConfig",
    # 枚举
    "NodeRole",
    "GrowthStrategy",
    "GrowthTrigger",
    # LLM
    "LLMProvider",
    "OpenAIProvider",
    # Memory
    "LoomMemory",
    "MemoryUnit",
    "MemoryTier",
    "MemoryType",
]
