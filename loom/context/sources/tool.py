"""
Tool Context Source - 工具定义上下文源

从工具注册表获取工具定义作为上下文。
"""

from typing import TYPE_CHECKING, Any

from loom.context.block import ContextBlock
from loom.context.source import ContextSource

if TYPE_CHECKING:
    from loom.memory.tokenizer import TokenCounter


class ToolSource(ContextSource):
    """
    工具定义源

    按需加载工具定义到上下文中。
    支持基于任务相关性的工具过滤。
    """

    def __init__(
        self,
        tool_manager: Any = None,
        tool_registry: Any = None,
    ):
        """
        初始化工具源

        Args:
            tool_manager: SandboxToolManager 实例
            tool_registry: ToolRegistry 实例（兼容旧API）
        """
        self._tool_manager = tool_manager
        self._tool_registry = tool_registry

    @property
    def source_name(self) -> str:
        return "tools"

    def _get_tool_definitions(self) -> list[dict]:
        """获取所有工具定义"""
        tools = []

        if self._tool_manager:
            try:
                for tool in self._tool_manager.list_tools():
                    tools.append(
                        {
                            "name": tool.name,
                            "description": tool.description,
                            "input_schema": tool.input_schema,
                        }
                    )
            except Exception:
                pass

        if self._tool_registry:
            try:
                for defn in self._tool_registry.definitions:
                    tools.append(
                        {
                            "name": defn.name,
                            "description": defn.description,
                            "input_schema": defn.input_schema,
                        }
                    )
            except Exception:
                pass

        return tools

    def _tool_to_content(self, tool: dict) -> str:
        """将工具定义转换为内容字符串"""
        name = tool.get("name", "unknown")
        desc = tool.get("description", "")
        schema = tool.get("input_schema", {})

        parts = [f"Tool: {name}"]
        if desc:
            parts.append(f"Description: {desc}")
        if schema:
            params = schema.get("properties", {})
            if params:
                param_strs = []
                for k, v in params.items():
                    param_strs.append(f"  - {k}: {v.get('type', 'any')}")
                parts.append("Parameters:\n" + "\n".join(param_strs))

        return "\n".join(parts)

    def _is_relevant(
        self,
        tool: dict,
        query: str,
        min_relevance: float,
    ) -> tuple[bool, float]:
        """判断工具是否与查询相关"""
        if not query:
            return True, 0.7

        query_lower = query.lower()
        name = tool.get("name", "").lower()
        desc = tool.get("description", "").lower()

        # 简单的关键词匹配
        keywords = set(query_lower.split())
        text = f"{name} {desc}"

        matches = sum(1 for kw in keywords if len(kw) > 2 and kw in text)
        relevance = min(1.0, 0.5 + matches * 0.1)

        return relevance >= min_relevance, relevance

    async def collect(
        self,
        query: str,
        token_budget: int,
        token_counter: "TokenCounter",
        min_relevance: float = 0.5,
    ) -> list[ContextBlock]:
        """收集工具定义"""
        tools = self._get_tool_definitions()
        if not tools:
            return []

        blocks: list[ContextBlock] = []
        current_tokens = 0

        for tool in tools:
            is_relevant, relevance = self._is_relevant(tool, query, min_relevance)
            if not is_relevant:
                continue

            content = self._tool_to_content(tool)
            tokens = self._count_tokens(content, "system", token_counter)

            if current_tokens + tokens > token_budget:
                break

            block = ContextBlock(
                content=content,
                role="system",
                token_count=tokens,
                priority=0.8 * relevance,
                source=self.source_name,
                compressible=False,
                metadata={
                    "tool_name": tool.get("name"),
                    "relevance": relevance,
                },
            )
            blocks.append(block)
            current_tokens += tokens

        return blocks
