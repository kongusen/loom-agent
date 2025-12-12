"""
通用流式响应累积器 - 适用于所有 LLM 提供商

解决问题:
- 处理混合类型内容（字符串 + 字典）
- 增量累积 tool_calls
- 延迟 JSON 解析
- 提供商无关的通用接口

使用示例:
    # 方式1: 通用接口（推荐）
    accumulator = StreamAccumulator(mode='auto')
    accumulator.add_content("Hello ")
    accumulator.add_content("world")
    accumulator.add_tool_call(0, {"id": "call_1", "function": {"name": "search", "arguments": "{..."}})

    content = accumulator.get_content()  # "Hello world"
    tool_calls = accumulator.get_tool_calls()  # [{"id": "call_1", ...}]

    # 方式2: OpenAI 特定（兼容旧代码）
    accumulator = OpenAIStreamAccumulator()
    for chunk in openai_stream:
        accumulator.add(chunk)
    result = accumulator.get_result()
"""

import json
from typing import Any, Dict, List, Optional, Union
from collections import defaultdict


class StreamAccumulator:
    """
    通用流式响应累积器 - LLM 提供商无关

    特性:
    - 自动处理混合类型（字符串、字典）
    - 增量累积 tool calls
    - 智能 JSON 检测和解析
    - 零依赖于特定 LLM SDK

    使用场景:
    - OpenAI streaming
    - Anthropic streaming
    - 自定义 LLM 实现
    """

    def __init__(self, mode: str = 'auto'):
        """
        Args:
            mode: 'auto' | 'text' | 'json' | 'tool'
                - auto: 自动检测（推荐）
                - text: 强制文本模式
                - json: 强制 JSON 解析
                - tool: 处理 function/tool calls
        """
        self.mode = mode

        # 内容累积
        self.content_parts: List[str] = []

        # Tool calls 累积（支持多个并行的 tool calls）
        # 格式: {index: {'id': '', 'type': '', 'function': {'name': '', 'arguments': ''}}}
        self.tool_calls: Dict[int, Dict[str, Any]] = defaultdict(
            lambda: {'id': '', 'type': 'function', 'function': {'name': '', 'arguments': ''}}
        )

        # 元数据
        self.finish_reason: Optional[str] = None
        self.detected_json = False

    def add_content(self, content: Any) -> None:
        """
        添加内容（自动处理字符串/字典）

        Args:
            content: 可以是 str, dict, 或其他可序列化类型
        """
        if isinstance(content, str):
            self.content_parts.append(content)
        elif isinstance(content, dict):
            self.content_parts.append(json.dumps(content))
            self.detected_json = True
        elif content is not None:
            # 其他类型转为字符串
            self.content_parts.append(str(content))

    def add_tool_call(self, index: int, tool_call: Dict[str, Any]) -> None:
        """
        增量添加 tool call

        Args:
            index: Tool call 索引（支持并行多个 tool calls）
            tool_call: Tool call 字典，可包含:
                - id: str
                - type: str (默认 'function')
                - function: dict with 'name' and 'arguments'

        Example:
            # 分多次添加
            acc.add_tool_call(0, {"id": "call_1"})
            acc.add_tool_call(0, {"function": {"name": "search"}})
            acc.add_tool_call(0, {"function": {"arguments": '{"q"'}})
            acc.add_tool_call(0, {"function": {"arguments": ':"hello"}'}})
        """
        tc = self.tool_calls[index]

        # 累积 id
        if tool_call.get('id'):
            tc['id'] = tool_call['id']

        # 累积 type
        if tool_call.get('type'):
            tc['type'] = tool_call['type']

        # 累积 function
        if tool_call.get('function'):
            func = tool_call['function']

            # 累积 name
            if func.get('name'):
                tc['function']['name'] = func['name']

            # 累积 arguments（增量拼接）
            if func.get('arguments'):
                args = func['arguments']
                # 如果是字典，序列化为字符串
                if isinstance(args, dict):
                    args = json.dumps(args)
                tc['function']['arguments'] += args

    def set_finish_reason(self, reason: str) -> None:
        """设置完成原因"""
        self.finish_reason = reason

    def get_content(self) -> Union[str, Dict, None]:
        """
        获取累积的内容（自动解析 JSON）

        Returns:
            - str: 纯文本模式
            - dict: JSON 模式（自动解析）
            - None: 无内容
        """
        if not self.content_parts:
            return None

        # 拼接所有部分
        full_content = ''.join(self.content_parts)

        # 根据模式决定是否解析 JSON
        should_parse_json = (
            self.mode == 'json' or
            (self.mode == 'auto' and self.detected_json) or
            (self.mode == 'auto' and self._looks_like_json(full_content))
        )

        if should_parse_json:
            try:
                return json.loads(full_content)
            except json.JSONDecodeError:
                # JSON 解析失败，返回原始字符串
                return full_content

        return full_content

    def get_tool_calls(self) -> List[Dict[str, Any]]:
        """
        获取累积的 tool calls（自动解析参数）

        Returns:
            List of tool calls:
            [
                {
                    'id': str,
                    'name': str,
                    'arguments': dict  # 已解析的 JSON
                },
                ...
            ]
        """
        if not self.tool_calls:
            return []

        result = []
        for idx in sorted(self.tool_calls.keys()):
            tc = self.tool_calls[idx]

            # 解析 arguments JSON
            try:
                arguments = json.loads(tc['function']['arguments']) if tc['function']['arguments'] else {}
            except json.JSONDecodeError:
                # 如果解析失败，保留原始字符串（兜底）
                arguments = tc['function']['arguments']

            # 构造简化的 tool call 格式
            result.append({
                'id': tc['id'],
                'name': tc['function']['name'],
                'arguments': arguments
            })

        return result

    def has_content(self) -> bool:
        """是否有内容"""
        return bool(self.content_parts)

    def has_tool_calls(self) -> bool:
        """是否有 tool calls"""
        return bool(self.tool_calls)

    @staticmethod
    def _looks_like_json(text: str) -> bool:
        """启发式判断是否像 JSON"""
        if not text:
            return False

        text = text.strip()
        return (
            (text.startswith('{') and text.endswith('}')) or
            (text.startswith('[') and text.endswith(']'))
        )


