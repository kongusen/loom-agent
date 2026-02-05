"""
OutputCollector Unit Tests

测试输出收集器功能
"""

import asyncio
import json
from unittest.mock import AsyncMock

import pytest

from loom.events import EventBus, OutputCollector, OutputStrategy, SSEEvent
from loom.protocol import Task, TaskStatus


class TestSSEEvent:
    """测试SSEEvent数据类"""

    def test_sse_event_creation(self):
        """测试创建SSEEvent"""
        event = SSEEvent(
            type="thinking",
            task_id="task1",
            agent_id="task1:Scanner",
            data="思考内容",
        )

        assert event.type == "thinking"
        assert event.task_id == "task1"
        assert event.agent_id == "task1:Scanner"
        assert event.data == "思考内容"
        assert event.tool_calls == []
        assert event.timestamp > 0

    def test_sse_event_to_json(self):
        """测试转换为JSON"""
        event = SSEEvent(
            type="tool_call",
            task_id="task1",
            agent_id="task1:Planner",
            data="",
            tool_calls=[{"function": {"name": "search", "arguments": "{}"}}],
        )

        json_str = event.to_json()
        parsed = json.loads(json_str)

        assert parsed["type"] == "tool_call"
        assert parsed["task_id"] == "task1"
        assert len(parsed["tool_calls"]) == 1

    def test_sse_event_to_sse(self):
        """测试转换为SSE格式"""
        event = SSEEvent(
            type="thinking",
            task_id="task1",
            agent_id="agent1",
            data="内容",
        )

        sse_str = event.to_sse()

        assert sse_str.startswith("data: ")
        assert sse_str.endswith("\n\n")
        assert "thinking" in sse_str


class TestOutputStrategy:
    """测试OutputStrategy枚举"""

    def test_strategy_values(self):
        """测试策略枚举值"""
        assert OutputStrategy.REALTIME.value == "realtime"
        assert OutputStrategy.STAGE_SUMMARY.value == "stage_summary"
        assert OutputStrategy.FINAL_SYNTHESIS.value == "final_synthesis"
        assert OutputStrategy.HIERARCHICAL.value == "hierarchical"


class TestOutputCollector:
    """测试OutputCollector"""

    @pytest.mark.asyncio
    async def test_collector_realtime_strategy(self):
        """测试实时策略"""
        bus = EventBus()
        collector = OutputCollector(bus, strategy=OutputStrategy.REALTIME)
        collector.start()

        # 发布事件
        task = Task(
            task_id="test_task",
            source_agent="chunk1:Scanner",
            action="node.thinking",
            parameters={"content": "正在思考..."},
            status=TaskStatus.PENDING,
        )
        await bus.publish(task)

        # 等待事件处理
        await asyncio.sleep(0.05)

        # 检查队列
        assert not collector._queue.empty()
        event = await collector._queue.get()
        assert event.type == "thinking"
        assert "chunk1" in event.agent_id

    @pytest.mark.asyncio
    async def test_collector_stage_summary_strategy(self):
        """测试阶段总结策略"""
        bus = EventBus()
        collector = OutputCollector(bus, strategy=OutputStrategy.STAGE_SUMMARY)
        collector.start()

        # 发布thinking事件
        thinking_task = Task(
            task_id="think1",
            source_agent="task1:Scanner",
            action="node.thinking",
            parameters={"content": "分析中..."},
        )
        await bus.publish(thinking_task)

        # 发布complete事件
        complete_task = Task(
            task_id="complete1",
            source_agent="task1:Scanner",
            action="node.complete",
            parameters={"result": "完成"},
        )
        await bus.publish(complete_task)

        await asyncio.sleep(0.05)

        # 应该只有一个stage_complete事件
        event = await collector._queue.get()
        assert event.type == "stage_complete"
        assert "task1:Scanner" in event.agent_id

    @pytest.mark.asyncio
    async def test_collector_close(self):
        """测试关闭收集器"""
        bus = EventBus()
        collector = OutputCollector(bus)
        collector.start()

        await collector.close()

        assert collector._closed is True
        event = await collector._queue.get()
        assert event is None

    @pytest.mark.asyncio
    async def test_collector_stream(self):
        """测试SSE流生成"""
        bus = EventBus()
        collector = OutputCollector(bus, strategy=OutputStrategy.REALTIME)
        collector.start()

        # 发布事件
        task = Task(
            task_id="stream_test",
            source_agent="agent1",
            action="node.thinking",
            parameters={"content": "测试"},
        )
        await bus.publish(task)

        # 关闭收集器
        async def close_after_delay():
            await asyncio.sleep(0.1)
            await collector.close()

        asyncio.create_task(close_after_delay())

        # 收集流输出
        outputs = []
        async for sse_str in collector.stream(timeout=0.5):
            outputs.append(sse_str)
            if len(outputs) >= 1:
                break

        assert len(outputs) >= 1
        assert "data:" in outputs[0]

    @pytest.mark.asyncio
    async def test_convert_task_to_sse(self):
        """测试Task转换为SSEEvent"""
        bus = EventBus()
        collector = OutputCollector(bus)

        task = Task(
            task_id="convert_test",
            source_agent="chunk1:Planner",
            action="node.tool_call",
            parameters={
                "tool_name": "search_kb",
                "tool_args": {"query": "测试"},
            },
        )

        event = collector._convert_task_to_sse(task)

        assert event.type == "tool_call"
        assert event.agent_id == "chunk1:Planner"
        assert len(event.tool_calls) == 1
        assert event.tool_calls[0]["function"]["name"] == "search_kb"

    def test_extract_stage_key(self):
        """测试提取阶段键"""
        bus = EventBus()
        collector = OutputCollector(bus)

        task = Task(
            task_id="test",
            source_agent="chunk5:Scanner",
            action="node.thinking",
        )

        stage_key = collector._extract_stage_key(task)
        assert stage_key == "chunk5:Scanner"

    def test_get_buffered_events(self):
        """测试获取缓冲事件"""
        bus = EventBus()
        collector = OutputCollector(bus, strategy=OutputStrategy.FINAL_SYNTHESIS)

        # 手动添加缓冲事件
        event = SSEEvent(type="thinking", task_id="t1", agent_id="a1", data="test")
        collector._stage_buffers["a1"].append(event)

        buffered = collector.get_buffered_events("a1")
        assert len(buffered) == 1
        assert buffered[0].data == "test"

    @pytest.mark.asyncio
    async def test_emit_final_synthesis(self):
        """测试发送最终合成"""
        bus = EventBus()
        collector = OutputCollector(bus, strategy=OutputStrategy.FINAL_SYNTHESIS)
        collector.start()

        await collector.emit_final_synthesis("合成的最终结果")

        event = await collector._queue.get()
        assert event.type == "final_summary"
        assert event.data == "合成的最终结果"
