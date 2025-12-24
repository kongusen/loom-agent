
import asyncio
import json
import logging
from typing import Dict, List, Optional
try:
    import redis.asyncio as aioredis
except ImportError:
    aioredis = None

from loom.interfaces.transport import Transport, EventHandler
from loom.protocol.cloudevents import CloudEvent

logger = logging.getLogger(__name__)

class RedisTransport(Transport):
    """
    Redis Pub/Sub Transport.
    Requires 'redis' package.
    """

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        if not aioredis:
            raise ImportError("redis package is required for RedisTransport. Install with 'pip install redis'")
        
        self.redis_url = redis_url
        self.redis: Optional[aioredis.Redis] = None
        self.pubsub: Optional[aioredis.client.PubSub] = None
        self._handlers: Dict[str, List[EventHandler]] = {}
        self._connected = False
        self._listen_task: Optional[asyncio.Task] = None

    async def connect(self) -> None:
        try:
            self.redis = aioredis.from_url(self.redis_url, decode_responses=True)
            await self.redis.ping()
            self.pubsub = self.redis.pubsub()
            self._connected = True
            
            # Start listener loop
            self._listen_task = asyncio.create_task(self._listener())
            logger.info(f"RedisTransport connected to {self.redis_url}")
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            raise

    async def disconnect(self) -> None:
        self._connected = False
        if self._listen_task:
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass
        
        if self.pubsub:
            await self.pubsub.close()
        
        if self.redis:
            await self.redis.close()
        
        logger.info("RedisTransport disconnected")

    async def publish(self, topic: str, event: CloudEvent) -> None:
        if not self._connected:
            raise RuntimeError("RedisTransport not connected")
        
        # Redis channel convention: loom.{topic}
        channel = self._to_channel(topic)
        payload = event.model_dump_json()
        await self.redis.publish(channel, payload)

    async def subscribe(self, topic: str, handler: EventHandler) -> None:
        if not self._connected:
            raise RuntimeError("RedisTransport not connected")

        # Map loom topic to redis channel pattern
        channel = self._to_channel(topic)

        if topic not in self._handlers:
            self._handlers[topic] = []
            # Subscribe in Redis
            await self.pubsub.psubscribe(channel)

        self._handlers[topic].append(handler)
        logger.debug(f"Subscribed to {channel}")

    async def unsubscribe(self, topic: str, handler: EventHandler) -> None:
        """
        Unsubscribe a handler from a topic.

        FIXED: Prevents memory leaks from accumulated handlers.
        """
        if topic in self._handlers:
            try:
                self._handlers[topic].remove(handler)

                # If no more handlers for this topic, unsubscribe from Redis
                if not self._handlers[topic]:
                    del self._handlers[topic]
                    channel = self._to_channel(topic)
                    if self.pubsub and self._connected:
                        await self.pubsub.punsubscribe(channel)
                        logger.debug(f"Unsubscribed from {channel}")
            except ValueError:
                # Handler not in list, ignore
                pass

    async def _listener(self):
        try:
            async for message in self.pubsub.listen():
                if message["type"] == "pmessage":
                    channel = message["channel"]
                    data = message["data"]
                    await self._handle_message(channel, data)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Redis listener error: {e}")

    async def _handle_message(self, channel: str, data: str):
        # Convert redis channel back to topic? 
        # Since we use psubscribe, we matched.
        # But we need to find which handlers to invoke.
        # Actually pattern matching is done by Redis.
        # But our internal registry matches by topic.
        
        # Simplification: We iterate our topic patterns to find match?
        # Or we assume channel == _to_channel(topic)
        # But wildcard * in topic maps to * in redis.
        
        try:
            event = CloudEvent.model_validate_json(data)
            
            # Dispatch to all matching local handlers
            # This is slightly inefficient if we have many patterns, but robust.
            for topic, handlers in self._handlers.items():
                if self._match(channel, self._to_channel(topic)):
                    for handler in handlers:
                        asyncio.create_task(self._safe_exec(handler, event))
        except Exception as e:
            logger.error(f"Failed to handle Redis message: {e}")

    async def _safe_exec(self, handler: EventHandler, event: CloudEvent):
        try:
             await handler(event)
        except Exception as e:
             logger.error(f"Handler failed: {e}")

    def _to_channel(self, topic: str) -> str:
        # loom.topic.sub
        # If topic has /, replace with . ?
        # Standard: topic is dot separated usually? 
        # Loom uses "node.request" etc.
        # If topic has *, it is wildcard.
        return f"loom.{topic}"

    def _match(self, channel: str, pattern: str) -> bool:
        # Redis-style glob matching implemented in Python for dispatch
        import fnmatch
        return fnmatch.fnmatch(channel, pattern)
