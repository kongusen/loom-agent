"""
外部知识库配置和接口定义

注意：接口定义已迁移到 loom/providers/knowledge/base.py
此文件保留用于向后兼容性，重新导出接口。

迁移日期：2026-01-31
"""

# 从新位置导入接口
from loom.providers.knowledge.base import KnowledgeBaseProvider, KnowledgeItem

# 向后兼容导出
__all__ = ["KnowledgeItem", "KnowledgeBaseProvider"]
