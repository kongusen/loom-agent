"""
OpenAI LLM实现 - 简洁的Protocol实现

只需实现两个接口：
1. model_name 属性
2. stream() 方法
"""

from __future__ import annotations

import json
from typing import Any, AsyncGenerator, Dict, List, Optional

from loom.interfaces.llm import LLMEvent
from loom.utils.stream_accumulator import OpenAIStreamAccumulator

try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None  # type: ignore


class OpenAILLM:
    """
    OpenAI LLM实现 - 实现BaseLLM Protocol

    **特点**:
    - 无需继承，直接实现Protocol
    - 只实现一个核心方法：stream()
    - 支持所有OpenAI模型
    - 支持工具调用 (function calling)
    - 支持JSON模式 (structured output)
    - 使用StreamAccumulator处理混合类型

    **支持的模型**:
    - GPT-4 系列: gpt-4, gpt-4-turbo, gpt-4o
    - GPT-3.5 系列: gpt-3.5-turbo
    - O1 系列: o1-preview, o1-mini

    Example::

        from loom.builtin.llms import OpenAILLM

        # 基础使用
        llm = OpenAILLM(
            api_key="sk-...",
            model="gpt-4",
            temperature=0.7
        )

        # 文本生成
        messages = [{"role": "user", "content": "Hello!"}]
        async for event in llm.stream(messages):
            if event["type"] == "content_delta":
                print(event["content"], end="", flush=True)

        # 工具调用
        tools = [{
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get weather",
                "parameters": {...}
            }
        }]

        async for event in llm.stream(messages, tools=tools):
            if event["type"] == "tool_calls":
                for tc in event["tool_calls"]:
                    print(f"Call: {tc['name']}")

        # JSON模式
        async for event in llm.stream(
            messages,
            response_format={"type": "json_object"}
        ):
            if event["type"] == "content_delta":
                json_str += event["content"]
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4",
        base_url: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        timeout: float = 120.0,
        max_retries: int = 3,
        **kwargs: Any,
    ) -> None:
        """
        初始化OpenAI LLM

        Args:
            api_key: OpenAI API密钥
            model: 模型名称 (default: "gpt-4")
            base_url: 可选的API基础URL (用于代理或兼容API)
            temperature: 采样温度 0-2 (default: 0.7)
            max_tokens: 最大生成token数 (default: None, 无限制)
            timeout: 请求超时时间（秒） (default: 120.0)
            max_retries: 最大重试次数 (default: 3)
            **kwargs: 其他OpenAI API参数
                - top_p: float
                - frequency_penalty: float
                - presence_penalty: float
                - stop: List[str]
                - seed: int (for reproducibility)
                等

        Raises:
            ImportError: 如果未安装openai包

        Example::

            # 基础配置
            llm = OpenAILLM(api_key="sk-...")

            # 高级配置
            llm = OpenAILLM(
                api_key="sk-...",
                model="gpt-4-turbo",
                temperature=0.3,
                max_tokens=2000,
                top_p=0.9,
                frequency_penalty=0.5,
                seed=42  # 可复现
            )

            # 使用代理
            llm = OpenAILLM(
                api_key="sk-...",
                base_url="https://api.openai-proxy.com/v1"
            )
        """
        if AsyncOpenAI is None:
            raise ImportError(
                "OpenAI package not installed. "
                "Install it with: pip install openai"
            )

        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
        )
        self._model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.kwargs = kwargs

    @property
    def model_name(self) -> str:
        """返回模型名称"""
        return self._model

    async def stream(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        response_format: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ) -> AsyncGenerator[LLMEvent, None]:
        """
        统一流式生成接口 - OpenAI实现

        实现了BaseLLM Protocol的stream()方法，支持：
        - 文本流式生成
        - 工具调用 (function calling)
        - JSON模式 (structured output)
        - 混合类型内容处理

        Args:
            messages: OpenAI格式消息列表
            tools: 可选的工具定义
            response_format: 可选的响应格式
            **kwargs: 额外的OpenAI参数（会覆盖初始化时的参数）

        Yields:
            LLMEvent: 标准事件流

        Example::

            # 文本生成
            async for event in llm.stream(messages):
                if event["type"] == "content_delta":
                    print(event["content"], end="")
                elif event["type"] == "finish":
                    print(f"\\nDone: {event['finish_reason']}")

            # 工具调用
            async for event in llm.stream(messages, tools=tools):
                match event["type"]:
                    case "content_delta":
                        print(event["content"], end="")
                    case "tool_calls":
                        execute_tools(event["tool_calls"])
                    case "finish":
                        print(f"\\nFinished: {event['finish_reason']}")

            # JSON模式
            json_parts = []
            async for event in llm.stream(
                messages,
                response_format={"type": "json_object"}
            ):
                if event["type"] == "content_delta":
                    json_parts.append(event["content"])

            result = json.loads("".join(json_parts))

        Note:
            - 使用StreamAccumulator处理工具调用累积
            - 自动处理混合类型内容 (dict, str, etc.)
            - 实时产出content_delta，流结束时产出tool_calls
            - 总是产出finish事件
        """
        # 构建请求参数
        params = {
            "model": self._model,
            "messages": messages,
            "temperature": self.temperature,
            "stream": True,
        }

        if self.max_tokens:
            params["max_tokens"] = self.max_tokens

        # 添加tools
        if tools:
            params["tools"] = tools

        # 添加response_format (JSON mode)
        if response_format:
            params["response_format"] = response_format

        # 合并额外参数 (kwargs优先级更高)
        merged_kwargs = {**self.kwargs, **kwargs}
        params.update(merged_kwargs)

        # 创建流式请求
        stream = await self.client.chat.completions.create(**params)

        # 使用 OpenAIStreamAccumulator 处理混合类型和工具调用
        accumulator = OpenAIStreamAccumulator(mode='auto')
        finish_reason = None

        # 流式处理
        async for chunk in stream:
            accumulator.add(chunk)

            # 检查chunk有效性
            if not chunk.choices or len(chunk.choices) == 0:
                continue

            choice = chunk.choices[0]
            delta = choice.delta
            finish_reason = choice.finish_reason

            # 实时产出content deltas
            if delta.content:
                content = delta.content

                # 处理混合类型 (dict, str, etc.)
                if isinstance(content, dict):
                    content = json.dumps(content)
                elif not isinstance(content, str):
                    content = str(content)

                yield {
                    "type": "content_delta",
                    "content": content
                }

        # 流结束后，产出tool_calls (如果有)
        tool_calls = accumulator.get_tool_calls()
        if tool_calls:
            yield {
                "type": "tool_calls",
                "tool_calls": tool_calls
            }

        # 产出finish事件
        yield {
            "type": "finish",
            "finish_reason": finish_reason or ("tool_calls" if tool_calls else "stop")
        }

    def __repr__(self) -> str:
        """字符串表示"""
        return f"OpenAILLM(model={self._model}, temperature={self.temperature})"
