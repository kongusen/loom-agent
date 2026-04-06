"""Web 操作工具 - 真实实现"""

from typing import Any
import httpx


async def web_fetch(url: str, prompt: str = "") -> dict[str, Any]:
    """获取网页内容

    Args:
        url: URL to fetch
        prompt: Optional prompt (not used, for compatibility)

    Returns:
        Dictionary with url, content, status_code
    """
    try:
        # Validate URL
        if not url.startswith(("http://", "https://")):
            return {
                "url": url,
                "content": f"Error: Invalid URL '{url}'. Must start with http:// or https://",
                "status_code": 0,
                "error": "Invalid URL"
            }

        # Fetch with timeout
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()

            # Get content type
            content_type = response.headers.get("content-type", "").lower()

            # Extract text content
            if "text/html" in content_type:
                text = _extract_text_from_html(response.text)
                content = f"Content from {url}:\n\n{text}"
            elif "application/json" in content_type:
                content = f"JSON from {url}:\n\n{response.text[:50000]}"
            elif "text/" in content_type:
                content = f"Text from {url}:\n\n{response.text[:50000]}"
            else:
                content = f"Binary content from {url} (Content-Type: {content_type})"

            return {
                "url": url,
                "content": content,
                "status_code": response.status_code
            }

    except httpx.TimeoutException:
        return {
            "url": url,
            "content": f"Error: Request to {url} timed out after 10 seconds",
            "status_code": 0,
            "error": "Timeout"
        }
    except httpx.HTTPStatusError as e:
        return {
            "url": url,
            "content": f"Error: HTTP {e.response.status_code} from {url}",
            "status_code": e.response.status_code,
            "error": f"HTTP {e.response.status_code}"
        }
    except httpx.RequestError as e:
        return {
            "url": url,
            "content": f"Error: Failed to fetch {url}: {str(e)}",
            "status_code": 0,
            "error": str(e)
        }
    except Exception as e:
        return {
            "url": url,
            "content": f"Error: Unexpected error fetching {url}: {str(e)}",
            "status_code": 0,
            "error": str(e)
        }


async def web_search(query: str, num_results: int = 5) -> dict[str, Any]:
    """网页搜索 - 使用 DuckDuckGo

    Args:
        query: Search query
        num_results: Number of results (default: 5)

    Returns:
        Dictionary with query, results list
    """
    try:
        # Use DuckDuckGo HTML search
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            response = await client.get(
                "https://html.duckduckgo.com/html/",
                params={"q": query},
                headers={"User-Agent": "Mozilla/5.0 (compatible; LoomAgent/1.0)"}
            )
            response.raise_for_status()

            # Parse results
            results = _parse_duckduckgo_results(response.text, num_results)

            if not results:
                return {
                    "query": query,
                    "results": [],
                    "message": f"No results found for: {query}"
                }

            return {
                "query": query,
                "results": results,
                "message": f"Found {len(results)} results"
            }

    except httpx.TimeoutException:
        return {
            "query": query,
            "results": [],
            "error": "Search request timed out after 10 seconds"
        }
    except httpx.HTTPStatusError as e:
        return {
            "query": query,
            "results": [],
            "error": f"HTTP {e.response.status_code} from search service"
        }
    except httpx.RequestError as e:
        return {
            "query": query,
            "results": [],
            "error": f"Failed to search: {str(e)}"
        }
    except Exception as e:
        return {
            "query": query,
            "results": [],
            "error": f"Unexpected error during search: {str(e)}"
        }


def _extract_text_from_html(html: str) -> str:
    """Extract readable text from HTML"""
    try:
        from html.parser import HTMLParser

        class TextExtractor(HTMLParser):
            def __init__(self):
                super().__init__()
                self.text_parts = []
                self.skip_tags = {'script', 'style', 'head', 'meta', 'link'}
                self.current_tag = None

            def handle_starttag(self, tag, attrs):
                self.current_tag = tag

            def handle_endtag(self, tag):
                self.current_tag = None

            def handle_data(self, data):
                if self.current_tag not in self.skip_tags:
                    text = data.strip()
                    if text:
                        self.text_parts.append(text)

        parser = TextExtractor()
        parser.feed(html)

        # Join and clean up
        text = " ".join(parser.text_parts)

        # Limit length
        max_length = 5000
        if len(text) > max_length:
            text = text[:max_length] + "... (truncated)"

        return text

    except Exception:
        # Fallback: simple tag removal
        import re
        text = re.sub(r'<[^>]+>', '', html)
        text = re.sub(r'\s+', ' ', text).strip()

        max_length = 5000
        if len(text) > max_length:
            text = text[:max_length] + "... (truncated)"

        return text


def _parse_duckduckgo_results(html: str, num_results: int) -> list[dict]:
    """Parse DuckDuckGo HTML search results"""
    try:
        from html.parser import HTMLParser

        class DDGParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.results = []
                self.current_result = {}
                self.in_result = False
                self.in_title = False
                self.in_snippet = False
                self.current_data = []

            def handle_starttag(self, tag, attrs):
                attrs_dict = dict(attrs)

                if tag == 'div' and attrs_dict.get('class', '').startswith('result'):
                    self.in_result = True
                    self.current_result = {}

                if self.in_result and tag == 'a' and 'result__a' in attrs_dict.get('class', ''):
                    self.in_title = True
                    self.current_result['url'] = attrs_dict.get('href', '')
                    self.current_data = []

                if self.in_result and tag == 'a' and 'result__snippet' in attrs_dict.get('class', ''):
                    self.in_snippet = True
                    self.current_data = []

            def handle_endtag(self, tag):
                if tag == 'a' and self.in_title:
                    self.current_result['title'] = ''.join(self.current_data).strip()
                    self.in_title = False

                if tag == 'a' and self.in_snippet:
                    self.current_result['snippet'] = ''.join(self.current_data).strip()
                    self.in_snippet = False

                if tag == 'div' and self.in_result:
                    if self.current_result.get('title') and self.current_result.get('url'):
                        self.results.append(self.current_result)
                    self.in_result = False
                    self.current_result = {}

            def handle_data(self, data):
                if self.in_title or self.in_snippet:
                    self.current_data.append(data)

        parser = DDGParser()
        parser.feed(html)

        return parser.results[:num_results]

    except Exception:
        return []

