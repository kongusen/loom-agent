from __future__ import annotations

import asyncio
from typing import AsyncGenerator, Dict, List, Optional

from loom.interfaces.llm import BaseLLM


class MockLLM(BaseLLM):
    """用于测试与示例的 Mock LLM。"""

    def __init__(self, responses: Optional[List[str]] = None, name: str = "mock-llm") -> None:
        self._responses = list(responses or ["OK"])
        self._model_name = name

    @property
    def model_name(self) -> str:
        return self._model_name

    async def generate(self, messages: List[Dict]) -> str:
        if self._responses:
            return self._responses.pop(0)
        return "".join(m.get("content", "") for m in messages if m.get("role") == "user")

    async def stream(self, messages: List[Dict]) -> AsyncGenerator[str, None]:
        text = await self.generate(messages)
        # 简单逐字符流
        for ch in text:
            await asyncio.sleep(0)  # 让出循环
            yield ch

    async def generate_with_tools(self, messages: List[Dict], tools: List[Dict]) -> Dict:
        return {"content": await self.generate(messages), "tool_calls": []}

