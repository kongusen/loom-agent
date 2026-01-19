"""
Anthropic (Claude) LLM Provider

基于配置对象的 Anthropic Provider。

特性：
1. 使用 LLMConfig 统一配置管理
2. 保留 Anthropic 特有的消息转换
3. 保留手动工具处理（事件结构特殊）
4. 框架不读取环境变量，由用户控制配置来源
"""

import json
from collections.abc import AsyncGenerator
from typing import Any

from loom.config.llm import LLMConfig
from loom.providers.llm.base_handler import BaseResponseHandler
from loom.providers.llm.interface import LLMProvider, LLMResponse, StreamChunk

try:
    from anthropic import AsyncAnthropic
except ImportError:
    AsyncAnthropic = None  # type: ignore


class AnthropicProvider(LLMProvider, BaseResponseHandler):
    """
    Anthropic Claude Provider - 基于配置对象

    使用方式：
        from loom.config import LLMConfig

        config = LLMConfig(
            provider="anthropic",
            model="claude-3-5-sonnet-20241022",
            api_key="sk-ant-...",  # 用户控制配置来源
            temperature=0.7,
            max_tokens=4096
        )

        provider = AnthropicProvider(config)
    """

    def __init__(self, config: LLMConfig, **kwargs: Any):
        """
        初始化 Anthropic Provider

        Args:
            config: LLM 配置对象
            **kwargs: 额外参数传递给 AsyncAnthropic 客户端

        Raises:
            ValueError: 如果 api_key 未在配置中提供
            ImportError: 如果 Anthropic SDK 未安装
        """
        BaseResponseHandler.__init__(self)

        if AsyncAnthropic is None:
            raise ImportError("Anthropic SDK not installed. Install with: pip install anthropic")

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

        # 创建 Anthropic 客户端
        self.client = AsyncAnthropic(
            api_key=config.api_key,
            base_url=config.base_url,
            timeout=config.timeout,
            max_retries=config.max_retries,
            **kwargs,
        )

    def get_token_counter(self):
        """
        获取 Token 计数器

        返回 AnthropicCounter 用于估算计数。

        Returns:
            AnthropicCounter 实例
        """
        from loom.memory.tokenizer import AnthropicCounter

        return AnthropicCounter()

    def _convert_messages(
        self, messages: list[dict[str, Any]]
    ) -> tuple[str | None, list[dict[str, Any]]]:
        """
        转换消息格式，提取 system 消息

        Anthropic 要求 system 消息单独传递

        Args:
            messages: 原始消息列表

        Returns:
            (system消息, 转换后的消息列表)
        """
        system = None
        converted_messages = []

        for msg in messages:
            if msg["role"] == "system":
                system = msg["content"]
            else:
                converted_messages.append(msg)

        return system, converted_messages

    def _convert_tools(self, tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        转换工具定义为 Anthropic 格式

        Args:
            tools: MCP 工具定义列表

        Returns:
            Anthropic 格式的工具列表
        """
        anthropic_tools = []

        for tool in tools:
            # 如果已经是 Anthropic 格式，直接使用
            if "input_schema" in tool:
                anthropic_tools.append(tool)
                continue

            # 从 MCP 格式转换
            # MCP: name, description, inputSchema/parameters
            # Anthropic: name, description, input_schema
            tool_def = {
                "name": tool.get("name"),
                "description": tool.get("description"),
                "input_schema": tool.get("inputSchema", tool.get("parameters", {})),
            }

            anthropic_tools.append(tool_def)

        return anthropic_tools

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """
        非流式调用 Anthropic Chat API

        Args:
            messages: 对话历史
            tools: 可用工具列表
            **kwargs: 额外参数（覆盖默认配置）

        Returns:
            LLM响应
        """
        # 提取 system 消息
        system, converted_messages = self._convert_messages(messages)

        # 构建基础参数
        params: dict[str, Any] = {
            "model": kwargs.pop("model", self.model),
            "messages": converted_messages,
            "max_tokens": kwargs.pop("max_tokens", self.max_tokens),
            "temperature": kwargs.pop("temperature", self.temperature),
        }

        # 添加 system 消息
        if system:
            params["system"] = system

        # 添加工具
        if tools:
            params["tools"] = self._convert_tools(tools)

        # 添加其他参数
        params.update(kwargs)

        # 调用 API
        from typing import cast

        response = await self.client.messages.create(**cast(Any, params))

        # 提取响应
        content = ""
        tool_calls = []

        for block in response.content:
            if block.type == "text":
                content += block.text
            elif block.type == "tool_use":
                tool_calls.append(
                    {
                        "id": block.id,
                        "type": "function",
                        "function": {
                            "name": block.name,
                            "arguments": json.dumps(block.input),
                        },
                    }
                )

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            token_usage={
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
            },
        )

    async def stream_chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> AsyncGenerator[StreamChunk, None]:
        """
        流式调用 Anthropic Chat API

        Args:
            messages: 对话历史
            tools: 可用工具列表
            **kwargs: 额外参数（覆盖默认配置）

        Yields:
            StreamChunk事件
        """
        # 提取 system 消息
        system, converted_messages = self._convert_messages(messages)

        # 构建基础参数
        params: dict[str, Any] = {
            "model": kwargs.pop("model", self.model),
            "messages": converted_messages,
            "max_tokens": kwargs.pop("max_tokens", self.max_tokens),
            "temperature": kwargs.pop("temperature", self.temperature),
            "stream": True,
        }

        # 添加 system 消息
        if system:
            params["system"] = system

        # 添加工具
        if tools:
            params["tools"] = self._convert_tools(tools)

        # 添加其他参数
        params.update(kwargs)

        try:
            # 调用流式 API
            from typing import cast

            stream = await self.client.messages.create(**cast(Any, params))

            # 工具调用缓冲区
            current_tool_use = None
            input_json_buffer = ""

            async for event in stream:
                # content_block_start - 新内容块开始
                if event.type == "content_block_start":
                    if event.content_block.type == "tool_use":
                        # 工具调用开始
                        current_tool_use = {
                            "id": event.content_block.id,
                            "name": event.content_block.name,
                            "input": "",
                        }
                        input_json_buffer = ""

                        yield StreamChunk(
                            type="tool_call_start",
                            content={
                                "id": current_tool_use["id"],
                                "name": current_tool_use["name"],
                                "index": event.index,
                            },
                            metadata={},
                        )

                # content_block_delta - 内容增量
                elif event.type == "content_block_delta":
                    if event.delta.type == "text_delta":
                        # 文本内容
                        yield StreamChunk(type="text", content=event.delta.text, metadata={})

                    elif event.delta.type == "input_json_delta" and current_tool_use:
                        # 工具调用参数增量
                        input_json_buffer += event.delta.partial_json

                # content_block_stop - 内容块结束
                elif event.type == "content_block_stop":
                    if current_tool_use:
                        # 工具调用完成
                        current_tool_use["input"] = input_json_buffer

                        # 验证 JSON
                        try:
                            json.loads(input_json_buffer)
                            yield StreamChunk(
                                type="tool_call_complete",
                                content={
                                    "id": current_tool_use["id"],
                                    "name": current_tool_use["name"],
                                    "arguments": input_json_buffer,
                                },
                                metadata={"index": event.index},
                            )
                        except json.JSONDecodeError as e:
                            yield StreamChunk(
                                type="error",
                                content={
                                    "error": "invalid_tool_arguments",
                                    "message": f"Tool {current_tool_use['name']} arguments are not valid JSON: {str(e)}",
                                    "tool_call": current_tool_use,
                                },
                                metadata={"index": event.index},
                            )

                        current_tool_use = None
                        input_json_buffer = ""

                # message_stop - 消息结束
                elif event.type == "message_stop":
                    # 获取 usage 信息
                    token_usage = None
                    if hasattr(event, "message") and hasattr(event.message, "usage"):
                        usage = event.message.usage
                        token_usage = {
                            "prompt_tokens": usage.input_tokens,
                            "completion_tokens": usage.output_tokens,
                            "total_tokens": usage.input_tokens + usage.output_tokens,
                        }

                    yield self.create_done_chunk(
                        finish_reason="stop",
                        token_usage=token_usage,
                    )

        except Exception as e:
            yield self.create_error_chunk(e)
