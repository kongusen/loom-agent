from __future__ import annotations

import asyncio
from typing import Any, AsyncGenerator, Dict, List, Optional

from loom.interfaces.llm import LLMEvent


class MockLLM:
    """用于测试与示例的 Mock LLM - 实现BaseLLM Protocol。"""

    def __init__(
        self,
        responses: Optional[List[str]] = None,
        name: str = "mock-llm",
        should_call_tools: bool = False,
        tool_calls: Optional[List[Dict]] = None
    ) -> None:
        """
        初始化Mock LLM

        Args:
            responses: 预设的响应列表（每次调用消耗一个）
            name: 模型名称
            should_call_tools: 是否应该调用工具
            tool_calls: 预设的工具调用列表
        """
        self._responses = list(responses or ["OK"])
        self._model_name = name
        self._should_call_tools = should_call_tools
        self._tool_calls = tool_calls or []

    @property
    def model_name(self) -> str:
        return self._model_name

    async def stream(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        response_format: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ) -> AsyncGenerator[LLMEvent, None]:
        """
        统一流式生成接口 - Mock实现

        Yields:
            LLMEvent: 标准事件流
        """
        # 获取响应文本
        if self._responses:
            text = self._responses.pop(0)
        else:
            # 如果没有预设响应，使用用户消息
            text = "".join(m.get("content", "") for m in messages if m.get("role") == "user")
        
        # 如果要求 JSON 格式，确保返回有效的 JSON
        if response_format and response_format.get("type") == "json_object":
            import json
            # 如果文本不是有效的 JSON，尝试包装它
            try:
                # 尝试解析现有文本是否为 JSON
                json.loads(text)
                # 如果已经是 JSON，直接使用
            except (json.JSONDecodeError, ValueError):
                # 如果不是 JSON，创建一个简单的 JSON 对象
                # 尝试从用户消息中提取要求
                user_content = "".join(m.get("content", "") for m in messages if m.get("role") == "user")
                if "greeting" in user_content.lower():
                    text = '{"greeting": "Hello"}'
                else:
                    # 默认 JSON 响应
                    text = json.dumps({"response": text, "status": "ok"})

        # 逐字符流式输出 content_delta
        for ch in text:
            await asyncio.sleep(0)  # 让出事件循环
            yield {
                "type": "content_delta",
                "content": ch
            }

        # 如果需要，产出工具调用
        if self._should_call_tools and tools and self._tool_calls:
            yield {
                "type": "tool_calls",
                "tool_calls": self._tool_calls
            }

        # 产出finish事件
        yield {
            "type": "finish",
            "finish_reason": "tool_calls" if (self._should_call_tools and tools) else "stop"
        }

