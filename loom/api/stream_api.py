"""
Stream API - 分形架构流式观测API

基于公理A2（事件主权）和A3（分形自相似）：
提供HTTP/SSE接口供前端订阅多层级节点事件。

分形流式输出设计：
1. 事件冒泡 - 子节点事件自动向上传播到根EventBus
2. 节点路径 - 每个事件携带完整的节点路径（如 root/worker-1/subtask-2）
3. 输出策略 - 支持实时流、按节点分组、树形结构输出

API端点：
- GET /stream/events - 订阅所有节点事件（实时流）
- GET /stream/nodes/{node_id} - 订阅特定节点及其子节点事件
- GET /stream/tree - 订阅树形结构事件（带层级信息）
- GET /stream/thinking - 订阅所有思考过程事件
- GET /stream/tools - 订阅所有工具调用事件
"""

import asyncio
import json
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from loom.events import EventBus
from loom.events.sse_formatter import SSEFormatter
from loom.runtime import Task


class OutputStrategy(Enum):
    """流式输出策略"""
    REALTIME = "realtime"      # 实时输出所有事件
    BY_NODE = "by_node"        # 按节点分组输出
    TREE = "tree"              # 树形结构输出（带缩进）


@dataclass
class FractalEvent:
    """分形事件 - 携带层级信息的事件"""
    task: Task
    node_path: str              # 节点路径（如 root/worker-1/subtask-2）
    depth: int                  # 节点深度（0=根节点）
    parent_node_id: str | None  # 父节点ID
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "task_id": self.task.taskId,
            "action": self.task.action,
            "node_id": self.task.parameters.get("node_id", ""),
            "node_path": self.node_path,
            "depth": self.depth,
            "parent_node_id": self.parent_node_id,
            "parameters": self.task.parameters,
            "status": self.task.status.value,
            "metadata": self.metadata,
        }


