"""
Anthropic (Claude) LLM Provider

支持 Claude 系列模型的完整流式工具调用。
"""

import json
import logging
import os
from collections.abc import AsyncGenerator
from typing import Any

from loom.config.llm import ConnectionConfig, GenerationConfig, LLMConfig
from loom.llm.interface import LLMProvider, LLMResponse, StreamChunk

logger = logging.getLogger(__name__)

try:
    from anthropic import AsyncAnthropic
except ImportError:
    raise ImportError("Anthropic SDK not installed. Install with: pip install anthropic") from None


class AnthropicProvider(LLMProvider):
    """
    Anthropic Claude Provider with streaming tool call support.

    支持三种使用方式：
    1. 最简单（自动读取环境变量）：
        provider = AnthropicProvider()

    2. 快速配置：
        provider = AnthropicProvider(
            model="claude-opus-4-20250514",
            api_key="sk-ant-..."
        )

    3. 完整配置：
        config = LLMConfig(...)
        provider = AnthropicProvider(config=config)
    """

    def __init__(
        self,
        config: LLMConfig | None = None,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs,
    ):
        """初始化 Anthropic Provider"""
        if config is None:
            config = LLMConfig()

            if api_key or base_url:
                config.connection = ConnectionConfig(api_key=api_key, base_url=base_url)

            if model or temperature is not None or max_tokens:
                config.generation = GenerationConfig(
                    model=model or "claude-3-5-sonnet-20241022",
                    temperature=temperature if temperature is not None else 0.7,
                    max_tokens=max_tokens or 4096,
                )

        self.config = config

        # 创建 Anthropic 客户端
        self.client = AsyncAnthropic(
            api_key=config.connection.api_key or os.getenv("ANTHROPIC_API_KEY"),
            base_url=config.connection.base_url,
            timeout=config.connection.timeout,
            max_retries=config.connection.max_retries,
            **kwargs,
        )

    def _convert_messages(
        self, messages: list[dict[str, Any]]
    ) -> tuple[str | None, list[dict[str, Any]]]:
        """
        转换消息格式，提取 system 消息

        Anthropic 要求 system 消息单独传递
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
        """转换工具定义为 Anthropic 格式"""
        anthropic_tools = []

        for tool in tools:
            # 检查是否已经是 Anthropic 格式
            if "input_schema" in tool:
                anthropic_tools.append(tool)
                continue

            # 从 MCP/OpenAI 格式转换
            tool_def = {
                "name": tool.get("name"),
                "description": tool.get("description"),
                "input_schema": tool.get("inputSchema", tool.get("parameters", {})),
            }

            anthropic_tools.append(tool_def)

        return anthropic_tools

    def _build_structured_output_prompt(self) -> str | None:
        """构建结构化输出的 system prompt"""
        if not self.config.structured_output.enabled:
            return None

        prompt_parts = []

        if self.config.structured_output.format in ["json_object", "json", "json_schema"]:
            prompt_parts.append(
                "You must respond with valid JSON only. Do not include any text outside the JSON structure."
            )

            # 如果提供了 schema，添加到 prompt 中
            if self.config.structured_output.schema is not None:
                import json

                schema_str = json.dumps(self.config.structured_output.schema, indent=2)
                prompt_parts.append(
                    f"\nYour response must conform to this JSON schema:\n{schema_str}"
                )

        return "\n".join(prompt_parts) if prompt_parts else None

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        config: dict[str, Any] | None = None,
    ) -> LLMResponse:
        """调用 Anthropic Chat API"""
        # 提取 system 消息
        system, converted_messages = self._convert_messages(messages)

        # 添加结构化输出指令到 system prompt
        structured_prompt = self._build_structured_output_prompt()
        if structured_prompt:
            system = f"{system}\n\n{structured_prompt}" if system else structured_prompt

        # 构建请求参数
        kwargs = {
            "model": self.config.generation.model,
            "messages": converted_messages,
            "max_tokens": self.config.generation.max_tokens,
            "temperature": self.config.generation.temperature,
        }

        if system:
            kwargs["system"] = system

        # 添加工具
        if tools:
            kwargs["tools"] = self._convert_tools(tools)

        # 覆盖配置
        if config:
            kwargs.update(config)

        # 调用 API
        from typing import cast

        response = await self.client.messages.create(**cast(Any, kwargs))

        # 提取响应
        content = ""
        tool_calls = []

        for block in response.content:
            if block.type == "text":
                content += block.text
            elif block.type == "tool_use":
                tool_calls.append(
                    {"id": block.id, "name": block.name, "arguments": json.dumps(block.input)}
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
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None
    ) -> AsyncGenerator[StreamChunk, None]:
        """流式调用 Anthropic Chat API（支持工具调用）"""
        # 提取 system 消息
        system, converted_messages = self._convert_messages(messages)

        # 添加结构化输出指令到 system prompt
        structured_prompt = self._build_structured_output_prompt()
        if structured_prompt:
            system = f"{system}\n\n{structured_prompt}" if system else structured_prompt

        # 构建请求参数
        kwargs = {
            "model": self.config.generation.model,
            "messages": converted_messages,
            "max_tokens": self.config.generation.max_tokens,
            "temperature": self.config.generation.temperature,
            "stream": True,
        }

        if system:
            kwargs["system"] = system

        # 添加工具
        if tools:
            kwargs["tools"] = self._convert_tools(tools)

        try:
            # 调用流式 API
            # Cast kwargs to Any to bypass overload resolution issues with dynamic unpacking
            # Anthropic client expects specific typed arguments but we build them dynamically
            from typing import cast

            stream = await self.client.messages.create(**cast(Any, kwargs))

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
                    if hasattr(event, "message") and hasattr(event.message, "usage"):
                        usage = event.message.usage
                        yield StreamChunk(
                            type="done",
                            content="",
                            metadata={
                                "finish_reason": "stop",
                                "token_usage": {
                                    "prompt_tokens": usage.input_tokens,
                                    "completion_tokens": usage.output_tokens,
                                    "total_tokens": usage.input_tokens + usage.output_tokens,
                                },
                            },
                        )
                    else:
                        yield StreamChunk(
                            type="done", content="", metadata={"finish_reason": "stop"}
                        )

        except Exception as e:
            logger.error(f"Anthropic stream error: {str(e)}")
            yield StreamChunk(
                type="error",
                content={"error": "stream_error", "message": str(e), "type": type(e).__name__},
                metadata={},
            )
