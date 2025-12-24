"""
Base Node Abstraction (Fractal System)
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from uuid import uuid4

from loom.protocol.cloudevents import CloudEvent
from loom.kernel.dispatcher import Dispatcher

class Node(ABC):
    """
    Abstract Base Class for all Fractal Nodes (Agent, Tool, Crew).
    Implements standard event subscription and request handling.
    """
    
    def __init__(self, node_id: str, dispatcher: Dispatcher):
        self.node_id = node_id
        self.dispatcher = dispatcher
        self.source_uri = f"/node/{node_id}" # Standard URI
        
        # Auto-subscribe to my requests
        asyncio.create_task(self._subscribe_to_events())

    async def _subscribe_to_events(self):
        """Subscribe to 'node.request' targeting this node."""
        topic = f"node.request/{self.source_uri.strip('/')}"
        await self.dispatcher.bus.subscribe(topic, self._handle_request)

    async def _handle_request(self, event: CloudEvent):
        """
        Standard request handler.
        1. Calls node-specific process()
        2. Dispatches response/result/error
        """
        try:
            # 1. Process
            result = await self.process(event)
            
            # 2. Respond
            response_event = CloudEvent.create(
                source=self.source_uri,
                type="node.response",
                data={
                    "request_id": event.id,
                    "result": result
                },
                traceparent=event.traceparent
            )
            # Response topic usually goes to whoever asked, or open bus
            # In request-reply pattern, typically we might just publish it
            # and the caller subscribes to node.response/originator
            
            # For now, just generic publish
            await self.dispatcher.dispatch(response_event)
            
        except Exception as e:
            error_event = CloudEvent.create(
                source=self.source_uri,
                type="node.error",
                data={
                    "request_id": event.id,
                    "error": str(e)
                },
                traceparent=event.traceparent
            )
            await self.dispatcher.dispatch(error_event)

    async def call(self, target_node: str, data: Dict[str, Any]) -> Any:
        """
        Call another node and wait for response.

        FIXED: Now properly cleans up subscription using unsubscribe()
        to prevent memory leaks from accumulated handlers.
        """
        request_id = str(uuid4())
        request_event = CloudEvent.create(
            source=self.source_uri,
            type="node.request",
            data=data,
            subject=target_node,
        )
        request_event.id = request_id

        # Subscribe to response
        # Using Broadcast Reply pattern: listen to target's responses
        response_future = asyncio.Future()

        async def handle_response(event: CloudEvent):
            if event.data and event.data.get("request_id") == request_id:
                if not response_future.done():
                    if event.type == "node.error":
                         response_future.set_exception(Exception(event.data.get("error", "Unknown Error")))
                    else:
                         response_future.set_result(event.data.get("result"))

        # Topic: node.response/{target_node}
        # Note: clean URI
        target_topic = f"node.response/{target_node.strip('/')}"

        # We need access to bus directly or via dispatcher
        # Dispatcher has .bus
        await self.dispatcher.bus.subscribe(target_topic, handle_response)

        try:
            # Dispatch request
            await self.dispatcher.dispatch(request_event)

            # Wait for response
            return await asyncio.wait_for(response_future, timeout=30.0)
        finally:
            # FIXED: Cleanup subscription to prevent memory leaks
            await self.dispatcher.bus.unsubscribe(target_topic, handle_response)


    @abstractmethod
    async def process(self, event: CloudEvent) -> Any:
        """Core logic."""
        pass
