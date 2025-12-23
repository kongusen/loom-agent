
import asyncio
import logging
from typing import Dict, List, Optional
try:
    import nats
    from nats.aio.client import Client as NATSClient
    from nats.js import JetStreamContext
except ImportError:
    nats = None
    NATSClient = None # type: ignore
    JetStreamContext = None # type: ignore

from loom.interfaces.transport import Transport, EventHandler
from loom.protocol.cloudevents import CloudEvent

logger = logging.getLogger(__name__)

class NATSTransport(Transport):
    """
    NATS Transport Implementation.
    Supports Core NATS and JetStream (optional).
    Requires 'nats-py' package.
    """

    def __init__(
        self,
        servers: List[str] = ["nats://localhost:4222"],
        use_jetstream: bool = False,
        stream_name: str = "LOOM_EVENTS",
    ):
        if not nats:
            raise ImportError("nats-py package is required for NATSTransport. Install with 'pip install nats-py'")

        self.servers = servers
        self.use_jetstream = use_jetstream
        self.stream_name = stream_name
        
        self.nc: Optional[NATSClient] = None
        self.js: Optional[JetStreamContext] = None
        self._handlers: Dict[str, List[EventHandler]] = {}
        self._subscriptions: List = [] 
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
        
        for sub in self._subscriptions:
             try:
                 await sub.unsubscribe()
             except Exception:
                 pass
        
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
        else:
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
            else:
                sub = await self.nc.subscribe(subject, cb=cb)
            
            self._subscriptions.append(sub)

        self._handlers[topic].append(handler)
        logger.debug(f"Subscribed to {subject}")

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
