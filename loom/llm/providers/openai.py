"""
OpenAI LLM Provider

支持完整的 LLM 配置体系。
"""

import os
from collections.abc import AsyncGenerator
from typing import Any

from loom.config.llm import (
    ConnectionConfig,
    GenerationConfig,
    LLMConfig,
    StreamConfig,
)
from loom.llm.interface import LLMProvider, LLMResponse, StreamChunk

try:
    from openai import AsyncOpenAI
except ImportError:
    raise ImportError(
        "OpenAI SDK not installed. Install with: pip install loom-agent[llm]"
    ) from None


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
        config: LLMConfig | None = None,
        # 快速配置参数（向后兼容）
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        stream: bool | None = None,
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

    def _convert_tools(self, tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Convert MCP tool definitions to OpenAI format."""
        openai_tools = []
        for tool in tools:
            # Check if it's already in OpenAI format
            if "type" in tool and "function" in tool:
                openai_tools.append(tool)
                continue

            # Convert from MCP format
            # MCP: name, description, inputSchema
            # OpenAI: type="function", function={name, description, parameters}
            function_def = {
                "name": tool.get("name"),
                "description": tool.get("description"),
                "parameters": tool.get("inputSchema", tool.get("parameters", {}))
            }

            openai_tools.append({
                "type": "function",
                "function": function_def
            })
        return openai_tools

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        config: dict[str, Any] | None = None
    ) -> LLMResponse:
        """调用 OpenAI Chat API（使用配置体系）"""
        # 获取基础参数
        kwargs = self.config.to_openai_kwargs()
        kwargs["messages"] = messages

        # chat方法强制禁用流式输出（流式输出应使用stream_chat方法）
        kwargs["stream"] = False
        if "stream_options" in kwargs:
            del kwargs["stream_options"]

        # 添加工具
        if tools:
            kwargs["tools"] = self._convert_tools(tools)
            kwargs["tool_choice"] = self.config.tool.tool_choice
            kwargs["parallel_tool_calls"] = self.config.tool.parallel_tool_calls

        # 添加结构化输出
        response_format = self.config.structured_output.to_openai_format()
        if response_format:
            kwargs["response_format"] = response_format

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
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None
    ) -> AsyncGenerator[StreamChunk, None]:
        """流式调用 OpenAI Chat API（增强版：实时工具调用通知）"""
        # 获取基础参数
        kwargs = self.config.to_openai_kwargs()
        kwargs["messages"] = messages
        kwargs["stream"] = True
        kwargs["stream_options"] = {"include_usage": True}  # 获取 token usage

        # 添加工具
        if tools:
            kwargs["tools"] = self._convert_tools(tools)
            kwargs["tool_choice"] = self.config.tool.tool_choice
            kwargs["parallel_tool_calls"] = self.config.tool.parallel_tool_calls

        # 添加结构化输出
        response_format = self.config.structured_output.to_openai_format()
        if response_format:
            kwargs["response_format"] = response_format

        try:
            # 调用 API
            stream = await self.client.chat.completions.create(**kwargs)

            # 工具调用聚合缓冲区
            tool_calls_buffer: dict[int, dict[str, Any]] = {}
            # 跟踪哪些工具调用已经发送了 start 事件
            tool_calls_started: dict[int, bool] = {}

            async for chunk in stream:
                if not chunk.choices:
                    # 处理 usage chunk（OpenAI 在最后发送）
                    if hasattr(chunk, 'usage') and chunk.usage:
                        yield StreamChunk(
                            type="done",
                            content="",
                            metadata={
                                "finish_reason": "usage_only",
                                "token_usage": {
                                    "prompt_tokens": chunk.usage.prompt_tokens,
                                    "completion_tokens": chunk.usage.completion_tokens,
                                    "total_tokens": chunk.usage.total_tokens
                                }
                            }
                        )
                    continue

                delta = chunk.choices[0].delta

                # 文本内容
                if delta.content:
                    yield StreamChunk(
                        type="text",
                        content=delta.content,
                        metadata={}
                    )

                # 工具调用 - 实时通知 + 聚合
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        idx = tc.index

                        # 第一次看到这个 tool_call - 发送 start 事件
                        if idx not in tool_calls_buffer:
                            tool_calls_buffer[idx] = {
                                "id": tc.id or "",
                                "name": tc.function.name or "",
                                "arguments": ""
                            }
                            tool_calls_started[idx] = False

                        # 聚合内容
                        if tc.id:
                            tool_calls_buffer[idx]["id"] = tc.id
                        if tc.function.name:
                            tool_calls_buffer[idx]["name"] = tc.function.name
                        if tc.function.arguments:
                            tool_calls_buffer[idx]["arguments"] += tc.function.arguments

                        # 当我们有了 name 且还没发送 start 事件时，发送它
                        if (tool_calls_buffer[idx]["name"] and
                            not tool_calls_started[idx]):
                            yield StreamChunk(
                                type="tool_call_start",
                                content={
                                    "id": tool_calls_buffer[idx]["id"],
                                    "name": tool_calls_buffer[idx]["name"],
                                    "index": idx
                                },
                                metadata={}
                            )
                            tool_calls_started[idx] = True

                # 结束标记
                if chunk.choices[0].finish_reason:
                    # Yield 所有完成的 tool_calls
                    for idx, tc in tool_calls_buffer.items():
                        if tc.get("id") and tc.get("name"):
                            # 验证 arguments 是否是有效 JSON
                            try:
                                import json
                                json.loads(tc["arguments"])  # 验证
                                yield StreamChunk(
                                    type="tool_call_complete",
                                    content=tc,
                                    metadata={"index": idx}
                                )
                            except json.JSONDecodeError as e:
                                yield StreamChunk(
                                    type="error",
                                    content={
                                        "error": "invalid_tool_arguments",
                                        "message": f"Tool {tc['name']} arguments are not valid JSON: {str(e)}",
                                        "tool_call": tc
                                    },
                                    metadata={"index": idx}
                                )

                    # 发送 done 事件
                    done_metadata = {"finish_reason": chunk.choices[0].finish_reason}

                    # 如果有 usage 信息，添加到 metadata
                    if hasattr(chunk, 'usage') and chunk.usage:
                        done_metadata["token_usage"] = {
                            "prompt_tokens": chunk.usage.prompt_tokens,
                            "completion_tokens": chunk.usage.completion_tokens,
                            "total_tokens": chunk.usage.total_tokens
                        }

                    yield StreamChunk(
                        type="done",
                        content="",
                        metadata=done_metadata
                    )

        except Exception as e:
            # 捕获所有异常并作为 error chunk 返回
            yield StreamChunk(
                type="error",
                content={
                    "error": "stream_error",
                    "message": str(e),
                    "type": type(e).__name__
                },
                metadata={}
            )
