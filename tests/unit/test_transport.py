"""
传输层测试

测试Transport抽象接口和各种传输层实现。
"""

import asyncio

import pytest

from loom.events.memory_transport import MemoryTransport


class TestMemoryTransport:
    """测试内存传输层"""

    @pytest.mark.asyncio
    async def test_connect_disconnect(self):
        """测试连接和断开"""
        transport = MemoryTransport()

        # 初始状态：未连接
        assert not transport.is_connected()

        # 连接
        await transport.connect()
        assert transport.is_connected()

        # 断开
        await transport.disconnect()
        assert not transport.is_connected()

    @pytest.mark.asyncio
    async def test_publish_subscribe(self):
        """测试发布和订阅"""
        transport = MemoryTransport()
        await transport.connect()

        # 用于收集接收到的消息
        received_messages = []

        async def handler(message: bytes):
            received_messages.append(message)

        # 订阅主题
        await transport.subscribe("test.topic", handler)

        # 发布消息
        test_message = b"Hello, World!"
        await transport.publish("test.topic", test_message)

        # 等待消息处理
        await asyncio.sleep(0.1)

        # 验证消息已接收
        assert len(received_messages) == 1
        assert received_messages[0] == test_message

        await transport.disconnect()

    @pytest.mark.asyncio
    async def test_multiple_subscribers(self):
        """测试多个订阅者"""
        transport = MemoryTransport()
        await transport.connect()

        received_1 = []
        received_2 = []

        async def handler1(message: bytes):
            received_1.append(message)

        async def handler2(message: bytes):
            received_2.append(message)

        # 两个订阅者订阅同一主题
        await transport.subscribe("test.topic", handler1)
        await transport.subscribe("test.topic", handler2)

        # 发布消息
        test_message = b"Test message"
        await transport.publish("test.topic", test_message)

        # 等待消息处理
        await asyncio.sleep(0.1)

        # 验证两个订阅者都收到消息
        assert len(received_1) == 1
        assert len(received_2) == 1
        assert received_1[0] == test_message
        assert received_2[0] == test_message

        await transport.disconnect()

    @pytest.mark.asyncio
    async def test_unsubscribe(self):
        """测试取消订阅"""
        transport = MemoryTransport()
        await transport.connect()

        received_messages = []

        async def handler(message: bytes):
            received_messages.append(message)

        # 订阅
        await transport.subscribe("test.topic", handler)

        # 发布第一条消息
        await transport.publish("test.topic", b"Message 1")
        await asyncio.sleep(0.1)

        # 取消订阅
        await transport.unsubscribe("test.topic")

        # 发布第二条消息
        await transport.publish("test.topic", b"Message 2")
        await asyncio.sleep(0.1)

        # 验证只收到第一条消息
        assert len(received_messages) == 1
        assert received_messages[0] == b"Message 1"

        await transport.disconnect()
