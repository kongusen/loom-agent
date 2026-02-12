"""
Tests for agent/factory.py and agent/tool_router.py
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from loom.agent.factory import AgentFactory
from loom.agent.tool_router import ToolRouter
from loom.config.tool import ToolConfig
from loom.exceptions import PermissionDenied


# ============ AgentFactory._normalize_tool_config ============


class TestNormalizeToolConfig:
    def test_none_config_passthrough(self):
        tools, skills, sd, sl = AgentFactory._normalize_tool_config(
            None, ["t1"], ["s1"], "/dir", ["loader"]
        )
        assert tools == ["t1"]
        assert skills == ["s1"]
        assert sd == "/dir"
        assert sl == ["loader"]

    def test_dict_config_converted(self):
        cfg = {"tools": [{"type": "function", "function": {"name": "x"}}]}
        tools, skills, sd, sl = AgentFactory._normalize_tool_config(
            cfg, None, None, None, None
        )
        assert tools == [{"type": "function", "function": {"name": "x"}}]

    def test_tool_config_object(self):
        tc = ToolConfig(skills=["skill_a"])
        tools, skills, sd, sl = AgentFactory._normalize_tool_config(
            tc, None, None, None, None
        )
        assert skills == ["skill_a"]

    def test_explicit_params_take_precedence(self):
        tc = ToolConfig(tools=[{"name": "from_config"}], skills=["from_config"])
        tools, skills, sd, sl = AgentFactory._normalize_tool_config(
            tc, [{"name": "explicit"}], ["explicit_skill"], None, None
        )
        assert tools == [{"name": "explicit"}]
        assert skills == ["explicit_skill"]

    def test_invalid_type_raises(self):
        with pytest.raises(TypeError):
            AgentFactory._normalize_tool_config(42, None, None, None, None)


# ============ AgentFactory._extract_capabilities ============


class TestExtractCapabilities:
    def test_none_capabilities(self):
        kwargs = {}
        AgentFactory._extract_capabilities(None, kwargs)
        assert kwargs == {}

    def test_extracts_tool_manager(self):
        caps = MagicMock()
        caps.tool_manager = "tm"
        caps.skill_registry = "sr"
        caps.skill_activator = "sa"
        kwargs = {}
        AgentFactory._extract_capabilities(caps, kwargs)
        assert kwargs["sandbox_manager"] == "tm"
        assert kwargs["skill_registry"] == "sr"
        assert kwargs["skill_activator"] == "sa"

    def test_does_not_overwrite_existing(self):
        caps = MagicMock()
        caps.tool_manager = "new_tm"
        kwargs = {"sandbox_manager": "existing"}
        AgentFactory._extract_capabilities(caps, kwargs)
        assert kwargs["sandbox_manager"] == "existing"


# ============ AgentFactory._normalize_context_config ============


class TestNormalizeContextConfig:
    def test_none_config_passthrough(self):
        result = AgentFactory._normalize_context_config(
            None, "mem", "budget", "comp", "strict"
        )
        assert result == ("mem", "budget", "comp", "strict")

    def test_invalid_type_raises(self):
        with pytest.raises(TypeError):
            AgentFactory._normalize_context_config(42, None, None, None, None)


# ============ AgentFactory._resolve_node_id ============


class TestResolveNodeId:
    def test_explicit_node_id(self):
        assert AgentFactory._resolve_node_id("my-id", "parent", "role") == "my-id"

    def test_parent_and_role(self):
        result = AgentFactory._resolve_node_id(None, "parent", "worker")
        assert result == "parent:worker"

    def test_parent_only(self):
        result = AgentFactory._resolve_node_id(None, "parent", None)
        assert result.startswith("parent:")
        assert len(result) > len("parent:")

    def test_role_only(self):
        result = AgentFactory._resolve_node_id(None, None, "worker")
        assert result.startswith("worker:")

    def test_all_none_generates_uuid(self):
        result = AgentFactory._resolve_node_id(None, None, None)
        assert len(result) == 36  # UUID format


# ============ AgentFactory._setup_sandbox ============


class TestSetupSandbox:
    def test_no_callables_no_change(self):
        tools = [{"type": "function"}]
        result = AgentFactory._setup_sandbox(tools, MagicMock(), {})
        assert result == [{"type": "function"}]

    def test_none_tools(self):
        result = AgentFactory._setup_sandbox(None, MagicMock(), {})
        assert result is None

    def test_callables_create_sandbox(self):
        def my_tool():
            pass

        tools = [{"type": "function"}, my_tool]
        kwargs = {}
        result = AgentFactory._setup_sandbox(tools, MagicMock(), kwargs)
        # Callables should be extracted, only dicts remain
        assert result == [{"type": "function"}]
        assert "sandbox_manager" in kwargs
        assert kwargs["_pending_tool_callables"] == [my_tool]

    def test_existing_sandbox_manager_not_overwritten(self):
        def my_tool():
            pass

        kwargs = {"sandbox_manager": "existing"}
        tools = [my_tool]
        result = AgentFactory._setup_sandbox(tools, MagicMock(), kwargs)
        assert kwargs["sandbox_manager"] == "existing"


# ============ AgentFactory._setup_skills ============


class TestSetupSkills:
    def test_none_skills(self):
        kwargs = {}
        AgentFactory._setup_skills(None, kwargs)
        assert "skill_registry" not in kwargs

    def test_skills_creates_config(self):
        kwargs = {}
        AgentFactory._setup_skills(["skill_a", "skill_b"], kwargs)
        assert "skill_registry" in kwargs
        assert "config" in kwargs
        assert kwargs["config"].enabled_skills == {"skill_a", "skill_b"}

    def test_skills_updates_existing_config(self):
        from loom.config.agent import AgentConfig

        existing_config = AgentConfig(enabled_skills=set())
        kwargs = {"config": existing_config}
        AgentFactory._setup_skills(["new_skill"], kwargs)
        assert existing_config.enabled_skills == {"new_skill"}


# ============ ToolRouter._parse_args ============


class TestToolRouterParseArgs:
    def test_dict_passthrough(self):
        assert ToolRouter._parse_args({"key": "val"}) == {"key": "val"}

    def test_json_string(self):
        assert ToolRouter._parse_args('{"key": "val"}') == {"key": "val"}

    def test_invalid_json_string(self):
        assert ToolRouter._parse_args("not json") == {}

    def test_other_type(self):
        assert ToolRouter._parse_args(42) == {}


# ============ ToolRouter.route ============


class TestToolRouterRoute:
    def _make_agent(self):
        agent = MagicMock()
        agent.tool_policy = None
        agent._dynamic_tool_executor = None
        agent.sandbox_manager = None
        agent.tool_registry = MagicMock()
        agent.memory = None
        agent.event_bus = None
        agent._metrics = MagicMock()
        agent._tracer = MagicMock()
        agent._search_executor = None
        return agent

    async def test_permission_denied(self):
        agent = self._make_agent()
        policy = MagicMock()
        policy.is_allowed.return_value = False
        policy.get_denial_reason.return_value = "blocked"
        agent.tool_policy = policy

        router = ToolRouter(agent)
        with pytest.raises(PermissionDenied):
            await router.route("dangerous_tool", {})

    async def test_registry_tool(self):
        agent = self._make_agent()
        agent.tool_registry.get_callable.return_value = AsyncMock(return_value="result")

        router = ToolRouter(agent)
        result = await router.route("my_tool", {"arg": "val"})
        assert result == "result"

    async def test_registry_tool_not_found(self):
        agent = self._make_agent()
        agent.tool_registry.get_callable.return_value = None

        router = ToolRouter(agent)
        result = await router.route("missing_tool", {})
        assert "未找到" in result

    async def test_registry_tool_error(self):
        agent = self._make_agent()
        agent.tool_registry.get_callable.return_value = AsyncMock(
            side_effect=RuntimeError("boom")
        )

        router = ToolRouter(agent)
        result = await router.route("bad_tool", {})
        assert "失败" in result

    async def test_no_registry(self):
        agent = self._make_agent()
        agent.tool_registry = None

        router = ToolRouter(agent)
        result = await router.route("any_tool", {})
        assert "未找到" in result

    async def test_sandbox_tool(self):
        agent = self._make_agent()
        agent.sandbox_manager = MagicMock()
        agent.sandbox_manager.__contains__ = MagicMock(return_value=True)
        agent.sandbox_manager.execute_tool = AsyncMock(return_value="sandbox_result")

        router = ToolRouter(agent)
        result = await router.route("sandboxed", {"x": 1})
        assert result == "sandbox_result"

    async def test_unified_browse_memory(self):
        agent = self._make_agent()
        agent.memory = MagicMock()

        router = ToolRouter(agent)
        with patch(
            "loom.agent.tool_router.execute_unified_browse_tool",
            new_callable=AsyncMock,
            return_value={"action": "list"},
        ):
            result = await router.route("browse_memory", {"action": "list"})
            parsed = json.loads(result)
            assert parsed["action"] == "list"

    async def test_unified_tool_no_resource(self):
        agent = self._make_agent()
        agent.memory = None

        router = ToolRouter(agent)
        result = await router.route("browse_memory", {"action": "list"})
        assert "未初始化" in result

    async def test_create_tool_dynamic(self):
        agent = self._make_agent()
        executor = MagicMock()
        executor.create_tool = AsyncMock(return_value="created")
        executor.created_tools = {}
        agent._dynamic_tool_executor = executor
        agent._build_tool_list = MagicMock(return_value=[])

        router = ToolRouter(agent)
        result = await router.route(
            "create_tool",
            {"tool_name": "new", "description": "d", "parameters": {}, "implementation": "pass"},
        )
        assert result == "created"

    async def test_dynamic_tool_execution(self):
        agent = self._make_agent()
        executor = MagicMock()
        executor.created_tools = {"custom_tool": True}
        executor.execute_tool = AsyncMock(return_value="dynamic_result")
        agent._dynamic_tool_executor = executor

        router = ToolRouter(agent)
        result = await router.route("custom_tool", {"arg": 1})
        assert result == "dynamic_result"
