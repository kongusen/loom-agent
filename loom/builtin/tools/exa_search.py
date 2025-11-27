"""Exa 搜索工具 - 使用 Exa API 进行高质量的 web 搜索"""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field

from loom.interfaces.tool import BaseTool


try:
    from exa_py import Exa
    from exa_py.models import SearchResponse
    from exa_py.exceptions import ExaError
    EXA_AVAILABLE = True
except ImportError:
    EXA_AVAILABLE = False


class ExaSearchInput(BaseModel):
    """Exa 搜索输入参数"""
    query: str = Field(description="Search query")
    max_results: int = Field(default=10, description="Maximum number of results to return")
    include_domains: list[str] = Field(default_factory=list, description="Domains to include in search")
    exclude_domains: list[str] = Field(default_factory=list, description="Domains to exclude from search")
    start_published_date: str = Field(default="", description="Start date for published content (YYYY-MM-DD)")
    end_published_date: str = Field(default="", description="End date for published content (YYYY-MM-DD)")


class ExaSearchTool(BaseTool):
    """
    Exa 搜索工具 - 使用 Exa API 进行高质量的 web 搜索

    需要安装: pip install exa-py
    """

    name = "exa_search"
    description = "Search the web using Exa API. Returns high-quality results with titles, snippets, URLs, and metadata."
    args_schema = ExaSearchInput
    is_concurrency_safe = True

    # Loom 2.0 - Orchestration attributes
    is_read_only = True  # Only reads from web, no local side effects
    category = "network"

    def __init__(self, api_key: str | None = None):
        """初始化 Exa 搜索工具"""
        if not EXA_AVAILABLE:
            raise ImportError(
                "Please install exa-py: pip install exa-py"
            )

        if api_key is None:
            raise ValueError(
                "Exa API key is required. Please provide it during initialization."
            )

        self.exa = Exa(api_key=api_key)

    async def run(
        self,
        query: str,
        max_results: int = 10,
        include_domains: list[str] = None,
        exclude_domains: list[str] = None,
        start_published_date: str = None,
        end_published_date: str = None,
        **kwargs: Any
    ) -> str:
        """执行 Exa 搜索"""
        try:
            # 构建搜索参数
            search_params = {
                "query": query,
                "num_results": max_results,
            }

            if include_domains:
                search_params["include_domains"] = include_domains
            if exclude_domains:
                search_params["exclude_domains"] = exclude_domains
            if start_published_date:
                search_params["start_published_date"] = start_published_date
            if end_published_date:
                search_params["end_published_date"] = end_published_date

            # 执行搜索
            response: SearchResponse = await self.exa.search_async(**search_params)

            if not response.results:
                return f"No results found for query: {query}"

            # 格式化输出
            output_lines = [f"Exa Search results for '{query}':\n"]
            output_lines.append(f"Total results: {len(response.results)}")
            output_lines.append("=" * 80)

            for i, result in enumerate(response.results, 1):
                title = result.title or "No title"
                snippet = result.text or ""
                url = result.url or ""
                published_date = result.published_date or "Unknown"
                domain = result.domain or "Unknown"

                output_lines.append(f"{i}. **{title}**")
                output_lines.append(f"   Domain: {domain}")
                output_lines.append(f"   Published: {published_date}")
                output_lines.append(f"   {snippet}")
                output_lines.append(f"   URL: {url}")
                output_lines.append("-" * 80)

            return "\n".join(output_lines)

        except ExaError as e:
            return f"Exa API error: {str(e)}"
        except Exception as e:
            return f"Search error: {str(e)}"

    async def find_similar(self, url: str, max_results: int = 10) -> str:
        """查找与给定URL相似的内容"""
        try:
            response = await self.exa.find_similar_async(url, num_results=max_results)

            if not response.results:
                return f"No similar content found for URL: {url}"

            output_lines = [f"Similar content to '{url}':\n"]
            for i, result in enumerate(response.results, 1):
                title = result.title or "No title"
                snippet = result.text or ""
                url = result.url or ""
                
                output_lines.append(f"{i}. **{title}**")
                output_lines.append(f"   {snippet}")
                output_lines.append(f"   URL: {url}")
                output_lines.append("-" * 80)

            return "\n".join(output_lines)

        except ExaError as e:
            return f"Exa API error: {str(e)}"
        except Exception as e:
            return f"Find similar error: {str(e)}"

    async def get_contents(self, urls: list[str]) -> str:
        """获取指定URL的内容"""
        try:
            response = await self.exa.get_contents_async(urls)

            if not response.results:
                return f"No content found for URLs: {', '.join(urls)}"

            output_lines = ["Content extraction results:\n"]
            for i, result in enumerate(response.results, 1):
                url = result.url or ""
                content = result.text or ""
                
                output_lines.append(f"{i}. URL: {url}")
                output_lines.append("=" * 80)
                output_lines.append(content)
                output_lines.append("\n" + "=" * 80)

            return "\n".join(output_lines)

        except ExaError as e:
            return f"Exa API error: {str(e)}"
        except Exception as e:
            return f"Get contents error: {str(e)}"
