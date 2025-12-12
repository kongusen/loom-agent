"""
LLM统一接口 - 基于Protocol的结构化子类型

核心设计：
- 使用Protocol而非ABC，支持鸭子类型
- 只有一个核心方法：stream()
- 统一处理文本、工具调用、JSON模式
"""

from __future__ import annotations

from typing import Protocol, AsyncGenerator, Optional, List, Dict, Any, Literal
from typing_extensions import runtime_checkable, TypedDict


# ============================================================================
# 标准事件类型定义
# ============================================================================

class ContentDeltaEvent(TypedDict):
    """内容增量事件"""
    type: Literal["content_delta"]
    content: str


class ToolCallsEvent(TypedDict):
    """工具调用事件"""
    type: Literal["tool_calls"]
    tool_calls: List[Dict[str, Any]]


class FinishEvent(TypedDict):
    """完成事件"""
    type: Literal["finish"]
    finish_reason: str


# 联合类型
LLMEvent = ContentDeltaEvent | ToolCallsEvent | FinishEvent


# ============================================================================
# BaseLLM Protocol
# ============================================================================

@runtime_checkable
class BaseLLM(Protocol):
    """
    LLM统一接口 - 基于Protocol的结构化子类型

    **核心方法**:
    只需实现一个方法：:meth:`stream`

    **为什么用Protocol？**

    1. **鸭子类型** - 不需要继承，只要实现接口即可
    2. **运行时检查** - @runtime_checkable 支持 isinstance() 检查
    3. **零依赖** - 子类无需导入父类
    4. **简单** - 只需实现1个方法而非4个

    **实现要求**:

    .. code-block:: python

        class MyLLM:
            @property
            def model_name(self) -> str:
                return "my-model"

            async def stream(
                self,
                messages: List[Dict],
                tools: Optional[List[Dict]] = None,
                response_format: Optional[Dict] = None,
                **kwargs
            ) -> AsyncGenerator[LLMEvent, None]:
                # 实现流式生成
                async for chunk in api_stream:
                    yield {"type": "content_delta", "content": chunk}
                yield {"type": "finish", "finish_reason": "stop"}

    **事件流格式**:

    1. Content Delta - 文本增量::

        {
            "type": "content_delta",
            "content": str  # 文本块
        }

    2. Tool Calls - 工具调用 (流结束时发出)::

        {
            "type": "tool_calls",
            "tool_calls": [
                {
                    "id": str,
                    "name": str,
                    "arguments": dict
                },
                ...
            ]
        }

    3. Finish - 完成标记::

        {
            "type": "finish",
            "finish_reason": "stop" | "tool_calls" | "length" | "content_filter"
        }

    **使用示例**:

    .. code-block:: python

        # 文本生成
        async for event in llm.stream(messages):
            if event["type"] == "content_delta":
                print(event["content"], end="", flush=True)
            elif event["type"] == "finish":
                print(f"\\nFinished: {event['finish_reason']}")

        # 工具调用
        async for event in llm.stream(messages, tools=tools_spec):
            if event["type"] == "content_delta":
                print(event["content"], end="")
            elif event["type"] == "tool_calls":
                for tc in event["tool_calls"]:
                    result = execute_tool(tc)
            elif event["type"] == "finish":
                print(f"\\nDone: {event['finish_reason']}")

        # JSON模式
        json_parts = []
        async for event in llm.stream(
            messages,
            response_format={"type": "json_object"}
        ):
            if event["type"] == "content_delta":
                json_parts.append(event["content"])

        result = json.loads("".join(json_parts))

    **类型检查**:

    .. code-block:: python

        from loom.interfaces.llm import BaseLLM

        def use_llm(llm: BaseLLM):
            # 运行时检查
            assert isinstance(llm, BaseLLM), "Must implement BaseLLM protocol"

            # 类型安全调用
            async for event in llm.stream([...]):
                ...
    """

    @property
    def model_name(self) -> str:
        """
        返回模型标识符

        Returns:
            str: 模型名称，如 'gpt-4', 'claude-3-opus-20240229'

        Example::

            llm = OpenAILLM(model="gpt-4")
            print(llm.model_name)  # "gpt-4"
        """
        ...

    async def stream(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        response_format: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ) -> AsyncGenerator[LLMEvent, None]:
        """
        统一流式生成接口 - 唯一必须实现的方法

        这个方法支持所有LLM能力：
        - 纯文本生成
        - 工具调用 (function calling)
        - JSON模式 (structured output)
        - 流式输出

        Args:
            messages: OpenAI格式的消息列表
                每个消息格式::

                    {
                        "role": "user" | "assistant" | "system" | "tool",
                        "content": str,
                        "tool_calls": [...],  # 仅assistant消息
                        "tool_call_id": str   # 仅tool消息
                    }

            tools: 可选的工具定义列表 (OpenAI function calling格式)
                格式::

                    [
                        {
                            "type": "function",
                            "function": {
                                "name": str,
                                "description": str,
                                "parameters": {
                                    "type": "object",
                                    "properties": {...}
                                }
                            }
                        },
                        ...
                    ]

            response_format: 可选的响应格式
                JSON模式示例::

                    {"type": "json_object"}

                或结构化输出 (如果提供商支持)::

                    {
                        "type": "json_schema",
                        "json_schema": {
                            "name": "response",
                            "schema": {...}
                        }
                    }

            **kwargs: 提供商特定参数
                OpenAI示例::

                    temperature=0.7,
                    max_tokens=1000,
                    top_p=0.9

        Yields:
            LLMEvent: 事件字典，类型为：

            - ``content_delta``: 文本增量
            - ``tool_calls``: 工具调用 (流结束时)
            - ``finish``: 完成标记

        Raises:
            NotImplementedError: 如果子类未实现此方法
            ValueError: 如果参数格式不正确
            Exception: 提供商API错误

        Note:
            - 必须至少yield一个事件
            - 最后必须yield ``finish`` 事件
            - ``tool_calls`` 事件应在所有 ``content_delta`` 之后
            - 支持并发调用 (线程安全)

        Performance:
            - 首字节延迟: ~200-500ms
            - 后续字节: ~20-50ms
            - 内存占用: O(1) (流式)

        Example Implementation::

            class MyLLM:
                async def stream(self, messages, tools=None, **kwargs):
                    # 调用API
                    api_stream = await self.client.stream(messages, tools=tools)

                    # 产出content deltas
                    async for chunk in api_stream:
                        if chunk.content:
                            yield {
                                "type": "content_delta",
                                "content": chunk.content
                            }

                    # 产出tool calls (如果有)
                    if accumulated_tool_calls:
                        yield {
                            "type": "tool_calls",
                            "tool_calls": accumulated_tool_calls
                        }

                    # 产出finish
                    yield {
                        "type": "finish",
                        "finish_reason": "stop"
                    }
        """
        ...


