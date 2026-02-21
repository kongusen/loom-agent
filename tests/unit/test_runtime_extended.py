"""Coverage-boost tests for runtime/core.py extended paths."""

from loom.runtime.core import Runtime
from loom.types import AgentNode, CapabilityProfile, Skill, TaskAd
from tests.conftest import MockLLMProvider


class TestRuntimeExtended:
    def test_load_skill(self):
        rt = Runtime(MockLLMProvider())
        skill = Skill(name="code", instructions="help with code")
        node = rt.load_skill(skill)
        assert isinstance(node, AgentNode)
        assert node.capabilities.scores.get("code") == 0.7

    def test_build_context_for_existing(self):
        rt = Runtime(MockLLMProvider())
        node = rt.add_agent(capabilities=CapabilityProfile(scores={"code": 0.8}))
        orch = rt.build_context_for(node.id)
        assert orch is not None

    def test_build_context_for_missing(self):
        rt = Runtime(MockLLMProvider())
        orch = rt.build_context_for("nonexistent")
        assert orch is not None

    def test_get_memory(self):
        rt = Runtime(MockLLMProvider())
        assert rt.get_memory() is not None

    async def test_execute_single_error(self):
        rt = Runtime(MockLLMProvider(["done"]))
        node = rt.add_agent(capabilities=CapabilityProfile(scores={"code": 0.8}))

        async def fail_add(msg):
            raise RuntimeError("memory broken")

        node.agent.memory.add_message = fail_add
        result = await rt.submit(TaskAd(domain="code", description="test"))
        assert "Error" in result

    async def test_handle_delegate(self):
        rt = Runtime(MockLLMProvider(["delegated result"]))
        rt.add_agent(capabilities=CapabilityProfile(scores={"code": 0.8}))
        result = await rt._handle_delegate("do something", "code")
        assert isinstance(result, str)
