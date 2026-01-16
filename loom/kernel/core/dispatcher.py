"""
Event Dispatcher (Kernel)
"""

import contextlib
from typing import Any, cast

from loom.kernel.control.base import Interceptor
from loom.kernel.core.bus import UniversalEventBus
from loom.protocol.cloudevents import CloudEvent


class Dispatcher:
    """
    Central dispatch mechanism.
    1. Runs Interceptor Chain (Pre-invoke).
    2. Publishes to Bus.
    3. Runs Interceptor Chain (Post-invoke).

    Enhanced for Dynamic Topology:
    - Manages ephemeral nodes (System 2 thoughts).
    """

    def __init__(self, bus: UniversalEventBus):
        self.bus = bus
        self.interceptors: list[Interceptor] = []
        self._ephemeral_nodes: dict[str, Any] = {}

    def add_interceptor(self, interceptor: Interceptor) -> None:
        """Add an interceptor to the chain."""
        self.interceptors.append(interceptor)

    async def register_ephemeral(self, node: Any) -> None:
        """
        Register a short-lived node (e.g., a Thought Spark).

        FIXED: Now automatically subscribes the node to the event bus,
        eliminating race conditions from manual subscription.

        Args:
            node: Node instance with node_id and _handle_request method
        """
        node_id = node.node_id
        self._ephemeral_nodes[node_id] = node

        # Auto-subscribe to event bus (eliminates race condition)
        if hasattr(node, '_handle_request'):
            topic = f"node.request/node/{node_id}"
            await self.bus.subscribe(topic, node._handle_request)
            print(f"[Dispatcher] Auto-subscribed ephemeral node: {node_id}")
        else:
            print(f"[Dispatcher] Warning: Node {node_id} has no _handle_request method")

    def cleanup_ephemeral(self, node_id: str) -> None:
        """
        Cleanup resources for a node.
        Typically call this when a thought process is complete.
        """
        if node_id in self._ephemeral_nodes:
            # If the node has a cleanup method, call it
            node = self._ephemeral_nodes[node_id]
            if hasattr(node, "cleanup"):
                # We assume cleanup might be async but for now we just drop the ref
                # In a full implementation we might await it
                pass
            del self._ephemeral_nodes[node_id]

    async def dispatch(self, event: CloudEvent) -> None:
        """
        Dispatch an event through the system.
        """
        # 1. Pre-invoke Interceptors
        current_event = event
        for interceptor in self.interceptors:
            # We know current_event is not None here because we return if it becomes None
            maybe_event = await interceptor.pre_invoke(current_event)
            if maybe_event is None:
                # Blocked by interceptor
                return
            # Explicit cast for mypy
            current_event = maybe_event

        # 2. Publish to Bus (Routing & Persistence)
        import asyncio
        timeout = 30.0 # Default fallback
        if current_event.extensions and "timeout" in current_event.extensions:
            with contextlib.suppress(Exception):
                timeout = float(current_event.extensions["timeout"])

        try:
             await asyncio.wait_for(self.bus.publish(current_event), timeout=timeout)
        except TimeoutError:
             print(f"timeout dispatching event {current_event.id}")
             # We might want to raise or handle graceful failure
             # Raising allows the caller (e.g. app.run) to catch it
             raise

        # 3. Post-invoke Interceptors (in reverse order)
        for interceptor in reversed(self.interceptors):
            await interceptor.post_invoke(current_event)
