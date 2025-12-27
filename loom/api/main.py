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
from loom.kernel.interceptors.studio import StudioInterceptor
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
        
        control_config = control_config or {}

        if "transport" in control_config and isinstance(control_config["transport"], dict):
             # Config dict provided, maybe future extensibility
             pass
        
        # Transport Selection
        # 1. Transport object passed directly
        self.transport = transport
        
        if not self.transport:
            # Config from control_config or Env
            transport_cfg = {}
            if "transport" in control_config and isinstance(control_config["transport"], dict):
                transport_cfg = control_config["transport"]
            
            import os
            # Priority: Config > Env > Default
            transport_type = transport_cfg.get("type") or os.getenv("LOOM_TRANSPORT", "memory").lower()
            
            if transport_type == "redis":
                from loom.infra.transport.redis import RedisTransport
                redis_url = transport_cfg.get("redis_url") or os.getenv("REDIS_URL", "redis://localhost:6379")
                self.transport = RedisTransport(redis_url=redis_url)
            elif transport_type == "nats":
                from loom.infra.transport.nats import NATSTransport
                nats_servers_cfg = transport_cfg.get("nats_servers")
                if nats_servers_cfg:
                     nats_servers = nats_servers_cfg if isinstance(nats_servers_cfg, list) else [nats_servers_cfg]
                else:
                     nats_servers = os.getenv("NATS_SERVERS", "nats://localhost:4222").split(",")
                self.transport = NATSTransport(servers=nats_servers)
            else:
                from loom.infra.transport.memory import InMemoryTransport
                self.transport = InMemoryTransport()
                
        self.bus = UniversalEventBus(store=store, transport=self.transport)
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
            patterns = control_config["hitl"]
            if isinstance(patterns, list):
                self.dispatcher.add_interceptor(HITLInterceptor(patterns=patterns))

        # Studio Support
        # Check env var or control_config
        studio_enabled = False
        studio_url = "ws://localhost:8765"
        
        if "studio" in control_config:
             studio_cfg = control_config["studio"]
             if isinstance(studio_cfg, dict):
                 studio_enabled = studio_cfg.get("enabled", False)
                 studio_url = studio_cfg.get("url", studio_url)
             elif isinstance(studio_cfg, bool):
                 studio_enabled = studio_cfg
        else:
             import os
             if os.getenv("LOOM_STUDIO_ENABLED", "false").lower() == "true":
                 studio_enabled = True
                 studio_url = os.getenv("LOOM_STUDIO_URL", studio_url)
                 
        if studio_enabled:
            self.dispatcher.add_interceptor(StudioInterceptor(studio_url=studio_url, enabled=True))
        
        self._started = False
        
    async def start(self):
        """Initialize async components."""
        if self._started:
            return
        
        await self.bus.connect()
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
            
            # Use timeout from event if set (injected by interceptor)
            timeout = 30.0
            if event.extensions and "timeout" in event.extensions:
                try:
                    timeout = float(event.extensions["timeout"])
                except (ValueError, TypeError):
                    pass
            
            return await asyncio.wait_for(response_future, timeout=timeout)
        except asyncio.TimeoutError:
            raise TimeoutError(f"Task targeting {target} timed out after {timeout}s")

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

    @classmethod
    def from_config(cls, config_path: str):
        """
        从 YAML 配置文件创建 LoomApp。

        Args:
            config_path: YAML 配置文件路径

        Returns:
            (app, agents, crews) 元组

        Example:
            app, agents, crews = LoomApp.from_config("loom.yaml")
            result = await app.run("任务", target="agent-name")
        """
        from loom.config.loader import ConfigLoader
        return ConfigLoader.from_file(config_path)