# ============================================================================
# 工具函数
# ============================================================================

def is_llm(obj: Any) -> bool:
    """
    检查对象是否实现了BaseLLM协议

    Args:
        obj: 要检查的对象

    Returns:
        bool: 是否实现了BaseLLM

    Example::

        from loom.builtin.llms import OpenAILLM
        from loom.interfaces.llm import is_llm

        llm = OpenAILLM(api_key="...")
        assert is_llm(llm)  # True

        not_llm = "string"
        assert not is_llm(not_llm)  # False
    """
    return isinstance(obj, BaseLLM)


def validate_llm(obj: Any, name: str = "llm") -> None:
    """
    验证对象实现了BaseLLM协议，否则抛出异常

    Args:
        obj: 要验证的对象
        name: 参数名（用于错误消息）

    Raises:
        TypeError: 如果对象未实现BaseLLM

    Example::

        from loom.interfaces.llm import validate_llm

        def use_llm(llm):
            validate_llm(llm)  # 确保实现了协议
            async for event in llm.stream([...]):
                ...
    """
    if not isinstance(obj, BaseLLM):
        raise TypeError(
            f"{name} must implement BaseLLM protocol. "
            f"Got {type(obj).__name__} which is missing required methods. "
            f"Required: model_name property and stream() method."
        )


