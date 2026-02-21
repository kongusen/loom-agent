"""Unit tests for events module."""

import pytest
from loom.events import EventBus
from loom.types import TextDeltaEvent, ErrorEvent, DoneEvent, TokenUsage


class TestEventBus:
    async def test_on_and_emit(self):
        bus = EventBus(node_id="test")
        received = []
        async def handler(e): received.append(e)
        bus.on("text_delta", handler)
        await bus.emit(TextDeltaEvent(text="hi"))
        assert len(received) == 1

    async def test_on_all(self):
        bus = EventBus()
        received = []
        async def handler(e): received.append(e)
        bus.on_all(handler)
        await bus.emit(TextDeltaEvent(text="a"))
        await bus.emit(ErrorEvent(error="b"))
        assert len(received) == 2

    async def test_off(self):
        bus = EventBus()
        received = []
        async def handler(e): received.append(e)
        bus.on("text_delta", handler)
        bus.off("text_delta", handler)
        await bus.emit(TextDeltaEvent(text="hi"))
        assert len(received) == 0

    async def test_parent_propagation(self):
        parent = EventBus(node_id="parent")
        child = parent.create_child("child")
        received = []
        async def handler(e): received.append(e)
        parent.on("text_delta", handler)
        await child.emit(TextDeltaEvent(text="from child"))
        assert len(received) == 1

    async def test_pattern_matching(self):
        bus = EventBus()
        received = []
        async def handler(e): received.append(e)
        bus.on_pattern("tool:*", handler)
        await bus.emit(TextDeltaEvent(text="no match"))
        assert len(received) == 0
