"""
Tests for Redis Transport
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from loom.infra.transport.redis import RedisTransport
from loom.protocol.cloudevents import CloudEvent


class MockRedis:
    """Mock Redis client."""
    def __init__(self):
        self.data = {}
        self.channels = {}
        self.patterns = {}
        self.closed = False
        self._pubsub = None

    async def ping(self):
        return True

    async def publish(self, channel, data):
        if channel not in self.channels:
            self.channels[channel] = []
        self.channels[channel].append(data)

    async def close(self):
        self.closed = True

    def pubsub(self):
        """Return a pubsub instance."""
        if self._pubsub is None:
            self._pubsub = MockPubSub()
        return self._pubsub


class MockPubSub:
    """Mock Redis PubSub."""
    def __init__(self):
        self.subscribed = []
        self.patterns = {}
        self.messages = asyncio.Queue()
        self.closed = False

    async def psubscribe(self, pattern):
        if pattern not in self.subscribed:
            self.subscribed.append(pattern)

    async def punsubscribe(self, pattern):
        if pattern in self.subscribed:
            self.subscribed.remove(pattern)

    async def close(self):
        self.closed = True

    async def listen(self):
        """Mock listen generator."""
        while not self.closed:
            try:
                msg = await asyncio.wait_for(self.messages.get(), timeout=0.1)
                yield msg
            except asyncio.TimeoutError:
                continue

    def add_message(self, channel, data):
        """Add a message to the queue."""
        self.messages.put_nowait({
            "type": "pmessage",
            "channel": channel,
            "data": data
        })


@pytest.fixture
def mock_redis_module():
    """Mock redis.asyncio module."""
    mock = MagicMock()
    mock.Redis = MockRedis
    mock.from_url = MagicMock(return_value=MockRedis())
    return mock


@pytest.fixture
def mock_pubsub():
    """Create a mock pubsub."""
    return MockPubSub()


class TestRedisTransport:
    """Test RedisTransport class."""

    def test_initialization_with_redis(self, mock_redis_module):
        """Test initialization when redis package is available."""
        with patch('loom.infra.transport.redis.aioredis', mock_redis_module):
            transport = RedisTransport("redis://localhost:6379")
            assert transport.redis_url == "redis://localhost:6379"
            assert transport.redis is None
            assert transport.pubsub is None
            assert transport._handlers == {}
            assert transport._connected is False

    def test_initialization_custom_url(self, mock_redis_module):
        """Test initialization with custom URL."""
        with patch('loom.infra.transport.redis.aioredis', mock_redis_module):
            transport = RedisTransport("redis://remote:6380")
            assert transport.redis_url == "redis://remote:6380"

    def test_initialization_without_redis(self):
        """Test initialization when redis package is not available."""
        with patch('loom.infra.transport.redis.aioredis', None):
            with pytest.raises(ImportError, match="redis package is required"):
                RedisTransport()

    @pytest.mark.asyncio
    async def test_connect_success(self, mock_redis_module):
        """Test successful connection to Redis."""
        mock_redis = MockRedis()

        mock_redis_module.from_url = MagicMock(return_value=mock_redis)

        with patch('loom.infra.transport.redis.aioredis', mock_redis_module):
            transport = RedisTransport()
            await transport.connect()

            assert transport._connected is True
            assert transport.redis == mock_redis
            assert transport._listen_task is not None

            # Cleanup
            await transport.disconnect()

    @pytest.mark.asyncio
    async def test_connect_failure(self, mock_redis_module):
        """Test connection failure handling."""
        mock_redis_module.from_url = MagicMock(side_effect=ConnectionError("Connection failed"))

        with patch('loom.infra.transport.redis.aioredis', mock_redis_module):
            transport = RedisTransport()
            with pytest.raises(ConnectionError):
                await transport.connect()

    @pytest.mark.asyncio
    async def test_disconnect(self, mock_redis_module):
        """Test disconnection from Redis."""
        mock_redis = MockRedis()

        mock_redis_module.from_url = MagicMock(return_value=mock_redis)

        with patch('loom.infra.transport.redis.aioredis', mock_redis_module):
            transport = RedisTransport()
            await transport.connect()
            assert transport._connected is True

            await transport.disconnect()

            assert transport._connected is False
            assert mock_redis.closed is True

    @pytest.mark.asyncio
    async def test_disconnect_cancels_listener(self, mock_redis_module):
        """Test that disconnect cancels the listener task."""
        mock_redis = MockRedis()
        mock_redis_module.from_url = MagicMock(return_value=mock_redis)

        with patch('loom.infra.transport.redis.aioredis', mock_redis_module):
            transport = RedisTransport()
            await transport.connect()

            task = transport._listen_task
            assert task is not None

            await transport.disconnect()

            assert task.cancelled()

    @pytest.mark.asyncio
    async def test_publish_not_connected(self, mock_redis_module):
        """Test publishing when not connected raises error."""
        with patch('loom.infra.transport.redis.aioredis', mock_redis_module):
            transport = RedisTransport()
            event = CloudEvent.create(
                source="/test",
                type="test.event",
                data={"test": "data"}
            )

            with pytest.raises(RuntimeError, match="not connected"):
                await transport.publish("test.topic", event)

    @pytest.mark.asyncio
    async def test_publish_success(self, mock_redis_module):
        """Test successful event publishing."""
        mock_redis = MockRedis()
        mock_redis_module.from_url = MagicMock(return_value=mock_redis)

        with patch('loom.infra.transport.redis.aioredis', mock_redis_module):
            transport = RedisTransport()
            await transport.connect()

            event = CloudEvent.create(
                source="/test",
                type="test.event",
                data={"test": "data"}
            )

            await transport.publish("test.topic", event)

            # Verify message was published to correct channel
            assert "loom.test.topic" in mock_redis.channels

            await transport.disconnect()

    @pytest.mark.asyncio
    async def test_subscribe_not_connected(self, mock_redis_module):
        """Test subscribing when not connected raises error."""
        with patch('loom.infra.transport.redis.aioredis', mock_redis_module):
            transport = RedisTransport()

            async def handler(event):
                pass

            with pytest.raises(RuntimeError, match="not connected"):
                await transport.subscribe("test.topic", handler)

    @pytest.mark.asyncio
    async def test_subscribe_success(self, mock_redis_module):
        """Test successful subscription."""
        mock_redis = MockRedis()
        mock_pubsub = MockPubSub()
        mock_redis.pubsub = MagicMock(return_value=mock_pubsub)

        mock_redis_module.from_url = MagicMock(return_value=mock_redis)

        with patch('loom.infra.transport.redis.aioredis', mock_redis_module):
            transport = RedisTransport()

            # Mock the pubsub creation
            with patch.object(transport, 'pubsub', mock_pubsub):
                await transport.connect()

                async def handler(event):
                    pass

                await transport.subscribe("test.topic", handler)

                assert "test.topic" in transport._handlers
                assert handler in transport._handlers["test.topic"]
                assert "loom.test.topic" in mock_pubsub.subscribed

                await transport.disconnect()

    @pytest.mark.asyncio
    async def test_subscribe_multiple_handlers(self, mock_redis_module):
        """Test subscribing multiple handlers to same topic."""
        mock_redis = MockRedis()
        mock_pubsub = MockPubSub()
        mock_redis.pubsub = MagicMock(return_value=mock_pubsub)

        mock_redis_module.from_url = MagicMock(return_value=mock_redis)

        with patch('loom.infra.transport.redis.aioredis', mock_redis_module):
            transport = RedisTransport()

            with patch.object(transport, 'pubsub', mock_pubsub):
                await transport.connect()

                async def handler1(event):
                    pass

                async def handler2(event):
                    pass

                await transport.subscribe("test.topic", handler1)
                await transport.subscribe("test.topic", handler2)

                assert len(transport._handlers["test.topic"]) == 2
                assert handler1 in transport._handlers["test.topic"]
                assert handler2 in transport._handlers["test.topic"]

                await transport.disconnect()

    @pytest.mark.asyncio
    async def test_unsubscribe_handler(self, mock_redis_module):
        """Test unsubscribing a handler."""
        mock_redis = MockRedis()
        mock_pubsub = MockPubSub()
        mock_redis.pubsub = MagicMock(return_value=mock_pubsub)

        mock_redis_module.from_url = MagicMock(return_value=mock_redis)

        with patch('loom.infra.transport.redis.aioredis', mock_redis_module):
            transport = RedisTransport()

            with patch.object(transport, 'pubsub', mock_pubsub):
                await transport.connect()

                async def handler(event):
                    pass

                await transport.subscribe("test.topic", handler)
                assert handler in transport._handlers["test.topic"]

                await transport.unsubscribe("test.topic", handler)
                # After removing last handler, the topic is removed from handlers
                assert "test.topic" not in transport._handlers

                await transport.disconnect()

    @pytest.mark.asyncio
    async def test_unsubscribe_last_handler_unsubscribes_redis(self, mock_redis_module):
        """Test that unsubscribing last handler unsubscribes from Redis."""
        mock_redis = MockRedis()
        mock_pubsub = MockPubSub()
        mock_redis.pubsub = MagicMock(return_value=mock_pubsub)

        mock_redis_module.from_url = MagicMock(return_value=mock_redis)

        with patch('loom.infra.transport.redis.aioredis', mock_redis_module):
            transport = RedisTransport()

            with patch.object(transport, 'pubsub', mock_pubsub):
                await transport.connect()

                async def handler(event):
                    pass

                await transport.subscribe("test.topic", handler)
                await transport.unsubscribe("test.topic", handler)

                # Verify Redis unsubscribe was called
                assert "loom.test.topic" not in mock_pubsub.subscribed

                await transport.disconnect()

    @pytest.mark.asyncio
    async def test_unsubscribe_nonexistent_handler(self, mock_redis_module):
        """Test unsubscribing a handler that doesn't exist."""
        mock_redis = MockRedis()
        mock_pubsub = MockPubSub()
        mock_redis.pubsub = MagicMock(return_value=mock_pubsub)

        mock_redis_module.from_url = MagicMock(return_value=mock_redis)

        with patch('loom.infra.transport.redis.aioredis', mock_redis_module):
            transport = RedisTransport()

            with patch.object(transport, 'pubsub', mock_pubsub):
                await transport.connect()

                async def handler(event):
                    pass

                # Should not raise even though handler not subscribed
                await transport.unsubscribe("test.topic", handler)

                await transport.disconnect()

    @pytest.mark.asyncio
    async def test_to_channel(self, mock_redis_module):
        """Test _to_channel method."""
        with patch('loom.infra.transport.redis.aioredis', mock_redis_module):
            transport = RedisTransport()

            assert transport._to_channel("test.topic") == "loom.test.topic"
            assert transport._to_channel("node.request") == "loom.node.request"
            assert transport._to_channel("wildcard.*") == "loom.wildcard.*"

    def test_match_exact(self, mock_redis_module):
        """Test _match with exact channel."""
        with patch('loom.infra.transport.redis.aioredis', mock_redis_module):
            transport = RedisTransport()

            assert transport._match("loom.test.topic", "loom.test.topic") is True
            assert transport._match("loom.test.topic", "loom.other.topic") is False

    def test_match_wildcard(self, mock_redis_module):
        """Test _match with wildcard patterns."""
        with patch('loom.infra.transport.redis.aioredis', mock_redis_module):
            transport = RedisTransport()

            assert transport._match("loom.test.topic", "loom.*") is True
            assert transport._match("loom.any.topic", "loom.*.topic") is True
            assert transport._match("loom.test.subtopic", "loom.*") is True

    @pytest.mark.asyncio
    async def test_handle_message_dispatches_to_handlers(self, mock_redis_module):
        """Test that _handle_message dispatches to matching handlers."""
        mock_redis = MockRedis()
        mock_redis_module.from_url = MagicMock(return_value=mock_redis)

        with patch('loom.infra.transport.redis.aioredis', mock_redis_module):
            transport = RedisTransport()

            event = CloudEvent.create(
                source="/test",
                type="test.event",
                data={"test": "data"}
            )

            received = []

            async def handler(e):
                received.append(e)

            transport._handlers["test.topic"] = [handler]

            await transport._handle_message("loom.test.topic", event.model_dump_json())

            # Give time for async task to complete
            await asyncio.sleep(0.1)

            assert len(received) == 1

    @pytest.mark.asyncio
    async def test_handle_message_with_pattern(self, mock_redis_module):
        """Test that _handle_message matches wildcard patterns."""
        mock_redis = MockRedis()
        mock_redis_module.from_url = MagicMock(return_value=mock_redis)

        with patch('loom.infra.transport.redis.aioredis', mock_redis_module):
            transport = RedisTransport()

            event = CloudEvent.create(
                source="/test",
                type="test.event",
                data={"test": "data"}
            )

            received = []

            async def handler(e):
                received.append(e)

            transport._handlers["*"] = [handler]

            await transport._handle_message("loom.any.topic", event.model_dump_json())

            await asyncio.sleep(0.1)

            assert len(received) == 1

    @pytest.mark.asyncio
    async def test_safe_exec_catches_handler_errors(self, mock_redis_module):
        """Test that _safe_exec catches and logs handler errors."""
        mock_redis = MockRedis()
        mock_redis_module.from_url = MagicMock(return_value=mock_redis)

        with patch('loom.infra.transport.redis.aioredis', mock_redis_module):
            transport = RedisTransport()

            event = CloudEvent.create(
                source="/test",
                type="test.event",
                data={"test": "data"}
            )

            async def failing_handler(e):
                raise ValueError("Handler failed")

            # Should not raise
            await transport._safe_exec(failing_handler, event)

    @pytest.mark.asyncio
    async def test_listener_handles_cancelled_error(self, mock_redis_module):
        """Test that listener handles CancelledError gracefully."""
        mock_redis = MockRedis()
        mock_pubsub = MockPubSub()
        mock_redis.pubsub = MagicMock(return_value=mock_pubsub)
        mock_redis_module.from_url = MagicMock(return_value=mock_redis)

        with patch('loom.infra.transport.redis.aioredis', mock_redis_module):
            transport = RedisTransport()

            with patch.object(transport, 'pubsub', mock_pubsub):
                await transport.connect()

                # Listener should be running
                assert transport._listen_task is not None

                # Disconnect should cancel listener without error
                await transport.disconnect()

    @pytest.mark.asyncio
    async def test_listener_handles_generic_errors(self, mock_redis_module):
        """Test that listener handles and logs errors."""
        mock_redis = MockRedis()
        mock_pubsub = MockPubSub()

        # Make listen raise an error
        async def failing_listen():
            raise RuntimeError("Listener error")

        mock_pubsub.listen = failing_listen
        mock_redis.pubsub = MagicMock(return_value=mock_pubsub)
        mock_redis_module.from_url = MagicMock(return_value=mock_redis)

        with patch('loom.infra.transport.redis.aioredis', mock_redis_module):
            transport = RedisTransport()

            with patch.object(transport, 'pubsub', mock_pubsub):
                await transport.connect()

                # Wait for listener to fail
                await asyncio.sleep(0.1)

                # Task should be done but not raise
                assert transport._listen_task.done()

                await transport.disconnect()

    @pytest.mark.asyncio
    async def test_subscribe_idempotent(self, mock_redis_module):
        """Test that subscribing same topic twice doesn't duplicate Redis subscription."""
        mock_redis = MockRedis()
        mock_pubsub = MockPubSub()
        mock_redis.pubsub = MagicMock(return_value=mock_pubsub)

        mock_redis_module.from_url = MagicMock(return_value=mock_redis)

        with patch('loom.infra.transport.redis.aioredis', mock_redis_module):
            transport = RedisTransport()

            with patch.object(transport, 'pubsub', mock_pubsub):
                await transport.connect()

                async def handler1(e):
                    pass

                async def handler2(e):
                    pass

                await transport.subscribe("test.topic", handler1)
                await transport.subscribe("test.topic", handler2)

                # Should only subscribe once to Redis
                # (second handler just adds to internal list)
                assert mock_pubsub.subscribed.count("loom.test.topic") == 1
                assert len(transport._handlers["test.topic"]) == 2

                await transport.disconnect()

    @pytest.mark.asyncio
    async def test_publish_with_wildcard_topic(self, mock_redis_module):
        """Test publishing to wildcard topic."""
        mock_redis = MockRedis()
        mock_redis_module.from_url = MagicMock(return_value=mock_redis)

        with patch('loom.infra.transport.redis.aioredis', mock_redis_module):
            transport = RedisTransport()
            await transport.connect()

            event = CloudEvent.create(
                source="/test",
                type="test.event",
                data={"test": "data"}
            )

            await transport.publish("test.*", event)

            assert "loom.test.*" in mock_redis.channels

            await transport.disconnect()
