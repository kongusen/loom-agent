"""
Tests for NATS Transport
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import sys

# Mock nats module at import time
mock_nats_module = MagicMock()
sys.modules["nats"] = mock_nats_module
sys.modules["nats.aio"] = MagicMock()
sys.modules["nats.aio.client"] = MagicMock()

from loom.events.nats_transport import NATSTransport


@pytest.fixture
def mock_client():
    """Create a mock NATS client"""
    client = AsyncMock()
    client.subscribe = AsyncMock(return_value=123)
    client.unsubscribe = AsyncMock()
    client.publish = AsyncMock()
    client.close = AsyncMock()
    return client


class TestNATSTransport:
    """Test suite for NATSTransport"""

    @pytest.fixture
    def transport(self):
        """Create a NATS transport instance"""
        return NATSTransport()

    @pytest.fixture
    def connected_transport(self, transport, mock_client):
        """Create a connected transport"""
        # Manually set the connected state
        transport._client = mock_client
        transport._connected = True
        return transport

    def test_init_default(self, transport):
        """Test initialization with default values"""
        assert transport._servers == ["nats://localhost:4222"]
        assert transport._name == "loom-agent"
        assert transport._max_reconnect_attempts == 10
        assert transport._client is None
        assert transport._connected is False
        assert transport._subscriptions == {}

    def test_init_with_custom_servers(self):
        """Test initialization with custom servers"""
        servers = ["nats://server1:4222", "nats://server2:4222"]
        transport = NATSTransport(servers=servers)
        assert transport._servers == servers

    def test_init_with_custom_name(self):
        """Test initialization with custom name"""
        transport = NATSTransport(name="custom-name")
        assert transport._name == "custom-name"

    def test_init_with_custom_max_reconnect(self):
        """Test initialization with custom max reconnect"""
        transport = NATSTransport(max_reconnect_attempts=5)
        assert transport._max_reconnect_attempts == 5

    @pytest.mark.asyncio
    async def test_connect(self, transport, mock_client):
        """Test connecting to NATS"""
        mock_nats_module.connect = AsyncMock(return_value=mock_client)

        await transport.connect()

        assert transport._connected is True
        assert transport._client is mock_client
        mock_nats_module.connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect(self, connected_transport, mock_client):
        """Test disconnecting from NATS"""
        await connected_transport.disconnect()

        assert connected_transport._connected is False
        assert connected_transport._client is None
        mock_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect_when_not_connected(self, transport):
        """Test disconnecting when not connected"""
        await transport.disconnect()
        assert transport._connected is False

    @pytest.mark.asyncio
    async def test_disconnect_with_subscriptions(self, connected_transport, mock_client):
        """Test disconnecting unsubscribes from all topics"""
        connected_transport._subscriptions = {"topic1": 1, "topic2": 2}

        await connected_transport.disconnect()

        mock_client.close.assert_called_once()
        assert connected_transport._subscriptions == {}

    def test_is_connected(self, transport):
        """Test checking connection status"""
        assert transport.is_connected() is False

    @pytest.mark.asyncio
    async def test_is_connected_after_connect(self, connected_transport):
        """Test is_connected returns True after connection"""
        assert connected_transport.is_connected() is True

    @pytest.mark.asyncio
    async def test_is_connected_after_disconnect(self, connected_transport, mock_client):
        """Test is_connected returns False after disconnect"""
        await connected_transport.disconnect()
        assert connected_transport.is_connected() is False

    @pytest.mark.asyncio
    async def test_publish(self, connected_transport, mock_client):
        """Test publishing a message"""
        await connected_transport.publish("test.topic", b"test message")
        mock_client.publish.assert_called_once_with("test.topic", b"test message")

    @pytest.mark.asyncio
    async def test_publish_not_connected(self, transport):
        """Test publishing when not connected raises error"""
        with pytest.raises(RuntimeError, match="Transport not connected"):
            await transport.publish("test.topic", b"message")

    @pytest.mark.asyncio
    async def test_subscribe(self, connected_transport, mock_client):
        """Test subscribing to a topic"""
        handler_called = []

        async def handler(msg):
            handler_called.append(msg)

        await connected_transport.subscribe("test.topic", handler)

        assert "test.topic" in connected_transport._subscriptions
        assert connected_transport._subscriptions["test.topic"] == 123

    @pytest.mark.asyncio
    async def test_subscribe_not_connected(self, transport):
        """Test subscribing when not connected raises error"""
        async def handler(msg):
            pass

        with pytest.raises(RuntimeError, match="Transport not connected"):
            await transport.subscribe("test.topic", handler)

    @pytest.mark.asyncio
    async def test_unsubscribe(self, connected_transport, mock_client):
        """Test unsubscribing from a topic"""
        async def handler(msg):
            pass

        await connected_transport.subscribe("test.topic", handler)
        await connected_transport.unsubscribe("test.topic")

        assert "test.topic" not in connected_transport._subscriptions
        mock_client.unsubscribe.assert_called_once_with(123)

    @pytest.mark.asyncio
    async def test_unsubscribe_nonexistent_topic(self, connected_transport):
        """Test unsubscribing from a non-existent topic"""
        await connected_transport.unsubscribe("nonexistent.topic")

    @pytest.mark.asyncio
    async def test_message_handler_wrapper(self, connected_transport, mock_client):
        """Test that message handler wraps data correctly"""
        received_data = []

        async def handler(data):
            received_data.append(data)

        await connected_transport.subscribe("test.topic", handler)

        mock_msg = MagicMock()
        mock_msg.data = b"test data"

        call_args = mock_client.subscribe.call_args
        wrapper_fn = call_args.kwargs.get("cb") or call_args[1]["cb"]

        await wrapper_fn(mock_msg)

        assert received_data == [b"test data"]