class FractalStreamAPI:
    """
    分形流式观测API

    支持多层级节点的事件订阅和流式输出。
    """

    def __init__(self, event_bus: EventBus):
        """
        初始化API

        Args:
            event_bus: 根事件总线（所有子节点事件会冒泡到此）
        """
        self.event_bus = event_bus
        self._node_registry: dict[str, str] = {}  # node_id -> parent_node_id

    def register_node(self, node_id: str, parent_node_id: str | None = None) -> None:
        """
        注册节点层级关系

        Args:
            node_id: 节点ID
            parent_node_id: 父节点ID
        """
        self._node_registry[node_id] = parent_node_id or ""

    def get_node_path(self, node_id: str) -> str:
        """
        获取节点的完整路径

        Args:
            node_id: 节点ID

        Returns:
            节点路径（如 root/worker-1/subtask-2）
        """
        path_parts = [node_id]
        current = node_id

        while current in self._node_registry and self._node_registry[current]:
            parent = self._node_registry[current]
            path_parts.insert(0, parent)
            current = parent

        return "/".join(path_parts)

    def get_node_depth(self, node_id: str) -> int:
        """
        获取节点深度

        Args:
            node_id: 节点ID

        Returns:
            节点深度（0=根节点）
        """
        depth = 0
        current = node_id

        while current in self._node_registry and self._node_registry[current]:
            depth += 1
            current = self._node_registry[current]

        return depth

    async def stream_all_events(
        self,
        strategy: OutputStrategy = OutputStrategy.REALTIME,
    ) -> AsyncIterator[str]:
        """
        订阅所有节点事件

        Args:
            strategy: 输出策略

        Yields:
            SSE格式的事件流
        """
        queue: asyncio.Queue[Task] = asyncio.Queue()

        async def handler(task: Task) -> Task:
            await queue.put(task)
            return task

        # 注册所有节点事件
        self.event_bus.register_handler("node.thinking", handler)
        self.event_bus.register_handler("node.tool_call", handler)
        self.event_bus.register_handler("node.tool_result", handler)

        try:
            yield self._format_connected_event(strategy)

            while True:
                try:
                    task = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield self._format_fractal_event(task, strategy)
                except TimeoutError:
                    yield self._format_heartbeat()

        except asyncio.CancelledError:
            yield self._format_disconnected_event()
        finally:
            self.event_bus.unregister_handler("node.thinking", handler)
            self.event_bus.unregister_handler("node.tool_call", handler)
            self.event_bus.unregister_handler("node.tool_result", handler)

    async def stream_node_events(
        self,
        node_id: str,
        include_children: bool = True,
    ) -> AsyncIterator[str]:
        """
        订阅特定节点及其子节点的事件

        Args:
            node_id: 节点ID
            include_children: 是否包含子节点事件

        Yields:
            SSE格式的事件流
        """
        queue: asyncio.Queue[Task] = asyncio.Queue()

        async def handler(task: Task) -> Task:
            event_node_id = task.parameters.get("node_id", "")

            # 检查是否是目标节点或其子节点
            if event_node_id == node_id:
                await queue.put(task)
            elif include_children:
                node_path = self.get_node_path(event_node_id)
                if node_id in node_path.split("/"):
                    await queue.put(task)

            return task

        self.event_bus.register_handler("node.thinking", handler)
        self.event_bus.register_handler("node.tool_call", handler)
        self.event_bus.register_handler("node.tool_result", handler)

        try:
            yield self._format_connected_event(
                OutputStrategy.REALTIME,
                {"node_id": node_id, "include_children": include_children}
            )

            while True:
                try:
                    task = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield self._format_fractal_event(task, OutputStrategy.REALTIME)
                except TimeoutError:
                    yield self._format_heartbeat()

        except asyncio.CancelledError:
            yield self._format_disconnected_event()
        finally:
            self.event_bus.unregister_handler("node.thinking", handler)
            self.event_bus.unregister_handler("node.tool_call", handler)
            self.event_bus.unregister_handler("node.tool_result", handler)

    async def stream_thinking_events(
        self,
        node_id: str | None = None,
    ) -> AsyncIterator[str]:
        """
        订阅思考过程事件

        Args:
            node_id: 可选的节点ID过滤

        Yields:
            SSE格式的事件流
        """
        queue: asyncio.Queue[Task] = asyncio.Queue()

        async def handler(task: Task) -> Task:
            if node_id is None or task.parameters.get("node_id") == node_id:
                await queue.put(task)
            return task

        self.event_bus.register_handler("node.thinking", handler)

        try:
            yield self._format_connected_event(OutputStrategy.REALTIME)

            while True:
                try:
                    task = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield self._format_fractal_event(task, OutputStrategy.REALTIME)
                except TimeoutError:
                    yield self._format_heartbeat()

        except asyncio.CancelledError:
            yield self._format_disconnected_event()
        finally:
            self.event_bus.unregister_handler("node.thinking", handler)

    async def stream_tool_events(
        self,
        node_id: str | None = None,
    ) -> AsyncIterator[str]:
        """
        订阅工具调用事件（包括调用和结果）

        Args:
            node_id: 可选的节点ID过滤

        Yields:
            SSE格式的事件流
        """
        queue: asyncio.Queue[Task] = asyncio.Queue()

        async def handler(task: Task) -> Task:
            if node_id is None or task.parameters.get("node_id") == node_id:
                await queue.put(task)
            return task

        self.event_bus.register_handler("node.tool_call", handler)
        self.event_bus.register_handler("node.tool_result", handler)

        try:
            yield self._format_connected_event(OutputStrategy.REALTIME)

            while True:
                try:
                    task = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield self._format_fractal_event(task, OutputStrategy.REALTIME)
                except TimeoutError:
                    yield self._format_heartbeat()

        except asyncio.CancelledError:
            yield self._format_disconnected_event()
        finally:
            self.event_bus.unregister_handler("node.tool_call", handler)
            self.event_bus.unregister_handler("node.tool_result", handler)

    def _format_fractal_event(
        self,
        task: Task,
        strategy: OutputStrategy,
    ) -> str:
        """格式化分形事件为SSE"""
        node_id = task.parameters.get("node_id", "unknown")
        node_path = self.get_node_path(node_id)
        depth = self.get_node_depth(node_id)
        parent_id = self._node_registry.get(node_id)

        fractal_event = FractalEvent(
            task=task,
            node_path=node_path,
            depth=depth,
            parent_node_id=parent_id,
        )

        # 根据策略格式化
        if strategy == OutputStrategy.TREE:
            # 树形输出：添加缩进
            indent = "  " * depth
            content = task.parameters.get("content", "")[:50]
            data = {
                **fractal_event.to_dict(),
                "display": f"{indent}[{node_id}] {content}...",
            }
        else:
            data = fractal_event.to_dict()

        return SSEFormatter.format_sse_message(
            event_type=task.action,
            data=json.dumps(data, ensure_ascii=False),
            event_id=task.taskId,
        )

    def _format_connected_event(
        self,
        strategy: OutputStrategy,
        extra: dict[str, Any] | None = None,
    ) -> str:
        """格式化连接成功事件"""
        data = {
            "status": "connected",
            "strategy": strategy.value,
            **(extra or {}),
        }
        return SSEFormatter.format_sse_message(
            event_type="connected",
            data=json.dumps(data),
        )

    def _format_disconnected_event(self) -> str:
        """格式化断开连接事件"""
        return SSEFormatter.format_sse_message(
            event_type="disconnected",
            data=json.dumps({"status": "disconnected"}),
        )

    def _format_heartbeat(self) -> str:
        """格式化心跳事件"""
        return SSEFormatter.format_sse_message(
            event_type="heartbeat",
            data=json.dumps({"timestamp": asyncio.get_event_loop().time()}),
        )


# 保留原有的StreamAPI作为简化版本
class StreamAPI:
    """
    流式观测API（简化版）

    提供HTTP/SSE端点供前端订阅节点事件。
    """

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self._fractal_api = FractalStreamAPI(event_bus)

    async def stream_node_events(self, node_id: str):
        """订阅特定节点的所有事件"""
        async for event in self._fractal_api.stream_node_events(node_id):
            yield event

    async def stream_thinking_events(self, node_id: str | None = None):
        """订阅思考过程事件"""
        async for event in self._fractal_api.stream_thinking_events(node_id):
            yield event

    async def stream_all_events(self, action_pattern: str = "node.*"):
        """订阅所有节点事件"""
        async for event in self._fractal_api.stream_all_events():
            yield event
