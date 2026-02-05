"""
Output Collector - 输出收集器

基于公理A2（事件主权）和A3（分形自相似）：
提供统一的事件到SSE流转换能力，支持多种输出策略。

设计原则：
1. 策略化 - 支持实时流式、阶段总结、最终合成
2. 标准化 - SSEEvent 提供统一的事件格式
3. 非侵入 - 通过EventBus通配符订阅，不修改现有流程
"""

import asyncio
import json
import time
from collections import defaultdict
from collections.abc import AsyncIterator
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

from loom.protocol.task import Task

if TYPE_CHECKING:
    from loom.events.event_bus import EventBus


class OutputStrategy(Enum):
    """输出策略枚举"""

    REALTIME = "realtime"  # 实时流式输出每个事件
    STAGE_SUMMARY = "stage_summary"  # 每阶段完成时发送总结
    FINAL_SYNTHESIS = "final_synthesis"  # 全部完成后合成输出
    HIERARCHICAL = "hierarchical"  # 分层汇聚（按深度合成）


@dataclass
class SSEEvent:
    """
    标准化的SSE事件

    统一了多Agent并行场景下的事件格式，
    便于前端解析和展示。
    """

    type: str  # thinking | tool_call | tool_result | stage_complete | final_summary | error
    task_id: str  # 任务/chunk的唯一标识
    agent_id: str  # 发出事件的Agent标识（结构化格式：{task_id}:{role}）
    data: str  # 事件内容
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(asdict(self), ensure_ascii=False, default=str)

    def to_sse(self) -> str:
        """转换为SSE格式字符串"""
        return f"data: {self.to_json()}\n\n"


@dataclass
class StageResult:
    """阶段执行结果"""

    stage_name: str
    task_id: str
    success: bool
    content: str
    duration: float
    error: str | None = None


