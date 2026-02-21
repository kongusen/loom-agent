"""
Google Gemini LLM Provider

基于配置对象的 Gemini Provider。

特性：
1. 使用 LLMConfig 统一配置管理
2. 保留 Gemini 特有的消息转换
3. 保留手动工具处理
4. 框架不读取环境变量，由用户控制配置来源
"""

import json
from collections.abc import AsyncGenerator
from typing import Any

from loom.config.llm import LLMConfig
from loom.providers.llm.base_handler import BaseResponseHandler
from loom.providers.llm.interface import LLMProvider, LLMResponse, StreamChunk

try:
    import google.generativeai as genai
    from google.generativeai.types import GenerationConfig as GeminiGenConfig
except ImportError:
    genai = None  # type: ignore
    GeminiGenConfig = None  # type: ignore


class GeminiProvider(LLMProvider, BaseResponseHandler):
    """
    Google Gemini Provider - 基于配置对象

    使用方式：
        from loom.config import LLMConfig

        config = LLMConfig(
            provider="gemini",
            model="gemini-2.0-flash-exp",
            api_key="...",  # 用户控制配置来源
            temperature=0.7,
            max_tokens=8192
        )

        provider = GeminiProvider(config)
    """

    def __init__(self, config: LLMConfig, **_kwargs: Any):
        """
        初始化 Gemini Provider

        Args:
            config: LLM 配置对象
            **kwargs: 额外参数（当前未使用）

        Raises:
            ValueError: 如果 api_key 未在配置中提供
            ImportError: 如果 Google Generative AI SDK 未安装
        """
        BaseResponseHandler.__init__(self)

        if genai is None:
            raise ImportError(
                "Google Generative AI SDK not installed. Install with: pip install google-generativeai"
            )

        # 验证必需参数
        if not config.api_key:
            raise ValueError(
                "api_key is required in LLMConfig. "
                "Please provide it explicitly, do not rely on environment variables."
            )

        # 存储配置
        self.model_name = config.model
        self.temperature = config.temperature
        self.max_tokens = config.max_tokens

        # 配置 API Key
        genai.configure(api_key=config.api_key)

        # 创建模型实例
        self.model = genai.GenerativeModel(model_name=config.model)

    def _convert_messages(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        转换消息格式为 Gemini 格式

        Gemini 使用 "user" 和 "model" 角色，消息格式为 parts

        Args:
            messages: 原始消息列表

        Returns:
            Gemini 格式的消息列表
        """
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

            gemini_messages.append({"role": role, "parts": [{"text": content}]})

        return gemini_messages

    def _convert_tools(self, tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        转换工具定义为 Gemini 格式

        Args:
            tools: MCP 工具定义列表

        Returns:
            Gemini 格式的工具列表
        """
        gemini_tools = []

        for tool in tools:
            # Gemini 工具格式使用 function_declarations
            tool_def = {
                "function_declarations": [
                    {
                        "name": tool.get("name"),
                        "description": tool.get("description"),
                        "parameters": tool.get("inputSchema", tool.get("parameters", {})),
                    }
                ]
            }
            gemini_tools.append(tool_def)

        return gemini_tools

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """
        非流式调用 Gemini Chat API

        Args:
            messages: 对话历史
            tools: 可用工具列表
            **kwargs: 额外参数（覆盖默认配置）

        Returns:
            LLM响应
        """
        # 转换消息
        gemini_messages = self._convert_messages(messages)

        # 构建生成配置
        gen_config = GeminiGenConfig(
            temperature=kwargs.pop("temperature", self.temperature),
            max_output_tokens=kwargs.pop("max_tokens", self.max_tokens),
        )

        # 准备工具
        gemini_tools = None
        if tools:
            gemini_tools = self._convert_tools(tools)

        # 调用 API
        if gemini_tools:
            response = await self.model.generate_content_async(
                gemini_messages, generation_config=gen_config, tools=gemini_tools
            )
        else:
            response = await self.model.generate_content_async(
                gemini_messages, generation_config=gen_config
            )

        # 提取响应
        content = ""
        tool_calls = []

        if response.candidates:
            candidate = response.candidates[0]
            for part in candidate.content.parts:
                if hasattr(part, "text"):
                    content += part.text
                elif hasattr(part, "function_call"):
                    fc = part.function_call
                    tool_calls.append(
                        {
                            "id": f"call_{fc.name}",
                            "type": "function",
                            "function": {
                                "name": fc.name,
                                "arguments": json.dumps(dict(fc.args)),
                            },
                        }
                    )

        # Token 使用统计
        token_usage = None
        if hasattr(response, "usage_metadata"):
            usage = response.usage_metadata
            token_usage = {
                "prompt_tokens": usage.prompt_token_count,
                "completion_tokens": usage.candidates_token_count,
                "total_tokens": usage.total_token_count,
            }

        return LLMResponse(content=content, tool_calls=tool_calls, token_usage=token_usage)

    async def stream_chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> AsyncGenerator[StreamChunk, None]:
        """
        流式调用 Gemini Chat API

        Args:
            messages: 对话历史
            tools: 可用工具列表
            **kwargs: 额外参数（覆盖默认配置）

        Yields:
            StreamChunk事件
        """
        # 转换消息
        gemini_messages = self._convert_messages(messages)

        # 构建生成配置
        gen_config = GeminiGenConfig(
            temperature=kwargs.pop("temperature", self.temperature),
            max_output_tokens=kwargs.pop("max_tokens", self.max_tokens),
        )

        # 准备工具
        gemini_tools = None
        if tools:
            gemini_tools = self._convert_tools(tools)

        try:
            # 调用流式 API
            if gemini_tools:
                response = await self.model.generate_content_async(
                    gemini_messages, generation_config=gen_config, tools=gemini_tools, stream=True
                )
            else:
                response = await self.model.generate_content_async(
                    gemini_messages, generation_config=gen_config, stream=True
                )

            # 工具调用缓冲区
            current_tool_call = None

            async for chunk in response:
                if not chunk.candidates:
                    continue

                candidate = chunk.candidates[0]

                for part in candidate.content.parts:
                    # 文本内容
                    if hasattr(part, "text") and part.text:
                        yield StreamChunk(type="text", content=part.text, metadata={})

                    # 工具调用
                    elif hasattr(part, "function_call"):
                        fc = part.function_call

                        # 工具调用开始
                        if current_tool_call is None:
                            current_tool_call = {
                                "id": f"call_{fc.name}",
                                "name": fc.name,
                                "arguments": "",
                            }

                            yield StreamChunk(
                                type="tool_call_start",
                                content={
                                    "id": current_tool_call["id"],
                                    "name": fc.name,
                                    "index": 0,
                                },
                                metadata={},
                            )

                        # 聚合参数
                        current_tool_call["arguments"] = json.dumps(dict(fc.args))

            # 完成工具调用
            if current_tool_call:
                try:
                    json.loads(current_tool_call["arguments"])
                    yield StreamChunk(
                        type="tool_call_complete", content=current_tool_call, metadata={"index": 0}
                    )
                except json.JSONDecodeError as e:
                    yield StreamChunk(
                        type="error",
                        content={
                            "error": "invalid_tool_arguments",
                            "message": f"Tool arguments are not valid JSON: {str(e)}",
                            "tool_call": current_tool_call,
                        },
                        metadata={"index": 0},
                    )

            # 发送完成事件
            yield self.create_done_chunk(finish_reason="stop")

        except Exception as e:
            yield self.create_error_chunk(e)
