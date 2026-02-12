"""
UnifiedSearchToolBuilder - 统一检索工具构建器

根据是否配置 knowledge_base 动态生成不同的工具描述：
- 无 knowledge_base → 纯记忆检索的 query 工具
- 有 knowledge_base → 增加 scope/source/intent/filters 参数

工具名始终为 "query"，agent 无需区分记忆和知识。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from loom.providers.knowledge.base import KnowledgeBaseProvider


class UnifiedSearchToolBuilder:
    """
    统一检索工具构建器。

    核心逻辑：
    - 无 knowledge_base → 生成纯记忆检索的 query 工具
    - 有 knowledge_base → 增加 scope/source 参数
    - 工具名始终为 "query"，agent 无需区分记忆和知识
    """

    def build_tool(
        self,
        knowledge_bases: list[KnowledgeBaseProvider] | None = None,
        memory_enabled: bool = True,
    ) -> dict[str, Any]:
        """构建统一检索工具定义"""
        if not knowledge_bases:
            return self._memory_only_tool()
        return self._unified_tool(knowledge_bases, memory_enabled)

    def _memory_only_tool(self) -> dict[str, Any]:
        """无知识库时：纯记忆检索"""
        return {
            "type": "function",
            "function": {
                "name": "query",
                "description": (
                    "搜索对话记忆。可查询最近任务(L1)、重要任务(L2)、"
                    "历史摘要(L3)、语义检索(L4)。"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "搜索查询",
                        },
                        "layer": {
                            "type": "string",
                            "enum": ["auto", "l1", "l2", "l3", "l4"],
                            "description": "指定记忆层级（默认 auto，自动选择）",
                        },
                    },
                    "required": ["query"],
                },
            },
        }

    def _unified_tool(
        self,
        kbs: list[KnowledgeBaseProvider],
        memory_enabled: bool,
    ) -> dict[str, Any]:
        """有知识库时：升级为统一检索工具"""
        # 动态构建知识源描述
        sources_desc = "\n".join(
            f"- {kb.name}: {kb.description}" for kb in kbs if kb.description
        )
        # 聚合所有 search_hints
        all_hints: list[str] = []
        for kb in kbs:
            all_hints.extend(kb.search_hints)
        hints_str = ", ".join(all_hints) if all_hints else ""

        desc_parts = ["统一检索工具。"]
        if memory_enabled:
            desc_parts.append("可搜索对话记忆(L1-L4)和外部知识库。")
        else:
            desc_parts.append("搜索外部知识库。")
        if sources_desc:
            desc_parts.append(f"\n可用知识源：\n{sources_desc}")
        if hints_str:
            desc_parts.append(f"\n适用场景：{hints_str}。")
        desc_parts.append("\n不指定 scope 时自动选择最相关的源。")

        # 构建参数
        props: dict[str, Any] = {
            "query": {
                "type": "string",
                "description": "搜索查询（自然语言）",
            },
            "scope": {
                "type": "string",
                "enum": ["auto", "memory", "knowledge", "all"],
                "description": (
                    "搜索范围。auto=自动路由, memory=仅对话记忆, "
                    "knowledge=仅知识库, all=搜索所有源统一排序"
                ),
            },
            "intent": {
                "type": "string",
                "description": "搜索意图（帮助优化检索相关性，如 recall/lookup/troubleshooting）",
            },
        }

        # 多知识库时增加 source 参数
        if len(kbs) > 1:
            props["source"] = {
                "type": "string",
                "enum": [kb.name for kb in kbs],
                "description": "指定知识库（可选，不指定时自动选择）",
            }

        # 聚合所有 supported_filters
        all_filters: set[str] = set()
        for kb in kbs:
            all_filters.update(kb.supported_filters)
        if all_filters:
            props["filters"] = {
                "type": "object",
                "description": f"过滤条件，支持: {', '.join(sorted(all_filters))}",
            }

        return {
            "type": "function",
            "function": {
                "name": "query",
                "description": "".join(desc_parts),
                "parameters": {
                    "type": "object",
                    "properties": props,
                    "required": ["query"],
                },
            },
        }
