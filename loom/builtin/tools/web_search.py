"""Web 搜索工具 - 使用 DuckDuckGo (无需 API key)"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from loom.interfaces.tool import BaseTool

try:
    from duckduckgo_search import DDGS
except ImportError:
    DDGS = None  # type: ignore


class WebSearchInput(BaseModel):
    """Web 搜索输入参数"""

    query: str = Field(description="Search query")
    max_results: int = Field(default=5, description="Maximum number of results to return")


class WebSearchTool(BaseTool):
    """
    Web 搜索工具 - 使用 DuckDuckGo

    需要安装: pip install duckduckgo-search
    """

    name = "web_search"
    description = "Search the web using DuckDuckGo. Returns titles, snippets, and URLs."
    args_schema = WebSearchInput
    is_concurrency_safe = True

    def __init__(self) -> None:
        if DDGS is None:
            raise ImportError(
                "Please install duckduckgo-search: pip install duckduckgo-search"
            )

    async def run(self, query: str, max_results: int = 5, **kwargs: Any) -> str:
        """执行搜索"""
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))

            if not results:
                return f"No results found for query: {query}"

            # 格式化输出
            output_lines = [f"Search results for '{query}':\n"]
            for i, result in enumerate(results, 1):
                title = result.get("title", "No title")
                snippet = result.get("body", "")
                url = result.get("href", "")
                output_lines.append(f"{i}. **{title}**")
                output_lines.append(f"   {snippet}")
                output_lines.append(f"   URL: {url}\n")

            return "\n".join(output_lines)

        except Exception as e:
            return f"Search error: {str(e)}"
