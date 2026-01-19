"""
Loom Configuration System

提供类型安全的配置模型，支持从文件加载和验证。

基于公理A1（统一接口公理）：
所有配置都遵循统一的接口和验证规则。
"""

from loom.config.base import LoomBaseConfig
from loom.config.execution import ExecutionConfig
from loom.config.fractal import FractalConfig, GrowthStrategy, GrowthTrigger
from loom.config.llm import LLMConfig
from loom.config.memory import MemoryConfig, MemoryLayerConfig, MemoryStrategyType
from loom.config.tool import ToolConfig

__all__ = [
    "LoomBaseConfig",
    "MemoryConfig",
    "MemoryLayerConfig",
    "MemoryStrategyType",
    "FractalConfig",
    "GrowthTrigger",
    "GrowthStrategy",
    "LLMConfig",
    "ExecutionConfig",
    "ToolConfig",
]
