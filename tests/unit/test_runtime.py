"""Unit tests for runtime module."""

from loom.runtime.core import Runtime
from loom.types import AgentNode, CapabilityProfile, TaskAd
from tests.conftest import MockLLMProvider


class TestRuntime:
    def test_add_agent(self):
        rt = Runtime(MockLLMProvider())
        node = rt.add_agent()
        assert isinstance(node, AgentNode)
        assert len(rt.cluster.nodes) == 1

    def test_add_agent_with_capabilities(self):
        rt = Runtime(MockLLMProvider())
        caps = CapabilityProfile(scores={"code": 0.9})
        node = rt.add_agent(capabilities=caps)
        assert node.capabilities.scores["code"] == 0.9

    async def test_submit_no_agents(self):
        rt = Runtime(MockLLMProvider())
        result = await rt.submit(TaskAd(domain="code", description="test"))
        assert "no available agents" in result

    async def test_submit_single_agent(self):
        rt = Runtime(MockLLMProvider(["done"]))
        rt.add_agent(capabilities=CapabilityProfile(scores={"code": 0.8}))
        result = await rt.submit(TaskAd(domain="code", description="test"))
        assert isinstance(result, str)

    def test_health_check_empty(self):
        rt = Runtime(MockLLMProvider())
        assert rt.health_check() == []

    def test_dispose(self):
        rt = Runtime(MockLLMProvider())
        rt.dispose()
        assert rt._health_timer is None

    def test_create_node(self):
        rt = Runtime(MockLLMProvider())
        rt.create_node()
        assert len(rt.cluster.nodes) == 1
