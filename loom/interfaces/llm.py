from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncGenerator, Dict, List


class BaseLLM(ABC):
    """LLM 基础接口 - 所有 LLM 提供者必须实现"""

    @abstractmethod
    async def generate(self, messages: List[Dict]) -> str:
        """非流式生成一个完整响应。"""
        raise NotImplementedError

    @abstractmethod
    async def stream(self, messages: List[Dict]) -> AsyncGenerator[str, None]:
        """流式生成响应内容增量。"""
        raise NotImplementedError

    @abstractmethod
    async def generate_with_tools(self, messages: List[Dict], tools: List[Dict]) -> Dict:
        """带工具调用的生成（返回可能包含 tool_calls 等结构）。"""
        raise NotImplementedError

    @property
    @abstractmethod
    def model_name(self) -> str:
        raise NotImplementedError

    @property
    def supports_tools(self) -> bool:
        return False

