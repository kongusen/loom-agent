"""
OpenAI LLM Provider

基于配置对象的 OpenAI Provider。

特性：
1. 使用 LLMConfig 统一配置管理
2. 使用 BaseResponseHandler 的 ToolCallAggregator
3. 框架不读取环境变量，由用户控制配置来源
"""

from collections.abc import AsyncGenerator
from typing import Any

from loom.config.llm import LLMConfig
from loom.providers.llm.base_handler import BaseResponseHandler
from loom.providers.llm.interface import LLMProvider, LLMResponse, StreamChunk

try:
    from openai import AsyncOpenAI
except ImportError:
    raise ImportError("OpenAI SDK not installed. Install with: pip install openai") from None


class OpenAIProvider(LLMProvider, BaseResponseHandler):
    """
    OpenAI Provider - 基于配置对象

    使用方式：
        from loom.config import LLMConfig

        config = LLMConfig(
            provider="openai",
            model="gpt-4",
            api_key="sk-...",  # 用户控制配置来源
            temperature=0.7
        )

        provider = OpenAIProvider(config)
    """

    def __init__(self, config: LLMConfig, **kwargs: Any):
        """
        初始化 OpenAI Provider

        Args:
            config: LLM 配置对象
            **kwargs: 额外参数传递给 AsyncOpenAI 客户端

        Raises:
            ValueError: 如果 api_key 未在配置中提供
        """
        BaseResponseHandler.__init__(self)

        # 验证必需参数
        if not config.api_key:
            raise ValueError(
                "api_key is required in LLMConfig. "
                "Please provide it explicitly, do not rely on environment variables."
            )

        # 存储配置
        self.model = config.model
        self.temperature = config.temperature
        self.max_tokens = config.max_tokens

        # 创建 OpenAI 客户端
        self.client = AsyncOpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
            timeout=config.timeout,
            max_retries=config.max_retries,
            **kwargs,
        )

    def get_token_counter(self):
        """
        获取 Token 计数器

        返回 TiktokenCounter 用于精确计数。

        Returns:
            TiktokenCounter 实例
        """
        from loom.memory.tokenizer import TiktokenCounter

        return TiktokenCounter(self.model)

    def _convert_tools(self, tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        转换 MCP 工具定义到 OpenAI 格式

        Args:
            tools: MCP 工具定义列表

        Returns:
            OpenAI 格式的工具列表
        """
        openai_tools = []
        for tool in tools:
            # 如果已经是 OpenAI 格式，直接使用
            if "type" in tool and "function" in tool:
                openai_tools.append(tool)
                continue

            # 从 MCP 格式转换
            # MCP: name, description, inputSchema
            # OpenAI: type="function", function={name, description, parameters}
            function_def = {
                "name": tool.get("name"),
                "description": tool.get("description"),
                "parameters": tool.get("inputSchema", tool.get("parameters", {})),
            }

            openai_tools.append({"type": "function", "function": function_def})
        return openai_tools

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """
        非流式调用 OpenAI Chat API

        Args:
            messages: 对话历史
            tools: 可用工具列表
            **kwargs: 额外参数（覆盖默认配置）

        Returns:
            LLM响应
        """
        # 构建基础参数
        params: dict[str, Any] = {
            "model": kwargs.pop("model", self.model),
            "messages": messages,
            "temperature": kwargs.pop("temperature", self.temperature),
            "stream": False,
        }

        # 添加 max_tokens（如果设置）
        max_tokens = kwargs.pop("max_tokens", self.max_tokens)
        if max_tokens:
            params["max_tokens"] = max_tokens

        # 添加工具
        if tools:
            params["tools"] = self._convert_tools(tools)

        # 添加其他参数
        params.update(kwargs)

        # 调用 API
        response = await self.client.chat.completions.create(**params)

        # 提取响应
        message = response.choices[0].message
        content = message.content or ""

        # 提取工具调用
        tool_calls = []
        if message.tool_calls:
            for tc in message.tool_calls:
                tool_calls.append(
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                )

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            token_usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }
            if response.usage
            else None,
        )

    async def stream_chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> AsyncGenerator[StreamChunk, None]:
        """
        流式调用 OpenAI Chat API

        Args:
            messages: 对话历史
            tools: 可用工具列表
            **kwargs: 额外参数（覆盖默认配置）

        Yields:
            StreamChunk事件
        """
        # 构建基础参数
        params: dict[str, Any] = {
            "model": kwargs.pop("model", self.model),
            "messages": messages,
            "temperature": kwargs.pop("temperature", self.temperature),
            "stream": True,
            "stream_options": {"include_usage": True},
        }

        # 添加 max_tokens（如果设置）
        max_tokens = kwargs.pop("max_tokens", self.max_tokens)
        if max_tokens:
            params["max_tokens"] = max_tokens

        # 添加工具
        if tools:
            params["tools"] = self._convert_tools(tools)

        # 添加其他参数
        params.update(kwargs)

        try:
            # 调用 API
            stream = await self.client.chat.completions.create(**params)

            # 清空聚合器
            self.aggregator.clear()

            async for chunk in stream:
                if not chunk.choices:
                    # 处理 usage chunk（OpenAI 在最后发送）
                    if hasattr(chunk, "usage") and chunk.usage:
                        yield self.create_done_chunk(
                            finish_reason="usage_only",
                            token_usage={
                                "prompt_tokens": chunk.usage.prompt_tokens,
                                "completion_tokens": chunk.usage.completion_tokens,
                                "total_tokens": chunk.usage.total_tokens,
                            },
                        )
                    continue

                delta = chunk.choices[0].delta

                # 处理文本内容
                if delta.content:
                    yield StreamChunk(type="text", content=delta.content, metadata={})

                # 处理工具调用（使用 aggregator）
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        start_chunk = self.aggregator.add_chunk(
                            index=tc.index,
                            tool_id=tc.id,
                            name=tc.function.name,
                            arguments=tc.function.arguments,
                        )
                        if start_chunk:
                            yield start_chunk

                # 处理完成标记
                if chunk.choices[0].finish_reason:
                    # 发送所有完成的工具调用
                    for complete_chunk in self.aggregator.get_complete_calls():
                        yield complete_chunk

                    # 发送 done 事件
                    token_usage = None
                    if hasattr(chunk, "usage") and chunk.usage:
                        token_usage = {
                            "prompt_tokens": chunk.usage.prompt_tokens,
                            "completion_tokens": chunk.usage.completion_tokens,
                            "total_tokens": chunk.usage.total_tokens,
                        }

                    yield self.create_done_chunk(
                        finish_reason=chunk.choices[0].finish_reason,
                        token_usage=token_usage,
                    )

        except Exception as e:
            yield self.create_error_chunk(e)

    async def stream_response(self, response: Any) -> AsyncGenerator[StreamChunk, None]:
        """
        处理单个流式响应块（BaseResponseHandler要求的抽象方法）

        注意：当前OpenAI实现在stream_chat中直接处理流式响应，
        此方法提供以满足抽象接口要求。

        Args:
            response: OpenAI流式响应对象

        Yields:
            StreamChunk事件
        """
        # 清空聚合器
        self.aggregator.clear()

        async for chunk in response:
            if not chunk.choices:
                # 处理 usage chunk
                if hasattr(chunk, "usage") and chunk.usage:
                    yield self.create_done_chunk(
                        finish_reason="usage_only",
                        token_usage={
                            "prompt_tokens": chunk.usage.prompt_tokens,
                            "completion_tokens": chunk.usage.completion_tokens,
                            "total_tokens": chunk.usage.total_tokens,
                        },
                    )
                continue

            delta = chunk.choices[0].delta

            # 处理文本内容
            if delta.content:
                yield StreamChunk(type="text", content=delta.content, metadata={})

            # 处理工具调用
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    start_chunk = self.aggregator.add_chunk(
                        index=tc.index,
                        tool_id=tc.id,
                        name=tc.function.name,
                        arguments=tc.function.arguments,
                    )
                    if start_chunk:
                        yield start_chunk

            # 处理完成标记
            if chunk.choices[0].finish_reason:
                # 发送所有完成的工具调用
                for complete_chunk in self.aggregator.get_complete_calls():
                    yield complete_chunk

                # 发送 done 事件
                token_usage = None
                if hasattr(chunk, "usage") and chunk.usage:
                    token_usage = {
                        "prompt_tokens": chunk.usage.prompt_tokens,
                        "completion_tokens": chunk.usage.completion_tokens,
                        "total_tokens": chunk.usage.total_tokens,
                    }

                yield self.create_done_chunk(
                    finish_reason=chunk.choices[0].finish_reason,
                    token_usage=token_usage,
                )
