"""
统一 LLM - 支持所有 OpenAI 兼容的提供商

这个类使用 OpenAI SDK，但可以配置不同的 base_url 来支持各种兼容提供商。

支持的提供商：
- OpenAI (原生)
- DeepSeek, Qwen, Kimi, 智谱, 豆包, 零一万物（国产主流模型）
"""

from __future__ import annotations

import json
from typing import Any, AsyncGenerator, Dict, List, Optional

from loom.interfaces.llm import LLMEvent
from loom.utils.stream_accumulator import OpenAIStreamAccumulator
from loom.builtin.llms.providers import (
    OPENAI_COMPATIBLE_PROVIDERS,
    get_provider_info,
    is_openai_compatible,
)
from loom.builtin.llms.base import BaseLLM
from loom.core.runnable import RunnableConfig
from loom.core.message import Message, AssistantMessage, ToolCall

try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None  # type: ignore


class UnifiedLLM(BaseLLM):
    """
    统一 LLM - 支持所有 OpenAI 兼容的提供商
    ...
    """

    def __init__(
        self,
        api_key: str,
        provider: str = "openai",
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        timeout: float = 120.0,
        max_retries: int = 3,
        **kwargs: Any,
    ) -> None:
        """..."""
        if AsyncOpenAI is None:
            raise ImportError(
                "OpenAI package not installed. "
                "Install it with: pip install openai"
            )

        # 验证提供商
        if not is_openai_compatible(provider):
            raise ValueError(
                f"提供商 '{provider}' 不支持或不兼容 OpenAI 格式。\n"
                f"支持的提供商: {', '.join(OPENAI_COMPATIBLE_PROVIDERS.keys())}"
            )

        # 获取提供商配置
        provider_config = get_provider_info(provider)
        if not provider_config:
            raise ValueError(f"无法找到提供商配置: {provider}")

        self.provider = provider
        self._model = model or provider_config["default_model"]

        # 处理 base_url
        if provider == "custom":
            # 自定义提供商必须指定 base_url
            if not base_url:
                raise ValueError(
                    "使用自定义提供商时必须指定 base_url。\n"
                    "示例: UnifiedLLM(provider='custom', base_url='https://your-api.com/v1', api_key='...', model='...')"
                )
            self._base_url = base_url
        else:
            # 其他提供商使用配置的 base_url，但允许覆盖
            self._base_url = base_url or provider_config["base_url"]

        # 创建 OpenAI 客户端
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=self._base_url,
            timeout=timeout,
            max_retries=max_retries,
        )

        self.model_name = f"{self.provider}/{self._model}" # BaseLLM requires model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.kwargs = kwargs

    async def invoke(
        self,
        input: List[Message],
        config: Optional[RunnableConfig] = None,
        tools: Optional[List[Dict]] = None,
        **kwargs
    ) -> AssistantMessage:
        """Synchronous-semantic execution."""
        messages = [msg.to_openai_dict() if hasattr(msg, 'to_openai_dict') else msg for msg in input]
        
        # Build params
        params = {
            "model": self._model,
            "messages": messages,
            "temperature": self.temperature,
            "stream": False,
        }
        if self.max_tokens:
            params["max_tokens"] = self.max_tokens
        if tools:
            params["tools"] = tools
            
        merged_kwargs = {**self.kwargs, **kwargs}
        params.update(merged_kwargs)
        
        response = await self.client.chat.completions.create(**params)
        choice = response.choices[0]
        msg = choice.message
        
        content = msg.content or ""
        tool_calls = []
        if msg.tool_calls:
            for tc in msg.tool_calls:
                tool_calls.append(ToolCall(
                    id=tc.id,
                    type=tc.type,
                    function={
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                ))
                
        return AssistantMessage(content=content, tool_calls=tool_calls if tool_calls else None)

    @property
    def model_name_prop(self) -> str:
        """返回模型名称（包含提供商信息）"""
        return self.model_name

    async def stream(
        self,
        input: List[Message],
        config: Optional[RunnableConfig] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs: Any
    ) -> AsyncGenerator[LLMEvent, None]:
        """
        统一流式生成接口

        实现了 BaseLLM Protocol 的 stream() 方法，支持：
        - 文本流式生成
        - 工具调用 (function calling)
        - JSON 模式 (structured output)

        Args:
            messages: OpenAI 格式消息列表
            tools: 可选的工具定义
            response_format: 可选的响应格式
            **kwargs: 额外的参数（会覆盖初始化时的参数）

        Yields:
            LLMEvent: 标准事件流
                - {"type": "content_delta", "content": "..."}
                - {"type": "tool_calls", "tool_calls": [...]}
                - {"type": "finish", "finish_reason": "stop"}

        Example::

            # 文本生成
            async for event in llm.stream(messages):
                if event["type"] == "content_delta":
                    print(event["content"], end="")
                elif event["type"] == "finish":
                    print(f"\\nDone: {event['finish_reason']}")

            # 工具调用
            async for event in llm.stream(messages, tools=tools):
                if event["type"] == "tool_calls":
                    for tc in event["tool_calls"]:
                        print(f"Tool: {tc['name']}")
        """
        # Convert Loom Messages to OpenAI format
        messages = [msg.to_openai_dict() if hasattr(msg, 'to_openai_dict') else msg for msg in input]
        
        # Extract response_format from kwargs if present
        response_format = kwargs.pop("response_format", None)

        # 构建请求参数
        params = {
            "model": self._model,
            "messages": messages,
            "temperature": self.temperature,
            "stream": True,
        }

        if self.max_tokens:
            params["max_tokens"] = self.max_tokens

        # 添加 tools
        if tools:
            params["tools"] = tools

        # 添加 response_format (JSON mode)
        if response_format:
            params["response_format"] = response_format

        # 合并额外参数 (kwargs 优先级更高)
        merged_kwargs = {**self.kwargs, **kwargs}
        params.update(merged_kwargs)

        # 创建流式请求
        stream = await self.client.chat.completions.create(**params)

        # 使用 OpenAIStreamAccumulator 处理混合类型和工具调用
        accumulator = OpenAIStreamAccumulator()
        finish_reason = None

        # 流式处理
        async for chunk in stream:
            # 将 OpenAI SDK 对象转换为字典格式
            # 尝试使用 model_dump() 方法（Pydantic 模型）
            if hasattr(chunk, 'model_dump'):
                chunk_dict = chunk.model_dump()
            else:
                # 手动构建字典格式
                chunk_dict = {
                    "choices": []
                }
                if chunk.choices:
                    for choice in chunk.choices:
                        delta_dict = {}
                        if choice.delta.content:
                            delta_dict["content"] = choice.delta.content
                        if hasattr(choice.delta, 'role') and choice.delta.role:
                            delta_dict["role"] = choice.delta.role
                        if hasattr(choice.delta, 'tool_calls') and choice.delta.tool_calls:
                            delta_dict["tool_calls"] = []
                            for tc in choice.delta.tool_calls:
                                tc_dict = {"index": tc.index}
                                if hasattr(tc, 'id') and tc.id:
                                    tc_dict["id"] = tc.id
                                if hasattr(tc, 'type'):
                                    tc_dict["type"] = tc.type
                                else:
                                    tc_dict["type"] = "function"
                                if hasattr(tc, 'function'):
                                    func_dict = {}
                                    if hasattr(tc.function, 'name') and tc.function.name:
                                        func_dict["name"] = tc.function.name
                                    if hasattr(tc.function, 'arguments') and tc.function.arguments:
                                        func_dict["arguments"] = tc.function.arguments
                                    if func_dict:
                                        tc_dict["function"] = func_dict
                                delta_dict["tool_calls"].append(tc_dict)
                        
                        choice_dict = {"delta": delta_dict}
                        if hasattr(choice, 'finish_reason') and choice.finish_reason:
                            choice_dict["finish_reason"] = choice.finish_reason
                        chunk_dict["choices"].append(choice_dict)
            
            accumulator.update(chunk_dict)

            # 检查 chunk 有效性
            if not chunk.choices or len(chunk.choices) == 0:
                continue

            choice = chunk.choices[0]
            delta = choice.delta
            finish_reason = choice.finish_reason

            # 实时产出 content deltas
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

        # 流结束后，产出 tool_calls (如果有)
        if accumulator.has_tool_calls():
            yield {
                "type": "tool_calls",
                "tool_calls": accumulator.get_loom_tool_calls()
            }

        # 产出 finish 事件
        yield {
            "type": "finish",
            "finish_reason": finish_reason or ("tool_calls" if accumulator.has_tool_calls() else "stop")
        }

    def __repr__(self) -> str:
        """字符串表示"""
        return f"UnifiedLLM(provider={self.provider}, model={self._model}, temperature={self.temperature})"
