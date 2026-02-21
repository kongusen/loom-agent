"""
Unified Search Tool - 统一检索工具

统一 query 工具，支持记忆 + 知识库检索。

核心组件：
- UnifiedSearchToolBuilder: 根据配置动态生成工具定义
- UnifiedSearchExecutor: 统一路由 + 执行 + 格式化
"""

from loom.tools.search.builder import UnifiedSearchToolBuilder
from loom.tools.search.executor import UnifiedSearchExecutor

__all__ = [
    "UnifiedSearchToolBuilder",
    "UnifiedSearchExecutor",
]
