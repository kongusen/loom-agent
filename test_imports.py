#!/usr/bin/env python
"""最小化导入测试"""
print("1. 开始导入...")

print("2. 导入 asyncio...")
import asyncio

print("3. 导入 os...")
import os

print("4. 导入 loom...")
from loom import LoomBuilder

print("5. 导入 OpenAIProvider...")
from loom.llm import OpenAIProvider

print("6. 导入 Dispatcher...")
from loom.kernel.core import UniversalEventBus, Dispatcher

print("7. 导入 CloudEvent...")
from loom.protocol.cloudevents import CloudEvent

print("8. 导入 ToolNode...")
from loom.node.tool import ToolNode

print("9. 导入 MCPToolDefinition...")
from loom.protocol.mcp import MCPToolDefinition

print("✅ 所有导入成功！")
