import asyncio
import pytest
from typing import Any, Dict

from loom.protocol.cloudevents import CloudEvent
from loom.node.base import Node
from loom.api.main import LoomApp

class EchoNode(Node):
    async def process(self, event: CloudEvent) -> Any:
        print(f"EchoNode received: {event}")
        # Echo back the data
        data = event.data or {}
        if isinstance(data, dict):
            if "task" in data:
                return f"Echo: {data['task']}"
            elif "ping" in data:
                return "pong"
        return "ok"

class CallerNode(Node):
    async def process(self, event: CloudEvent) -> Any:
        # Test calling EchoNode
        data = event.data or {}
        if isinstance(data, dict):
             target = data.get("target")
             if target:
                # Call the target
                print(f"Caller calling {target}")
                result = await self.call(target, {"ping": True})
                return f"Caller received: {result}"
        return "no target"

@pytest.mark.asyncio
async def test_loom_app_run_rpc():
    app = LoomApp()
    echo = EchoNode(node_id="echo", dispatcher=app.dispatcher)
    
    # Allow subscriptions to settle
    await asyncio.sleep(0.1)
    
    # Test LoomApp.run -> Node
    result = await app.run("Hello", target="node/echo")
    assert result == "Echo: Hello"

@pytest.mark.asyncio
async def test_node_call_rpc():
    app = LoomApp()
    echo = EchoNode(node_id="echo", dispatcher=app.dispatcher)
    caller = CallerNode(node_id="caller", dispatcher=app.dispatcher)
    
    await asyncio.sleep(0.1)
    
    # We use app.run to trigger the caller
    # caller calls echo, then returns result
    
    # Since we need to trigger the caller, we can use app.run targeting caller
    # caller expects 'target' in data
    # LoomApp.run(task=..., target=...) puts task in data["task"].
    # We can't easily put "target" in data unless we change LoomApp.run to take extra args or pack it in task.
    # Hack: pass JSON in task? Or just use a different method.
    
    # Let's use dispatcher directly to trigger caller with correct payload
    await app.start()
    
    # But wait, we want to test 'call' return value.
    # Let's just modify the CallerNode to use hardcoded target for simplicity or derive from task
    pass # Replaced by test_node_node_rpc_flow logic mostly

class ProxyNode(Node):
    async def process(self, event: CloudEvent) -> Any:
        # Calls the target specified in 'task'
        data = event.data or {}
        if isinstance(data, dict):
             target = data.get("task")
             if target:
                 print(f"Proxy calling node/{target}")
                 response = await self.call(f"node/{target}", {"ping": True})
                 return f"Proxy got: {response}"
        return "fail"

@pytest.mark.asyncio
async def test_node_node_rpc_flow():
    app = LoomApp()
    echo = EchoNode(node_id="echo", dispatcher=app.dispatcher)
    proxy = ProxyNode(node_id="proxy", dispatcher=app.dispatcher)
    
    await asyncio.sleep(0.1)
    
    # User -> Proxy -> Echo -> Proxy -> User
    # task="echo" -> Proxy calls "node/echo" -> Echo returns "pong" -> Proxy returns "Proxy got: pong"
    result = await app.run(task="echo", target="node/proxy")
    
    assert result == "Proxy got: pong"
