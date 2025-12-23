"""
Event Dispatcher (Kernel)
"""

from typing import List, Any

from loom.protocol.cloudevents import CloudEvent
from loom.kernel.bus import UniversalEventBus
from loom.kernel.base_interceptor import Interceptor

class Dispatcher:
    """
    Central dispatch mechanism.
    1. Runs Interceptor Chain (Pre-invoke).
    2. Publishes to Bus.
    3. Runs Interceptor Chain (Post-invoke).
    """
    
    def __init__(self, bus: UniversalEventBus):
        self.bus = bus
        self.interceptors: List[Interceptor] = []
        
    def add_interceptor(self, interceptor: Interceptor) -> None:
        """Add an interceptor to the chain."""
        self.interceptors.append(interceptor)
        
    async def dispatch(self, event: CloudEvent) -> None:
        """
        Dispatch an event through the system.
        """
        # 1. Pre-invoke Interceptors
        current_event = event
        for interceptor in self.interceptors:
            current_event = await interceptor.pre_invoke(current_event)
            if current_event is None:
                # Blocked by interceptor
                return

        # 2. Publish to Bus (Routing & Persistence)
        import asyncio
        timeout = 30.0 # Default fallback
        if current_event.extensions and "timeout" in current_event.extensions:
            try:
                timeout = float(current_event.extensions["timeout"])
            except:
                pass
                
        try:
             await asyncio.wait_for(self.bus.publish(current_event), timeout=timeout)
        except asyncio.TimeoutError:
             print(f"timeout dispatching event {current_event.id}")
             # We might want to raise or handle graceful failure
             # Raising allows the caller (e.g. app.run) to catch it
             raise
        
        # 3. Post-invoke Interceptors (in reverse order)
        for interceptor in reversed(self.interceptors):
            await interceptor.post_invoke(current_event)