def validate_llm_event(event: LLMEvent, strict: bool = True) -> None:
    """
    验证 LLM 事件格式是否符合规范

    在开发/测试环境中启用，生产环境可设置 strict=False

    Args:
        event: LLM 事件字典
        strict: 是否启用严格模式（抛出异常 vs 警告）

    Raises:
        ValueError: 如果事件格式不正确且 strict=True
        Warning: 如果事件格式不正确且 strict=False

    Example::

        from loom.interfaces.llm import validate_llm_event

        # 开发环境 - 严格模式
        async for event in llm.stream(messages):
            validate_llm_event(event, strict=True)
            process_event(event)

        # 生产环境 - 宽松模式
        async for event in llm.stream(messages):
            validate_llm_event(event, strict=False)
            process_event(event)
    """
    import warnings

    def report_error(message: str) -> None:
        if strict:
            raise ValueError(message)
        else:
            warnings.warn(message, UserWarning, stacklevel=3)

    # 检查基本结构
    if not isinstance(event, dict):
        report_error(f"LLMEvent must be a dict, got {type(event)}")
        return

    event_type = event.get("type")
    if not event_type:
        report_error("LLMEvent must have 'type' field")
        return

    # 验证 content_delta 事件
    if event_type == "content_delta":
        if "content" not in event:
            report_error("content_delta event must have 'content' field")
            return

        content = event["content"]
        if not isinstance(content, str):
            report_error(
                f"content_delta.content must be str, got {type(content).__name__}. "
                f"Event: {event}"
            )

    # 验证 tool_calls 事件
    elif event_type == "tool_calls":
        if "tool_calls" not in event:
            report_error("tool_calls event must have 'tool_calls' field")
            return

        tool_calls = event["tool_calls"]
        if not isinstance(tool_calls, list):
            report_error(
                f"tool_calls must be a list, got {type(tool_calls).__name__}. "
                f"Event: {event}"
            )
            return

        # 验证每个 tool call 的格式
        for i, tc in enumerate(tool_calls):
            if not isinstance(tc, dict):
                report_error(
                    f"tool_calls[{i}] must be a dict, got {type(tc).__name__}. "
                    f"Event: {event}"
                )
                continue

            # 检查必需字段
            required_fields = {'id', 'name', 'arguments'}
            missing_fields = required_fields - tc.keys()
            if missing_fields:
                report_error(
                    f"tool_calls[{i}] missing required fields: {missing_fields}. "
                    f"Expected: {required_fields}, Got: {tc.keys()}. "
                    f"Tool call: {tc}"
                )

            # 验证 arguments 类型
            if 'arguments' in tc and not isinstance(tc['arguments'], dict):
                report_error(
                    f"tool_calls[{i}].arguments must be dict, got {type(tc['arguments']).__name__}. "
                    f"Tool call: {tc}"
                )

    # 验证 finish 事件
    elif event_type == "finish":
        if "finish_reason" not in event:
            report_error("finish event must have 'finish_reason' field")
            return

        finish_reason = event["finish_reason"]
        if not isinstance(finish_reason, str):
            report_error(
                f"finish_reason must be str, got {type(finish_reason).__name__}. "
                f"Event: {event}"
            )

        # 可选：验证 finish_reason 的值
        valid_reasons = {'stop', 'length', 'tool_calls', 'content_filter', 'function_call'}
        if strict and finish_reason not in valid_reasons:
            warnings.warn(
                f"Uncommon finish_reason: '{finish_reason}'. "
                f"Common values: {valid_reasons}",
                UserWarning,
                stacklevel=3
            )

    # 未知事件类型
    else:
        report_error(
            f"Unknown event type: '{event_type}'. "
            f"Valid types: content_delta, tool_calls, finish. "
            f"Event: {event}"
        )

