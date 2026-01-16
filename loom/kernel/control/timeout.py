"""
Standard Kernel Interceptors.
"""

from loom.kernel.control.base import Interceptor
from loom.protocol.cloudevents import CloudEvent


class TimeoutInterceptor(Interceptor):
    """
    Enforces a timeout on event processing by injecting a deadline constraint.
    The Dispatcher or Transport is responsible for respecting this constraint.
    """

    def __init__(self, default_timeout_sec: float = 30.0):
        self.default_timeout_sec = default_timeout_sec

    async def pre_invoke(self, event: CloudEvent) -> CloudEvent | None:
        # If timeout not already set in extensions, inject it
        extensions = event.extensions or {}
        if "timeout" not in extensions:
            extensions["timeout"] = self.default_timeout_sec
            event.extensions = extensions

        return event

    async def post_invoke(self, event: CloudEvent) -> None:
        pass
