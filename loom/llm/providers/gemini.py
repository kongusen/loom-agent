"""
Google Gemini LLM Provider

支持 Gemini 系列模型的完整流式工具调用。
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
    import google.generativeai as genai
    from google.generativeai.types import GenerationConfig as GeminiGenConfig
except ImportError:
    raise ImportError(
        "Google Generative AI SDK not installed. Install with: pip install google-generativeai"
    ) from None


class GeminiProvider(LLMProvider):
    """
    Google Gemini Provider with streaming tool call support.

    使用方式：
    1. 简单配置：
        provider = GeminiProvider(api_key="...")

    2. 指定模型：
        provider = GeminiProvider(
            model="gemini-2.0-flash-exp",
            api_key="..."
        )
    """

    def __init__(
        self,
        config: LLMConfig | None = None,
        model: str | None = None,
        api_key: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs  # noqa: ARG002 - Reserved for future configuration options
    ):
        """初始化 Gemini Provider"""
        if config is None:
            config = LLMConfig()

            if api_key:
                config.connection = ConnectionConfig(api_key=api_key)

            if model or temperature is not None or max_tokens:
                config.generation = GenerationConfig(
                    model=model or "gemini-2.0-flash-exp",
                    temperature=float(temperature) if temperature is not None else 0.7,
                    max_tokens=int(max_tokens) if max_tokens else 8192
                )

        self.config = config

        # 配置 API Key
        api_key = config.connection.api_key or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("Google API Key is required")

        genai.configure(api_key=api_key)

        # 创建模型实例
        self.model = genai.GenerativeModel(
            model_name=config.generation.model
        )

    def _convert_messages(
        self,
        messages: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """转换消息格式为 Gemini 格式"""
        gemini_messages = []

        for msg in messages:
            role = msg["role"]
            content = msg["content"]

            # Gemini 使用 "user" 和 "model" 角色
            if role == "assistant":
                role = "model"
            elif role == "system":
                # System 消息转换为 user 消息
                role = "user"
                content = f"[System]: {content}"

            gemini_messages.append({
                "role": role,
                "parts": [{"text": content}]
            })

        return gemini_messages

    def _convert_tools(self, tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """转换工具定义为 Gemini 格式"""
        gemini_tools = []

        for tool in tools:
            # Gemini 工具格式
            tool_def = {
                "function_declarations": [{
                    "name": tool.get("name"),
                    "description": tool.get("description"),
                    "parameters": tool.get("inputSchema", tool.get("parameters", {}))
                }]
            }
            gemini_tools.append(tool_def)

        return gemini_tools

    def _build_generation_config(self) -> GeminiGenConfig:
        """构建生成配置，包含结构化输出"""
        config_kwargs: dict[str, Any] = {
            "temperature": self.config.generation.temperature,
            "max_output_tokens": self.config.generation.max_tokens
        }

        # 添加结构化输出配置
        if self.config.structured_output.enabled and self.config.structured_output.format in ["json_object", "json", "json_schema"]:
            config_kwargs["response_mime_type"] = "application/json"

            # 如果提供了 schema，添加 response_schema
            if self.config.structured_output.schema is not None:
                config_kwargs["response_schema"] = self.config.structured_output.schema

        return GeminiGenConfig(**config_kwargs)

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        _config: dict[str, Any] | None = None
    ) -> LLMResponse:
        """调用 Gemini Chat API"""
        # 转换消息
        gemini_messages = self._convert_messages(messages)

        # 构建生成配置（包含结构化输出）
        gen_config = self._build_generation_config()

        # 准备工具
        gemini_tools = None
        if tools:
            gemini_tools = self._convert_tools(tools)

        # 调用 API
        if gemini_tools:
            response = await self.model.generate_content_async(
                gemini_messages,
                generation_config=gen_config,
                tools=gemini_tools
            )
        else:
            response = await self.model.generate_content_async(
                gemini_messages,
                generation_config=gen_config
            )

        # 提取响应
        content = ""
        tool_calls = []

        if response.candidates:
            candidate = response.candidates[0]
            for part in candidate.content.parts:
                if hasattr(part, 'text'):
                    content += part.text
                elif hasattr(part, 'function_call'):
                    fc = part.function_call
                    tool_calls.append({
                        "id": f"call_{fc.name}",
                        "name": fc.name,
                        "arguments": json.dumps(dict(fc.args))
                    })

        # Token 使用统计
        token_usage = None
        if hasattr(response, 'usage_metadata'):
            usage = response.usage_metadata
            token_usage = {
                "prompt_tokens": usage.prompt_token_count,
                "completion_tokens": usage.candidates_token_count,
                "total_tokens": usage.total_token_count
            }

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            token_usage=token_usage
        )

    async def stream_chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None
    ) -> AsyncGenerator[StreamChunk, None]:
        """流式调用 Gemini Chat API（支持工具调用）"""
        # 转换消息
        gemini_messages = self._convert_messages(messages)

        # 构建生成配置（包含结构化输出）
        gen_config = self._build_generation_config()

        # 准备工具
        gemini_tools = None
        if tools:
            gemini_tools = self._convert_tools(tools)

        try:
            # 调用流式 API
            if gemini_tools:
                response = await self.model.generate_content_async(
                    gemini_messages,
                    generation_config=gen_config,
                    tools=gemini_tools,
                    stream=True
                )
            else:
                response = await self.model.generate_content_async(
                    gemini_messages,
                    generation_config=gen_config,
                    stream=True
                )

            # 工具调用缓冲区
            current_tool_call = None

            async for chunk in response:
                if not chunk.candidates:
                    continue

                candidate = chunk.candidates[0]

                for part in candidate.content.parts:
                    # 文本内容
                    if hasattr(part, 'text') and part.text:
                        yield StreamChunk(
                            type="text",
                            content=part.text,
                            metadata={}
                        )

                    # 工具调用
                    elif hasattr(part, 'function_call'):
                        fc = part.function_call

                        # 工具调用开始
                        if current_tool_call is None:
                            current_tool_call = {
                                "id": f"call_{fc.name}",
                                "name": fc.name,
                                "arguments": ""
                            }

                            yield StreamChunk(
                                type="tool_call_start",
                                content={
                                    "id": current_tool_call["id"],
                                    "name": fc.name,
                                    "index": 0
                                },
                                metadata={}
                            )

                        # 聚合参数
                        current_tool_call["arguments"] = json.dumps(dict(fc.args))

            # 完成工具调用
            if current_tool_call:
                try:
                    json.loads(current_tool_call["arguments"])
                    yield StreamChunk(
                        type="tool_call_complete",
                        content=current_tool_call,
                        metadata={"index": 0}
                    )
                except json.JSONDecodeError as e:
                    yield StreamChunk(
                        type="error",
                        content={
                            "error": "invalid_tool_arguments",
                            "message": f"Tool arguments are not valid JSON: {str(e)}",
                            "tool_call": current_tool_call
                        },
                        metadata={"index": 0}
                    )

            # 发送完成事件
            yield StreamChunk(
                type="done",
                content="",
                metadata={"finish_reason": "stop"}
            )

        except Exception as e:
            logger.error(f"Gemini stream error: {str(e)}")
            yield StreamChunk(
                type="error",
                content={
                    "error": "stream_error",
                    "message": str(e),
                    "type": type(e).__name__
                },
                metadata={}
            )
