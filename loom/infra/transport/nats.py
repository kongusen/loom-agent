import asyncio
import logging
from typing import Any

try:
    import nats
    from nats.aio.client import Client as NATSClient
    from nats.js import JetStreamContext
except ImportError:
    nats = None
    NATSClient = None  # type: ignore
    JetStreamContext = None  # type: ignore

import contextlib

from loom.protocol.cloudevents import CloudEvent

from .base import EventHandler, Transport

logger = logging.getLogger(__name__)


class NATSTransport(Transport):
    """
    NATS Transport Implementation.
    Supports Core NATS and JetStream (optional).
    Requires 'nats-py' package.
    """

    def __init__(
        self,
        servers: list[str] | None = None,
        use_jetstream: bool = False,
        stream_name: str = "LOOM_EVENTS",
    ):
        if servers is None:
            servers = ["nats://localhost:4222"]
        if not nats:
            raise ImportError(
                "nats-py package is required for NATSTransport. Install with 'pip install nats-py'"
            )

        self.servers = servers
        self.use_jetstream = use_jetstream
        self.stream_name = stream_name

        self.nc: NATSClient | None = None
        self.js: JetStreamContext | None = None
        self._handlers: dict[str, list[EventHandler]] = {}
        self._subscriptions: list[tuple[str, Any]] = []  # (topic, subscription)
        self._connected = False

    async def connect(self) -> None:
        try:
            self.nc = await nats.connect(servers=self.servers)

            if self.use_jetstream:
                self.js = self.nc.jetstream()
                # Create stream if not exists is best effort or explicit setup
                # Here we assume stream might be managed externally or auto-created
                try:
                    await self.js.add_stream(name=self.stream_name, subjects=["loom.>"])
                except Exception as e:
                    logger.debug(f"Stream creation check: {e}")

            self._connected = True
            logger.info(f"NATSTransport connected to {self.servers}")
        except Exception as e:
            logger.error(f"NATS connection failed: {e}")
            raise

    async def disconnect(self) -> None:
        self._connected = False

        for sub_tuple in self._subscriptions:
            sub = sub_tuple[1]
            with contextlib.suppress(Exception):
                await sub.unsubscribe()

        if self.nc:
            await self.nc.close()

        logger.info("NATSTransport disconnected")

    async def publish(self, topic: str, event: CloudEvent) -> None:
        if not self._connected:
            raise RuntimeError("NATSTransport not connected")

        # NATS Subject: loom.{topic} (replace / with .)
        subject = self._to_subject(topic)
        payload = event.model_dump_json().encode()

        if self.use_jetstream and self.js:
            await self.js.publish(subject, payload)
        elif self.nc:
            await self.nc.publish(subject, payload)

    async def subscribe(self, topic: str, handler: EventHandler) -> None:
        if not self._connected:
            raise RuntimeError("NATSTransport not connected")

        # Normalize subject for wildcard
        subject = self._to_subject(topic)

        # NATS wildcards: * (one token), > (tail)
        # Loom wildcards: * (usually suffix)
        # If topic ends with *, replace with >
        if subject.endswith(".*"):
            subject = subject[:-2] + ".>"

        if topic not in self._handlers:
            self._handlers[topic] = []

            async def cb(msg):
                try:
                    data = msg.data.decode()
                    event = CloudEvent.model_validate_json(data)
                    # How to map back to specific handlers?
                    # We invoke all handlers for this subscription
                    handlers = self._handlers.get(topic, [])
                    for h in handlers:
                        asyncio.create_task(self._safe_exec(h, event))
                except Exception as e:
                    logger.error(f"Error handling NATS message: {e}")

            if self.use_jetstream and self.js:
                # Durable consumer? For now, ephemeral to match interface
                sub = await self.js.subscribe(subject, cb=cb)
            elif self.nc:
                sub = await self.nc.subscribe(subject, cb=cb)
            else:
                raise RuntimeError("NATS client not connected")

            # Store subscription with topic for later unsubscribe
            self._subscriptions.append((topic, sub))

        self._handlers[topic].append(handler)
        logger.debug(f"Subscribed to {subject}")

    async def unsubscribe(self, topic: str, handler: EventHandler) -> None:
        """
        Unsubscribe a handler from a topic.

        FIXED: Prevents memory leaks from accumulated handlers.
        """
        if topic in self._handlers:
            try:
                self._handlers[topic].remove(handler)

                # If no more handlers for this topic, unsubscribe from NATS
                if not self._handlers[topic]:
                    del self._handlers[topic]

                    # Find and unsubscribe the NATS subscription
                    for i, (sub_topic, sub) in enumerate(self._subscriptions):
                        if sub_topic == topic:
                            try:
                                await sub.unsubscribe()
                                self._subscriptions.pop(i)
                                logger.debug(f"Unsubscribed from {topic}")
                            except Exception as e:
                                logger.error(f"Error unsubscribing from NATS: {e}")
                            break
            except ValueError:
                # Handler not in list, ignore
                pass

    async def _safe_exec(self, handler: EventHandler, event: CloudEvent):
        try:
            await handler(event)
        except Exception as e:
            logger.error(f"Handler failed: {e}")

    def _to_subject(self, topic: str) -> str:
        # Replace / with .
        # e.g. node.request/agent -> node.request.agent
        # loom prefix
        safe_topic = topic.replace("/", ".")
        return f"loom.{safe_topic}"