class OpenAIStreamAccumulator(StreamAccumulator):
    """
    OpenAI 特定的流式累积器（兼容旧代码）

    在 StreamAccumulator 基础上，添加了直接处理 OpenAI chunk 的能力
    """

    def __init__(self, mode: str = 'auto'):
        super().__init__(mode)
        self.role: Optional[str] = None

    def add(self, chunk) -> None:
        """
        添加 OpenAI 流式 chunk（兼容旧接口）

        Args:
            chunk: OpenAI ChatCompletion chunk 对象
        """
        if not hasattr(chunk, 'choices') or not chunk.choices:
            return

        choice = chunk.choices[0]
        delta = choice.delta

        # 提取 role（通常只在第一个 chunk）
        if hasattr(delta, 'role') and delta.role:
            self.role = delta.role

        # 提取 finish_reason（最后一个 chunk）
        if hasattr(choice, 'finish_reason') and choice.finish_reason:
            self.set_finish_reason(choice.finish_reason)

        # 处理普通内容
        if hasattr(delta, 'content') and delta.content is not None:
            self.add_content(delta.content)

        # 处理 tool calls
        if hasattr(delta, 'tool_calls') and delta.tool_calls:
            for tc in delta.tool_calls:
                idx = tc.index

                tool_call_dict = {}

                # 提取 id
                if hasattr(tc, 'id') and tc.id:
                    tool_call_dict['id'] = tc.id

                # 提取 type
                if hasattr(tc, 'type') and tc.type:
                    tool_call_dict['type'] = tc.type

                # 提取 function
                if hasattr(tc, 'function') and tc.function:
                    function_dict = {}
                    if hasattr(tc.function, 'name') and tc.function.name:
                        function_dict['name'] = tc.function.name
                    if hasattr(tc.function, 'arguments') and tc.function.arguments:
                        function_dict['arguments'] = tc.function.arguments

                    if function_dict:
                        tool_call_dict['function'] = function_dict

                # 添加到累积器
                if tool_call_dict:
                    self.add_tool_call(idx, tool_call_dict)

    def get_result(self) -> Dict[str, Any]:
        """
        获取完整结果（兼容旧接口）

        Returns:
            {
                'content': str | dict | None,
                'tool_calls': list | None,
                'role': str | None,
                'finish_reason': str | None
            }
        """
        result = {
            'role': self.role,
            'content': self.get_content(),
            'finish_reason': self.finish_reason
        }

        # 只在有 tool calls 时添加
        tool_calls = self.get_tool_calls()
        if tool_calls:
            result['tool_calls'] = tool_calls

        return result


# ============================================================================
# 工具函数
# ============================================================================

def safe_string_concat(parts: List[Any]) -> str:
    """
    安全地连接可能包含混合类型的列表

    Args:
        parts: 可能包含 str, dict, bytes 等类型的列表

    Returns:
        连接后的字符串
    """
    result = []
    for part in parts:
        if isinstance(part, str):
            result.append(part)
        elif isinstance(part, dict):
            result.append(json.dumps(part))
        elif isinstance(part, bytes):
            result.append(part.decode('utf-8', errors='replace'))
        elif part is not None:
            result.append(str(part))

    return ''.join(result)


def is_json_content(content: Any) -> bool:
    """
    判断内容是否为 JSON 格式

    Args:
        content: 要检查的内容

    Returns:
        是否为 JSON
    """
    if isinstance(content, (dict, list)):
        return True

    if isinstance(content, str):
        content = content.strip()
        if (content.startswith('{') and content.endswith('}')) or \
           (content.startswith('[') and content.endswith(']')):
            try:
                json.loads(content)
                return True
            except json.JSONDecodeError:
                pass

    return False
