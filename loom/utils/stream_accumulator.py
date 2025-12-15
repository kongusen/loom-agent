"""
Stream Accumulator - 流式响应累积器

用于累积流式 LLM 响应（特别是 OpenAI 格式）
"""

from __future__ import annotations
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field


@dataclass
class OpenAIStreamAccumulator:
    """
    OpenAI 流式响应累积器

    用于累积 OpenAI API 的流式响应，处理增量更新。
    """

    content: str = ""
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    role: str = "assistant"
    finish_reason: Optional[str] = None

    def update(self, chunk: Dict[str, Any]) -> None:
        """
        更新累积器状态

        Args:
            chunk: OpenAI 流式响应的增量块
        """
        if not chunk.get("choices"):
            return

        choice = chunk["choices"][0]
        delta = choice.get("delta", {})

        # 累积 content
        if "content" in delta and delta["content"]:
            self.content += delta["content"]

        # 累积 role
        if "role" in delta:
            self.role = delta["role"]

        # 累积 tool_calls
        if "tool_calls" in delta:
            for tc_delta in delta["tool_calls"]:
                index = tc_delta.get("index", 0)

                # 确保 tool_calls 列表足够长
                while len(self.tool_calls) <= index:
                    self.tool_calls.append({
                        "id": "",
                        "type": "function",
                        "function": {"name": "", "arguments": ""}
                    })

                # 更新对应位置的 tool call
                if "id" in tc_delta:
                    self.tool_calls[index]["id"] = tc_delta["id"]

                if "type" in tc_delta:
                    self.tool_calls[index]["type"] = tc_delta["type"]

                if "function" in tc_delta:
                    func_delta = tc_delta["function"]
                    if "name" in func_delta:
                        self.tool_calls[index]["function"]["name"] += func_delta["name"]
                    if "arguments" in func_delta:
                        self.tool_calls[index]["function"]["arguments"] += func_delta["arguments"]

        # 更新 finish_reason
        if "finish_reason" in choice and choice["finish_reason"]:
            self.finish_reason = choice["finish_reason"]

    def get_message(self) -> Dict[str, Any]:
        """
        获取累积的完整消息

        Returns:
            消息字典（OpenAI 格式）
        """
        message: Dict[str, Any] = {
            "role": self.role,
            "content": self.content,
        }

        if self.tool_calls:
            message["tool_calls"] = self.tool_calls

        return message

    def has_tool_calls(self) -> bool:
        """是否包含工具调用"""
        return len(self.tool_calls) > 0

    def reset(self) -> None:
        """重置累积器"""
        self.content = ""
        self.tool_calls = []
        self.role = "assistant"
        self.finish_reason = None


__all__ = [
    "OpenAIStreamAccumulator",
]