class OutputCollector:
    """
    输出收集器

    将EventBus的事件转换为SSE流，支持多种输出策略。

    使用方式：
    1. 创建收集器并关联到EventBus
    2. 调用 stream() 获取SSE流
    3. 在请求处理完成后调用 close()
    """

    def __init__(
        self,
        event_bus: "EventBus",
        strategy: OutputStrategy = OutputStrategy.REALTIME,
        stage_separator: str = ":",  # task_id:stage_name 的分隔符
    ):
        """
        初始化输出收集器

        Args:
            event_bus: 要监听的事件总线
            strategy: 输出策略
            stage_separator: 阶段分隔符（用于从agent_id解析stage）
        """
        self.event_bus = event_bus
        self.strategy = strategy
        self.stage_separator = stage_separator
        self._queue: asyncio.Queue[SSEEvent | None] = asyncio.Queue()
        self._stage_buffers: dict[str, list[SSEEvent]] = defaultdict(list)
        self._closed = False
        self._registered = False

    def start(self) -> None:
        """注册事件处理器，开始收集事件"""
        if self._registered:
            return

        # 注册通配符处理器监听所有事件
        self.event_bus.register_handler("*", self._handle_event)
        self._registered = True

    async def _handle_event(self, task: Task) -> Task:
        """
        处理并路由事件

        根据策略决定是立即输出还是缓冲后合成。

        Args:
            task: 事件任务

        Returns:
            原始任务（不修改）
        """
        sse_event = self._convert_task_to_sse(task)

        if self.strategy == OutputStrategy.REALTIME:
            # 实时输出
            await self._queue.put(sse_event)

        elif self.strategy == OutputStrategy.STAGE_SUMMARY:
            # 缓冲同一阶段的事件
            stage_key = self._extract_stage_key(task)
            self._stage_buffers[stage_key].append(sse_event)

            # 阶段完成时发送总结
            if task.action in ("node.complete", "node.error"):
                summary = self._create_stage_summary(stage_key)
                await self._queue.put(summary)
                # 清理缓冲
                self._stage_buffers.pop(stage_key, None)

        elif self.strategy == OutputStrategy.FINAL_SYNTHESIS:
            # 只缓冲，不立即输出
            stage_key = self._extract_stage_key(task)
            self._stage_buffers[stage_key].append(sse_event)

        elif self.strategy == OutputStrategy.HIERARCHICAL:
            # 分层策略：根据深度决定
            depth = task.metadata.get("_depth", 0)
            if depth <= 1:
                await self._queue.put(sse_event)
            else:
                # 深层事件缓冲
                stage_key = self._extract_stage_key(task)
                self._stage_buffers[stage_key].append(sse_event)

        return task

    def _convert_task_to_sse(self, task: Task) -> SSEEvent:
        """
        将Task转换为SSEEvent

        Args:
            task: 事件任务

        Returns:
            SSEEvent实例
        """
        # 确定事件类型
        action_to_type = {
            "node.thinking": "thinking",
            "node.tool_call": "tool_call",
            "node.tool_result": "tool_result",
            "node.complete": "complete",
            "node.error": "error",
            "node.start": "start",
        }
        event_type = action_to_type.get(task.action, task.action)

        # 提取agent_id（优先使用source_agent，fallback到parameters）
        agent_id = task.source_agent or task.parameters.get("node_id", "unknown")

        # 提取task_id（从agent_id解析或使用parent_task_id）
        task_id = task.parameters.get("parent_task_id", task.task_id)
        if self.stage_separator in agent_id:
            task_id = agent_id.split(self.stage_separator)[0]

        # 提取内容
        content = task.parameters.get("content", "")
        if not content and task.result:
            content = str(task.result) if not isinstance(task.result, dict) else task.result.get("content", "")

        # 提取工具调用
        tool_calls = []
        if task.action == "node.tool_call":
            tool_calls.append({
                "function": {
                    "name": task.parameters.get("tool_name", ""),
                    "arguments": json.dumps(
                        task.parameters.get("tool_args", {}),
                        ensure_ascii=False,
                        default=str,
                    ),
                },
                "type": "function",
            })

        return SSEEvent(
            type=event_type,
            task_id=task_id,
            agent_id=agent_id,
            data=content,
            tool_calls=tool_calls,
            metadata={
                "action": task.action,
                "status": task.status.value if task.status else None,
            },
        )

    def _extract_stage_key(self, task: Task) -> str:
        """
        从任务中提取阶段键

        格式：{task_id}:{stage_name}

        Args:
            task: 事件任务

        Returns:
            阶段键字符串
        """
        agent_id = task.source_agent or task.parameters.get("node_id", "unknown")
        return agent_id

    def _create_stage_summary(self, stage_key: str) -> SSEEvent:
        """
        创建阶段总结事件

        Args:
            stage_key: 阶段键

        Returns:
            总结SSEEvent
        """
        events = self._stage_buffers.get(stage_key, [])

        # 合并所有thinking内容
        thinking_content = []
        tool_calls = []
        has_error = False
        error_msg = ""

        for event in events:
            if event.type == "thinking" and event.data:
                thinking_content.append(event.data)
            if event.tool_calls:
                tool_calls.extend(event.tool_calls)
            if event.type == "error":
                has_error = True
                error_msg = event.data

        # 提取task_id和stage_name
        parts = stage_key.split(self.stage_separator)
        task_id = parts[0] if parts else stage_key
        stage_name = parts[-1] if len(parts) > 1 else "unknown"

        summary_data = "".join(thinking_content)
        if len(summary_data) > 500:
            summary_data = summary_data[:500] + "..."

        return SSEEvent(
            type="stage_complete" if not has_error else "stage_error",
            task_id=task_id,
            agent_id=stage_key,
            data=summary_data if not has_error else error_msg,
            tool_calls=tool_calls,
            metadata={
                "stage": stage_name,
                "event_count": len(events),
                "has_error": has_error,
            },
        )

    async def emit_final_synthesis(self, synthesized_content: str) -> None:
        """
        发送最终合成结果

        适用于 FINAL_SYNTHESIS 策略，在所有处理完成后调用。

        Args:
            synthesized_content: 合成后的内容
        """
        await self._queue.put(SSEEvent(
            type="final_summary",
            task_id="all",
            agent_id="synthesizer",
            data=synthesized_content,
            metadata={"stage_count": len(self._stage_buffers)},
        ))

    async def close(self) -> None:
        """关闭收集器，注销 handler 并发送结束信号"""
        # 注销 handler 防止内存泄漏
        if self._registered:
            self.event_bus.unregister_handler("*", self._handle_event)
            self._registered = False
        self._closed = True
        await self._queue.put(None)

    async def stream(self, timeout: float = 30.0) -> AsyncIterator[str]:
        """
        生成SSE流

        Args:
            timeout: 等待超时时间（秒），超时发送心跳

        Yields:
            SSE格式字符串
        """
        while not self._closed:
            try:
                event = await asyncio.wait_for(self._queue.get(), timeout=timeout)
                if event is None:
                    # 结束信号
                    break
                yield event.to_sse()
            except TimeoutError:
                # 发送心跳
                yield ": heartbeat\n\n"
            except Exception as e:
                # 发送错误事件
                error_event = SSEEvent(
                    type="error",
                    task_id="system",
                    agent_id="output_collector",
                    data=str(e),
                )
                yield error_event.to_sse()
                break

    def get_buffered_events(self, stage_key: str | None = None) -> list[SSEEvent]:
        """
        获取缓冲的事件（用于调试或自定义合成）

        Args:
            stage_key: 可选的阶段键，不指定则返回所有

        Returns:
            事件列表
        """
        if stage_key:
            return list(self._stage_buffers.get(stage_key, []))
        return [event for events in self._stage_buffers.values() for event in events]
