"""
Depth Interceptor
"""

from loom.kernel.control.base import Interceptor
from loom.protocol.cloudevents import CloudEvent


class RecursionLimitExceededError(Exception):
    pass

class DepthInterceptor(Interceptor):
    """
    Prevents infinite fractal recursion.
    """

    def __init__(self, max_depth: int = 5):
        self.max_depth = max_depth

    async def pre_invoke(self, event: CloudEvent) -> CloudEvent | None:
        # We need to know the current depth.
        # CloudEvents 1.0 doesn't have a standard depth field.
        # We assume it is propagated in extension attribute `depth` or inside `tracestate`.

        # If it's a new request from User, depth is 0.
        # If it's a sub-request, parent should have incremented it.

        # But Interceptor is on the Sender side (Dispatcher)?
        # Yes, Dispatcher is shared or per-node.
        # If Dispatcher is centralized (LoomApp), it intercepts ALL events.

        # We check `event.extensions`.
        current_depth = int(getattr(event, "depth", 0) or 0)

        if current_depth > self.max_depth:
             raise RecursionLimitExceededError(f"Max recursion depth {self.max_depth} exceeded.")

        # When an Agent receives an event and sends a NEW event (Tool Call),
        # the Agent is responsible for correct propagation (depth+1).
        # This interceptor essentially Gates it.

        return event

    async def post_invoke(self, event: CloudEvent) -> None:
        pass
