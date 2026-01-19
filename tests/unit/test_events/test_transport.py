"""
Tests for Transport Abstract Interface
"""


import pytest

from loom.events.transport import MessageHandler, Transport


class TestTransportABC:
    """Test suite for Transport abstract base class"""

    def test_transport_is_abstract(self):
        """Test Transport cannot be instantiated directly"""
        with pytest.raises(TypeError):
            Transport()

    def test_transport_subclass_implementing_all_methods(self):
        """Test creating a concrete Transport subclass"""

        class ConcreteTransport(Transport):
            async def connect(self) -> None:
                pass

            async def disconnect(self) -> None:
                pass

            async def publish(self, topic: str, message: bytes) -> None:
                pass

            async def subscribe(self, topic: str, handler: MessageHandler) -> None:
                pass

            async def unsubscribe(self, topic: str) -> None:
                pass

        # Should be able to instantiate
        transport = ConcreteTransport()
        assert transport is not None

    @pytest.mark.asyncio
    async def test_transport_connect(self):
        """Test connect method"""

        class ConcreteTransport(Transport):
            async def connect(self) -> None:
                self.connected = True

            async def disconnect(self) -> None:
                self.connected = False

            async def publish(self, topic: str, message: bytes) -> None:
                pass

            async def subscribe(self, topic: str, handler: MessageHandler) -> None:
                pass

            async def unsubscribe(self, topic: str) -> None:
                pass

        transport = ConcreteTransport()
        await transport.connect()

        assert transport.connected is True

    @pytest.mark.asyncio
    async def test_transport_disconnect(self):
        """Test disconnect method"""

        class ConcreteTransport(Transport):
            def __init__(self):
                self.disconnected = False

            async def connect(self) -> None:
                pass

            async def disconnect(self) -> None:
                self.disconnected = True

            async def publish(self, topic: str, message: bytes) -> None:
                pass

            async def subscribe(self, topic: str, handler: MessageHandler) -> None:
                pass

            async def unsubscribe(self, topic: str) -> None:
                pass

        transport = ConcreteTransport()
        await transport.disconnect()

        assert transport.disconnected is True

    @pytest.mark.asyncio
    async def test_transport_publish(self):
        """Test publish method"""

        published_messages = []

        class ConcreteTransport(Transport):
            async def connect(self) -> None:
                pass

            async def disconnect(self) -> None:
                pass

            async def publish(self, topic: str, message: bytes) -> None:
                published_messages.append((topic, message))

            async def subscribe(self, topic: str, handler: MessageHandler) -> None:
                pass

            async def unsubscribe(self, topic: str) -> None:
                pass

        transport = ConcreteTransport()
        await transport.publish("test_topic", b"test_message")

        assert published_messages == [("test_topic", b"test_message")]

    @pytest.mark.asyncio
    async def test_transport_subscribe(self):
        """Test subscribe method"""

        subscribed_handlers = []

        class ConcreteTransport(Transport):
            async def connect(self) -> None:
                pass

            async def disconnect(self) -> None:
                pass

            async def publish(self, topic: str, message: bytes) -> None:
                pass

            async def subscribe(self, topic: str, handler: MessageHandler) -> None:
                subscribed_handlers.append((topic, handler))

            async def unsubscribe(self, topic: str) -> None:
                pass

        transport = ConcreteTransport()

        async def handler(msg: bytes) -> None:
            pass

        await transport.subscribe("test_topic", handler)

        assert len(subscribed_handlers) == 1
        assert subscribed_handlers[0][0] == "test_topic"
        assert subscribed_handlers[0][1] is handler

    @pytest.mark.asyncio
    async def test_transport_unsubscribe(self):
        """Test unsubscribe method"""

        unsubscribed_topics = []

        class ConcreteTransport(Transport):
            async def connect(self) -> None:
                pass

            async def disconnect(self) -> None:
                pass

            async def publish(self, topic: str, message: bytes) -> None:
                pass

            async def subscribe(self, topic: str, handler: MessageHandler) -> None:
                pass

            async def unsubscribe(self, topic: str) -> None:
                unsubscribed_topics.append(topic)

        transport = ConcreteTransport()
        await transport.unsubscribe("test_topic")

        assert unsubscribed_topics == ["test_topic"]

    def test_transport_is_connected_default(self):
        """Test default is_connected returns False"""

        class ConcreteTransport(Transport):
            async def connect(self) -> None:
                pass

            async def disconnect(self) -> None:
                pass

            async def publish(self, topic: str, message: bytes) -> None:
                pass

            async def subscribe(self, topic: str, handler: MessageHandler) -> None:
                pass

            async def unsubscribe(self, topic: str) -> None:
                pass

        transport = ConcreteTransport()
        assert transport.is_connected() is False

    def test_transport_is_connected_custom_implementation(self):
        """Test custom is_connected implementation"""

        class ConnectedTransport(Transport):
            def __init__(self):
                self._connected = True

            def is_connected(self) -> bool:
                return self._connected

            async def connect(self) -> None:
                pass

            async def disconnect(self) -> None:
                pass

            async def publish(self, topic: str, message: bytes) -> None:
                pass

            async def subscribe(self, topic: str, handler: MessageHandler) -> None:
                pass

            async def unsubscribe(self, topic: str) -> None:
                pass

        transport = ConnectedTransport()
        assert transport.is_connected() is True

        transport._connected = False
        assert transport.is_connected() is False


class TestMessageHandler:
    """Test suite for MessageHandler type"""

    @pytest.mark.asyncio
    async def test_message_handler_callable(self):
        """Test MessageHandler is a callable type"""

        async def handler(msg: bytes) -> None:
            pass

        # Should be callable
        await handler(b"test")

    @pytest.mark.asyncio
    async def test_message_handler_with_implementation(self):
        """Test MessageHandler with actual implementation"""

        messages = []

        async def handler(msg: bytes) -> None:
            messages.append(msg)

        await handler(b"message1")
        await handler(b"message2")

        assert messages == [b"message1", b"message2"]
