"""
Loom Projection Module

提供上下文投影相关的功能，包括投影模式、配置和策略。
"""

from .profiles import ProjectionConfig, ProjectionMode

__all__ = [
    "ProjectionMode",
    "ProjectionConfig",
]
