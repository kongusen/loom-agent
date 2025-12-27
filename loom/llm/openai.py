"""
OpenAI LLM Provider

支持完整的 LLM 配置体系。
"""

import os
from typing import List, Dict, Any, AsyncIterator, Optional, Union
from loom.interfaces.llm import LLMProvider, LLMResponse, StreamChunk
from loom.llm.config import (
    LLMConfig,
    ConnectionConfig,
    GenerationConfig,
    StreamConfig,
    StructuredOutputConfig,
    ToolConfig,
    AdvancedConfig
)

try:
    from openai import AsyncOpenAI
except ImportError:
    raise ImportError(
        "OpenAI SDK not installed. Install with: pip install loom-agent[llm]"
    )


class OpenAIProvider(LLMProvider):
    """
    OpenAI Provider with comprehensive configuration system.

    支持三种使用方式：

    1. 最简单（自动读取环境变量）：
        provider = OpenAIProvider()

    2. 快速配置（传递参数）：
        provider = OpenAIProvider(
            model="gpt-4",
            api_key="sk-...",
            temperature=0.7
        )

    3. 完整配置（使用 LLMConfig）：
        config = LLMConfig(
            connection=ConnectionConfig(api_key="sk-..."),
            generation=GenerationConfig(model="gpt-4", temperature=0.7),
            stream=StreamConfig(enabled=True),
            structured_output=StructuredOutputConfig(
                enabled=True,
                format="json_object"
            )
        )
        provider = OpenAIProvider(config=config)
    """

    def __init__(
        self,
        config: Optional[LLMConfig] = None,
        # 快速配置参数（向后兼容）
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: Optional[bool] = None,
        **kwargs
    ):
        """
        初始化 OpenAI Provider

        Args:
            config: 完整的 LLMConfig 配置
            model: 模型名称（快速配置）
            api_key: API Key（快速配置）
            base_url: Base URL（快速配置）
            temperature: 温度参数（快速配置）
            max_tokens: 最大 Token 数（快速配置）
            stream: 是否启用流式（快速配置）
            **kwargs: 其他参数
        """
        # 如果没有提供 config，创建默认配置
        if config is None:
            config = LLMConfig()

            # 应用快速配置参数
            if api_key or base_url:
                config.connection = ConnectionConfig(
                    api_key=api_key,
                    base_url=base_url
                )

            if model or temperature is not None or max_tokens:
                config.generation = GenerationConfig(
                    model=model or "gpt-4",
                    temperature=temperature if temperature is not None else 0.7,
                    max_tokens=max_tokens
                )

            if stream is not None:
                config.stream = StreamConfig(enabled=stream)

        self.config = config

        # 创建 OpenAI 客户端
        self.client = AsyncOpenAI(
            api_key=config.connection.api_key or os.getenv("OPENAI_API_KEY"),
            base_url=config.connection.base_url or os.getenv("OPENAI_BASE_URL"),
            timeout=config.connection.timeout,
            max_retries=config.connection.max_retries,
            organization=config.connection.organization,
            **kwargs
        )

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> LLMResponse:
        """调用 OpenAI Chat API（使用配置体系）"""
        # 获取基础参数
        kwargs = self.config.to_openai_kwargs()
        kwargs["messages"] = messages

        # 添加工具
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = self.config.tool.tool_choice
            kwargs["parallel_tool_calls"] = self.config.tool.parallel_tool_calls

        # 覆盖配置（如果提供）
        if config:
            kwargs.update(config)

        # 调用 API
        response = await self.client.chat.completions.create(**kwargs)

        # 提取响应
        message = response.choices[0].message
        content = message.content or ""

        # 提取工具调用
        tool_calls = []
        if message.tool_calls:
            for tc in message.tool_calls:
                tool_calls.append({
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": tc.function.arguments
                })

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            token_usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            } if response.usage else None
        )

    async def stream_chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> AsyncIterator[StreamChunk]:
        """流式调用 OpenAI Chat API（使用配置体系）"""
        # 获取基础参数
        kwargs = self.config.to_openai_kwargs()
        kwargs["messages"] = messages
        kwargs["stream"] = True

        # 添加工具
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = self.config.tool.tool_choice
            kwargs["parallel_tool_calls"] = self.config.tool.parallel_tool_calls

        # 调用 API
        stream = await self.client.chat.completions.create(**kwargs)

        async for chunk in stream:
            delta = chunk.choices[0].delta

            # 文本内容
            if delta.content:
                yield StreamChunk(
                    type="text",
                    content=delta.content,
                    metadata={}
                )

            # 工具调用
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    yield StreamChunk(
                        type="tool_call",
                        content={
                            "id": tc.id,
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        },
                        metadata={}
                    )

            # 结束标记
            if chunk.choices[0].finish_reason:
                yield StreamChunk(
                    type="done",
                    content="",
                    metadata={"finish_reason": chunk.choices[0].finish_reason}
                )
