
import asyncio
import json
import os
import time
from typing import Optional, List, Dict, Any
import logging

try:
    import websockets
    from websockets.client import WebSocketClientProtocol
except ImportError:
    websockets = None
    WebSocketClientProtocol = Any

from loom.kernel.base_interceptor import Interceptor
from loom.protocol.cloudevents import CloudEvent

logger = logging.getLogger(__name__)

class StudioInterceptor(Interceptor):
    """
    Studio Interceptor: Captures all events and forwards them to Studio Server.

    Features:
    - Async non-blocking: Uses asyncio.create_task to avoid blocking main flow.
    - Optional: Controlled by LOOM_STUDIO_ENABLED environment variable.
    - Batching: Buffers events and sends in batches to reduce network overhead.
    """

    def __init__(self, studio_url: str = "ws://localhost:8765", enabled: bool = False):
        self.studio_url = studio_url
        self.ws: Optional[WebSocketClientProtocol] = None
        self.event_buffer: List[CloudEvent] = []
        self.buffer_size = 10
        # Priority: Argument > Env Var
        self.enabled = enabled or os.getenv("LOOM_STUDIO_ENABLED", "false").lower() == "true"
        self._loop = None
        
        if self.enabled and not websockets:
            logger.warning("LOOM_STUDIO_ENABLED is true but websockets is not installed. Disabling Studio.")
            self.enabled = False

        if self.enabled:
             asyncio.create_task(self._ensure_connection())

    async def _ensure_connection(self):
        """Ensure WebSocket connection is established"""
        if not self.enabled:
            return

        if self.ws:
            try:
                # Basic check if open
                if self.ws.state == 1: # Open
                     return
            except Exception:
                pass
            self.ws = None

        try:
            # Append /ws/ingest to the base URL if not present
            url = self.studio_url
            if not url.endswith("/ws/ingest"):
                url = f"{url.rstrip('/')}/ws/ingest"
            
            # Simple debounce/lock could go here but for now just log
            print(f"DEBUG: Connecting to {url}") 
            self.ws = await websockets.connect(url)
            logger.info(f"Connected to Loom Studio at {url}")
            print(f"DEBUG: Connected successfully")
        except Exception as e:
            # Silent fail to not disrupt agent operation, but log it
            logger.debug(f"Failed to connect to Studio: {e}") 
            print(f"DEBUG: Failed to connect: {e}")
            self.ws = None

    async def pre_invoke(self, event: CloudEvent) -> Optional[CloudEvent]:
        """Capture event (pre-phase) - 不发送事件，只在 post_invoke 发送以避免重复"""
        # 不在 pre 阶段发送事件，只在 post 阶段发送完整的事件
        return event

    async def post_invoke(self, event: CloudEvent) -> None:
        """Capture event (post-phase) - 只在此阶段发送事件，避免重复"""
        if self.enabled:
            enriched_event_data = event.model_dump(mode='json')
            if "extensions" not in enriched_event_data:
                enriched_event_data["extensions"] = {}
                
            # 标记为 post 阶段（虽然现在只在 post 发送，但保留标记以便将来扩展）
            enriched_event_data["extensions"]["studio_phase"] = "post"
            enriched_event_data["extensions"]["studio_timestamp"] = time.time()

            asyncio.create_task(self._send_event_data(enriched_event_data))

    async def _send_event_data(self, event_data: Dict[str, Any]):
        """Buffer and send event data"""
        try:
            self.event_buffer.append(event_data)

            if len(self.event_buffer) >= self.buffer_size:
                await self._flush_buffer()
        except Exception as e:
            logger.error(f"Error in StudioInterceptor: {e}")

    async def _flush_buffer(self):
        """Flush buffered events to server"""
        if not self.event_buffer:
            return
            
        # Snapshot and clear immediately to avoid duplicates/race
        current_batch = list(self.event_buffer)
        self.event_buffer = []

        await self._ensure_connection()

        if self.ws:
            try:
                batch = {
                    "type": "event_batch",
                    "events": current_batch
                }
                await self.ws.send(json.dumps(batch))
            except Exception as e:
                logger.debug(f"Failed to send batch to Studio: {e}")
                print(f"DEBUG: Failed to send batch: {e}")
                # Re-queue? For now drop to avoid complexity
        else:
             print(f"DEBUG: No connection, dropping batch of {len(current_batch)}")
