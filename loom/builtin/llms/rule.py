from __future__ import annotations

import asyncio
import re
from typing import AsyncGenerator, Dict, List

from loom.interfaces.llm import BaseLLM


class RuleLLM(BaseLLM):
    """规则驱动的演示 LLM：
    - 若用户消息包含 "calc:" 前缀，则产生 calculator 的工具调用。
    - 否则返回纯文本。
    """

    def __init__(self, model: str = "rule-llm") -> None:
        self._model_name = model

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def supports_tools(self) -> bool:
        return True

    async def generate(self, messages: List[Dict]) -> str:
        last = messages[-1]["content"] if messages else ""
        return f"Echo: {last}"

    async def stream(self, messages: List[Dict]) -> AsyncGenerator[str, None]:
        text = await self.generate(messages)
        for ch in text:
            await asyncio.sleep(0)
            yield ch

    async def generate_with_tools(self, messages: List[Dict], tools: List[Dict]) -> Dict:
        if not messages:
            return {"content": "", "tool_calls": []}

        last_msg = messages[-1]
        last_role = last_msg.get("role")
        last = last_msg.get("content", "")

        # 若上条是工具结果，直接返回总结，不再调用工具
        if last_role == "tool":
            return {"content": f"工具执行完成，输出: {last}", "tool_calls": []}

        # 简易规则：calc/read/write/glob/grep
        m = re.search(r"calc:\s*([0-9+\-*/. ()]+)", last, re.IGNORECASE)
        if m:
            expr = m.group(1).strip()
            return {
                "content": "我将使用 calculator 计算该表达式。",
                "tool_calls": [
                    {"id": "tool_1", "name": "calculator", "arguments": {"expression": expr}}
                ],
            }

        m = re.search(r"read:\s*(.+)$", last, re.IGNORECASE)
        if m:
            path = m.group(1).strip()
            return {
                "content": "我将读取指定文件。",
                "tool_calls": [{"id": "tool_1", "name": "read_file", "arguments": {"path": path}}],
            }

        m = re.search(r"write:\s*([^<]+)<<<(.*)$", last, re.IGNORECASE | re.DOTALL)
        if m:
            path = m.group(1).strip()
            content = m.group(2).strip()
            return {
                "content": "我将写入指定文件。",
                "tool_calls": [
                    {"id": "tool_1", "name": "write_file", "arguments": {"path": path, "content": content}}
                ],
            }

        m = re.search(r"glob:\s*(.+)$", last, re.IGNORECASE)
        if m:
            pattern = m.group(1).strip()
            return {
                "content": "我将搜索匹配的文件。",
                "tool_calls": [{"id": "tool_1", "name": "glob", "arguments": {"pattern": pattern}}],
            }

        m = re.search(r"grep:\s*(.+?)\s+in\s+(.+)$", last, re.IGNORECASE)
        if m:
            pattern = m.group(1).strip()
            target = m.group(2).strip()
            args = {"pattern": pattern}
            if target.startswith("glob:"):
                args["glob_pattern"] = target.split(":", 1)[1].strip()
            else:
                args["path"] = target
            return {
                "content": "我将检索文本匹配。",
                "tool_calls": [{"id": "tool_1", "name": "grep", "arguments": args}],
            }

        # 默认：无工具
        return {"content": await self.generate(messages), "tool_calls": []}
