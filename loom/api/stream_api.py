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
import time
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from loom.events import EventBus
from loom.events.sse_formatter import SSEFormatter
from loom.runtime import Task


class OutputStrategy(Enum):
    """流式输出策略"""

    REALTIME = "realtime"  # 实时输出所有事件
    BY_NODE = "by_node"  # 按节点分组输出
    TREE = "tree"  # 树形结构输出（带缩进）


@dataclass
class FractalEvent:
    """分形事件 - 携带层级信息的事件"""

    task: Task
    node_path: str  # 节点路径（如 root/worker-1/subtask-2）
    depth: int  # 节点深度（0=根节点）
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


# 事件过滤器类型：接收 Task，返回是否放入队列
EventFilter = Callable[[Task], bool]

# 常用事件类型组
_ALL_NODE_EVENTS = ("node.thinking", "node.tool_call", "node.tool_result")
_TOOL_EVENTS = ("node.tool_call", "node.tool_result")


class FractalStreamAPI:
    """
    分形流式观测API

    支持多层级节点的事件订阅和流式输出。
    """

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self._node_registry: dict[str, str] = {}  # node_id -> parent_node_id

    def register_node(self, node_id: str, parent_node_id: str | None = None) -> None:
        """注册节点层级关系"""
        self._node_registry[node_id] = parent_node_id or ""

    def resolve_node_info(self, node_id: str) -> tuple[str, int]:
        """
        获取节点的完整路径和深度（单次遍历）

        带环路保护，避免循环引用导致死循环。

        Returns:
            (node_path, depth) 元组
        """
        path_parts: list[str] = [node_id]
        current = node_id
        visited: set[str] = {node_id}

        while current in self._node_registry and self._node_registry[current]:
            parent = self._node_registry[current]
            if parent in visited:
                break  # 环路保护
            visited.add(parent)
            path_parts.append(parent)
            current = parent

        path_parts.reverse()
        return "/".join(path_parts), len(path_parts) - 1

    # ==================== 公开的流式端点 ====================

    async def stream_all_events(
        self,
        strategy: OutputStrategy = OutputStrategy.REALTIME,
    ) -> AsyncIterator[str]:
        """订阅所有节点事件"""
        async for event in self._stream_loop(
            event_types=_ALL_NODE_EVENTS,
            strategy=strategy,
        ):
            yield event

    async def stream_node_events(
        self,
        node_id: str,
        include_children: bool = True,
    ) -> AsyncIterator[str]:
        """订阅特定节点及其子节点的事件"""

        def node_filter(task: Task) -> bool:
            event_node_id = task.parameters.get("node_id", "")
            if event_node_id == node_id:
                return True
            if include_children:
                path, _ = self.resolve_node_info(event_node_id)
                return node_id in path.split("/")
            return False

        async for event in self._stream_loop(
            event_types=_ALL_NODE_EVENTS,
            strategy=OutputStrategy.REALTIME,
            event_filter=node_filter,
            connect_extra={"node_id": node_id, "include_children": include_children},
        ):
            yield event

    async def stream_thinking_events(
        self,
        node_id: str | None = None,
    ) -> AsyncIterator[str]:
        """订阅思考过程事件"""
        async for event in self._stream_loop(
            event_types=("node.thinking",),
            strategy=OutputStrategy.REALTIME,
            event_filter=self._make_node_filter(node_id),
        ):
            yield event

    async def stream_tool_events(
        self,
        node_id: str | None = None,
    ) -> AsyncIterator[str]:
        """订阅工具调用事件（包括调用和结果）"""
        async for event in self._stream_loop(
            event_types=_TOOL_EVENTS,
            strategy=OutputStrategy.REALTIME,
            event_filter=self._make_node_filter(node_id),
        ):
            yield event

    # ==================== 内部实现 ====================

    async def _stream_loop(
        self,
        event_types: tuple[str, ...],
        strategy: OutputStrategy = OutputStrategy.REALTIME,
        event_filter: EventFilter | None = None,
        connect_extra: dict[str, Any] | None = None,
    ) -> AsyncIterator[str]:
        """
        通用流式循环 — 所有 stream_* 方法的统一骨架

        Args:
            event_types: 要订阅的事件类型列表
            strategy: 输出策略
            event_filter: 可选的事件过滤器
            connect_extra: 连接事件的额外数据
        """
        queue: asyncio.Queue[Task] = asyncio.Queue()

        async def handler(task: Task) -> Task:
            if event_filter is None or event_filter(task):
                await queue.put(task)
            return task

        for et in event_types:
            self.event_bus.register_handler(et, handler)

        try:
            yield self._format_connected_event(strategy, connect_extra)

            while True:
                try:
                    task = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield self._format_fractal_event(task, strategy)
                except TimeoutError:
                    yield self._format_heartbeat()

        except asyncio.CancelledError:
            yield self._format_disconnected_event()
        finally:
            for et in event_types:
                self.event_bus.unregister_handler(et, handler)

    @staticmethod
    def _make_node_filter(node_id: str | None) -> EventFilter | None:
        """创建按 node_id 过滤的 filter（None 表示不过滤）"""
        if node_id is None:
            return None

        def _filter(task: Task) -> bool:
            return task.parameters.get("node_id") == node_id

        return _filter

    # ==================== 格式化 ====================

    def _format_fractal_event(self, task: Task, strategy: OutputStrategy) -> str:
        """格式化分形事件为SSE"""
        node_id = task.parameters.get("node_id", "unknown")
        node_path, depth = self.resolve_node_info(node_id)
        parent_id = self._node_registry.get(node_id)

        fractal_event = FractalEvent(
            task=task,
            node_path=node_path,
            depth=depth,
            parent_node_id=parent_id,
        )

        if strategy == OutputStrategy.TREE:
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
        data = {"status": "connected", "strategy": strategy.value, **(extra or {})}
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
            data=json.dumps({"timestamp": time.time()}),
        )


# StreamAPI 保留为 FractalStreamAPI 的别名（向后兼容）
StreamAPI = FractalStreamAPI
