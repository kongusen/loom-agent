"""
OpenAI LLM 集成示例 - BaseLLM Protocol 实现

这是一个集成示例，展示如何实现 BaseLLM Protocol 来集成 OpenAI API。

**依赖**:
```bash
pip install openai
```

**使用方式**:
```python
from examples.integrations.openai_llm import OpenAILLM
import loom, Message

llm = OpenAILLM(api_key="sk-...")
agent = loom.agent(name="assistant", llm=llm)

response = await agent.run(Message(role="user", content="Hello"))
print(response.content)
```

**特点**:
- 无需继承，直接实现 Protocol
- 只实现核心方法：stream()
- 支持所有 OpenAI 模型
- 支持工具调用 (function calling)
- 支持 JSON 模式 (structured output)
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
    OpenAI LLM 实现 - 实现 BaseLLM Protocol

    **支持的模型**:
    - GPT-4 系列: gpt-4, gpt-4-turbo, gpt-4o
    - GPT-3.5 系列: gpt-3.5-turbo
    - O1 系列: o1-preview, o1-mini

    Example::

        from examples.integrations.openai_llm import OpenAILLM

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
        初始化 OpenAI LLM

        Args:
            api_key: OpenAI API 密钥
            model: 模型名称 (default: "gpt-4")
            base_url: 可选的 API 基础 URL (用于代理或兼容 API)
            temperature: 采样温度 0-2 (default: 0.7)
            max_tokens: 最大生成 token 数 (default: None, 无限制)
            timeout: 请求超时时间（秒） (default: 120.0)
            max_retries: 最大重试次数 (default: 3)
            **kwargs: 其他 OpenAI API 参数
                - top_p: float
                - frequency_penalty: float
                - presence_penalty: float
                - stop: List[str]
                - seed: int (for reproducibility)

        Raises:
            ImportError: 如果未安装 openai 包
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
        统一流式生成接口 - OpenAI 实现

        实现了 BaseLLM Protocol 的 stream() 方法，支持：
        - 文本流式生成
        - 工具调用 (function calling)
        - JSON 模式 (structured output)

        Args:
            messages: OpenAI 格式消息列表
            tools: 可选的工具定义
            response_format: 可选的响应格式
            **kwargs: 额外的 OpenAI 参数（会覆盖初始化时的参数）

        Yields:
            LLMEvent: 标准事件流
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
        accumulator = OpenAIStreamAccumulator(mode='auto')
        finish_reason = None

        # 流式处理
        async for chunk in stream:
            accumulator.add(chunk)

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
        tool_calls = accumulator.get_tool_calls()
        if tool_calls:
            yield {
                "type": "tool_calls",
                "tool_calls": tool_calls
            }

        # 产出 finish 事件
        yield {
            "type": "finish",
            "finish_reason": finish_reason or ("tool_calls" if tool_calls else "stop")
        }

    def __repr__(self) -> str:
        """字符串表示"""
        return f"OpenAILLM(model={self._model}, temperature={self.temperature})"
