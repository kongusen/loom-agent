"""
Loom SDK: Main Application
"""

import asyncio
from typing import Callable, Any, Optional, Dict
from uuid import uuid4

from loom.kernel.bus import UniversalEventBus
from loom.kernel.state import StateStore
from loom.kernel.dispatcher import Dispatcher
from loom.kernel.interceptors import TracingInterceptor
from loom.kernel.interceptors.budget import BudgetInterceptor
from loom.kernel.interceptors.depth import DepthInterceptor
from loom.kernel.interceptors.hitl import HITLInterceptor
from loom.protocol.cloudevents import CloudEvent
from loom.interfaces.store import EventStore
from loom.node.base import Node

from loom.interfaces.transport import Transport

class LoomApp:
    """
    The High-Level Application Object.
    
    Usage:
        app = LoomApp(control_config={"budget": 5000})
        app.add_node(agent)
        app.run("Do something", target="agent_1")
    """
    
    def __init__(self, 
                 store: Optional[EventStore] = None, 
                 transport: Optional[Transport] = None,
                 control_config: Optional[Dict[str, Any]] = None):
        # Initialize Kernel
        self.bus = UniversalEventBus(store=store, transport=transport)
        self.state_store = StateStore()
        self.dispatcher = Dispatcher(self.bus)
        
        # Default Interceptors
        self.dispatcher.add_interceptor(TracingInterceptor())
        
        # Configured Controls
        control_config = control_config or {}
        
        if "budget" in control_config:
            cfg = control_config["budget"]
            max_tokens = cfg["max_tokens"] if isinstance(cfg, dict) else cfg
            self.dispatcher.add_interceptor(BudgetInterceptor(max_tokens=max_tokens))
            
        if "depth" in control_config:
            cfg = control_config["depth"]
            max_depth = cfg["max_depth"] if isinstance(cfg, dict) else cfg
            self.dispatcher.add_interceptor(DepthInterceptor(max_depth=max_depth))
            
        if "hitl" in control_config:
            # hitl expects a list of patterns
            patterns = control_config["hitl"]
            if isinstance(patterns, list):
                self.dispatcher.add_interceptor(HITLInterceptor(patterns=patterns))
        
        self._started = False
        
    async def start(self):
        """Initialize async components."""
        if self._started:
            return
        await self.bus.subscribe("state.patch/*", self.state_store.apply_event)
        self._started = True

    def add_node(self, node: Node):
        """Register a node with the app."""
        # Nodes auto-subscribe in their __init__ using the dispatcher.
        # We assume the node has already been initialized with THIS app's dispatcher.
        # Or we can provide a helper here if Node wasn't initialized?
        # Better: The Factory helper uses app.dispatcher.
        pass

    async def run(self, task: str, target: str) -> Any:
        """
        Run a single task targeting a specific node and return the result.
        """
        await self.start()
        
        request_id = str(uuid4())
        event = CloudEvent.create(
            source="/user/sdk",
            type="node.request",
            data={"task": task},
            subject=target
        )
        event.id = request_id
        
        # Subscribe to response
        response_future = asyncio.Future()
        
        async def handle_response(event: CloudEvent):
            if event.data and event.data.get("request_id") == request_id:
                if not response_future.done():
                    if event.type == "node.error":
                         response_future.set_exception(Exception(event.data.get("error", "Unknown Error")))
                    else:
                         response_future.set_result(event.data.get("result"))

        target_topic = f"node.response/{target.strip('/')}"
        
        # We need to subscribe to the response
        await self.bus.subscribe(target_topic, handle_response)
        
        try:
            await self.dispatcher.dispatch(event)
            return await asyncio.wait_for(response_future, timeout=30.0)
        except asyncio.TimeoutError:
            raise TimeoutError(f"Task targeting {target} timed out after 30s")

    def on(self, event_type: str, handler: Callable[[CloudEvent], Any]):
        """
        Add an observability hook.
        """
        async def _wrapper(event: CloudEvent):
            if event_type == "*" or event.type == event_type:
                res = handler(event)
                if asyncio.iscoroutine(res):
                    await res
        
        # We subscribe to the bus
        # This requires an async context to call 'await bus.subscribe'.
        # We can schedule it.
        asyncio.create_task(self.bus.subscribe(f"{event_type}/*" if event_type != "*" else "*", _wrapper))

