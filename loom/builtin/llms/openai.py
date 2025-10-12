"""OpenAI LLM 实现 - 支持工具调用与流式输出"""

from __future__ import annotations

import json
from typing import Any, AsyncGenerator, Dict, List, Optional

from loom.interfaces.llm import BaseLLM

try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None  # type: ignore


class OpenAILLM(BaseLLM):
    """OpenAI LLM 实现 - 支持 gpt-4/gpt-3.5-turbo 等模型"""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4",
        base_url: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        if AsyncOpenAI is None:
            raise ImportError("Please install openai package: pip install openai")

        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self._model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.kwargs = kwargs

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def supports_tools(self) -> bool:
        # GPT-4 和 GPT-3.5-turbo 都支持工具调用
        return "gpt-4" in self._model.lower() or "gpt-3.5-turbo" in self._model.lower()

    async def generate(self, messages: List[Dict]) -> str:
        """同步生成(非流式)"""
        params = {
            "model": self._model,
            "messages": messages,
            "temperature": self.temperature,
        }
        if self.max_tokens:
            params["max_tokens"] = self.max_tokens

        response = await self.client.chat.completions.create(**params)
        return response.choices[0].message.content or ""

    async def stream(self, messages: List[Dict]) -> AsyncGenerator[str, None]:
        """流式生成"""
        params = {
            "model": self._model,
            "messages": messages,
            "temperature": self.temperature,
            "stream": True,
        }
        if self.max_tokens:
            params["max_tokens"] = self.max_tokens

        stream = await self.client.chat.completions.create(**params)
        async for chunk in stream:
            content = chunk.choices[0].delta.content
            if content:
                yield content

    async def generate_with_tools(self, messages: List[Dict], tools: List[Dict]) -> Dict:
        """带工具调用的生成"""
        params = {
            "model": self._model,
            "messages": messages,
            "tools": tools,
            "temperature": self.temperature,
        }
        if self.max_tokens:
            params["max_tokens"] = self.max_tokens

        response = await self.client.chat.completions.create(**params)
        message = response.choices[0].message

        # 解析工具调用
        tool_calls = []
        if message.tool_calls:
            for tc in message.tool_calls:
                tool_calls.append(
                    {
                        "id": tc.id,
                        "name": tc.function.name,
                        "arguments": json.loads(tc.function.arguments) if tc.function.arguments else {},
                    }
                )

        return {
            "content": message.content or "",
            "tool_calls": tool_calls if tool_calls else None,
        }

    async def stream_with_tools(
        self, messages: List[Dict], tools: List[Dict]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """流式工具调用(高级功能)"""
        params = {
            "model": self._model,
            "messages": messages,
            "tools": tools,
            "temperature": self.temperature,
            "stream": True,
        }
        if self.max_tokens:
            params["max_tokens"] = self.max_tokens

        stream = await self.client.chat.completions.create(**params)

        # 累积工具调用信息
        accumulated_tool_calls: Dict[int, Dict] = {}

        async for chunk in stream:
            delta = chunk.choices[0].delta

            # 文本增量
            if delta.content:
                yield {"type": "text_delta", "content": delta.content}

            # 工具调用增量
            if delta.tool_calls:
                for tc_delta in delta.tool_calls:
                    idx = tc_delta.index
                    if idx not in accumulated_tool_calls:
                        accumulated_tool_calls[idx] = {
                            "id": tc_delta.id or "",
                            "name": "",
                            "arguments": "",
                        }

                    if tc_delta.id:
                        accumulated_tool_calls[idx]["id"] = tc_delta.id
                    if tc_delta.function.name:
                        accumulated_tool_calls[idx]["name"] = tc_delta.function.name
                    if tc_delta.function.arguments:
                        accumulated_tool_calls[idx]["arguments"] += tc_delta.function.arguments

        # 流结束后,输出完整的工具调用
        if accumulated_tool_calls:
            tool_calls = []
            for tc_data in accumulated_tool_calls.values():
                try:
                    arguments = json.loads(tc_data["arguments"]) if tc_data["arguments"] else {}
                except json.JSONDecodeError:
                    arguments = {}

                tool_calls.append(
                    {
                        "id": tc_data["id"],
                        "name": tc_data["name"],
                        "arguments": arguments,
                    }
                )

            yield {"type": "tool_calls", "tool_calls": tool_calls}
