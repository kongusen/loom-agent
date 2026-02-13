"""
Tests for agent handlers: builder.py, tool_handler.py, planner.py, delegator.py
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

from loom.agent.builder import AgentBuilder
from loom.agent.delegator import DelegatorMixin, create_delegate_task_tool
from loom.agent.planner import PlannerMixin, create_plan_tool
from loom.agent.tool_handler import ToolHandlerMixin
from loom.exceptions import PermissionDenied

# ==================== AgentBuilder ====================


class TestAgentBuilder:
    def _make_builder(self):
        llm = MagicMock()
        return AgentBuilder(llm)

    def test_init(self):
        llm = MagicMock()
        b = AgentBuilder(llm)
        assert b.llm is llm
        assert b.config == {}

    def test_with_system_prompt(self):
        b = self._make_builder().with_system_prompt("You are helpful")
        assert b.config["system_prompt"] == "You are helpful"

    def test_with_tools(self):
        tools = [{"type": "function", "function": {"name": "t"}}]
        b = self._make_builder().with_tools(tools)
        assert b.config["tools"] == tools

    def test_with_memory(self):
        b = self._make_builder().with_memory(8000)
        assert b.config["max_context_tokens"] == 8000

    def test_with_context_window_alias(self):
        b = self._make_builder().with_context_window(6000)
        assert b.config["max_context_tokens"] == 6000

    def test_with_memory_config(self):
        cfg = {"l1_token_budget": 4000}
        b = self._make_builder().with_memory_config(cfg)
        assert b.config["memory_config"] == cfg

    def test_with_context_budget(self):
        b = self._make_builder().with_context_budget({"total": 10000})
        assert b.config["context_budget_config"] == {"total": 10000}

    def test_with_context_config(self):
        b = self._make_builder().with_context_config({"max_tokens": 5000})
        assert b.config["context_config"] == {"max_tokens": 5000}

    def test_with_knowledge_base(self):
        kb = MagicMock()
        b = self._make_builder().with_knowledge_base(kb)
        assert b.config["knowledge_base"] is kb

    def test_with_event_bus(self):
        bus = MagicMock()
        b = self._make_builder().with_event_bus(bus)
        assert b.config["event_bus"] is bus

    def test_with_iterations(self):
        b = self._make_builder().with_iterations(20)
        assert b.config["max_iterations"] == 20

    def test_with_session_isolation(self):
        b = self._make_builder().with_session_isolation("strict")
        assert b.config["session_isolation"] == "strict"

    def test_with_compaction(self):
        b = self._make_builder().with_compaction({"level": "aggressive"})
        assert b.config["compaction_config"] == {"level": "aggressive"}

    def test_with_tool_policy(self):
        policy = MagicMock()
        b = self._make_builder().with_tool_policy(policy)
        assert b.config["tool_policy"] is policy

    def test_with_skills(self):
        b = self._make_builder().with_skills(["code_review", "analysis"])
        assert b.config["skills"] == ["code_review", "analysis"]

    def test_with_skills_dir(self):
        b = self._make_builder().with_skills_dir("/path/to/skills")
        assert b.config["skills_dir"] == "/path/to/skills"

    def test_with_skill_loaders(self):
        loaders = [MagicMock()]
        b = self._make_builder().with_skill_loaders(loaders)
        assert b.config["skill_loaders"] == loaders

    def test_with_tool_config(self):
        b = self._make_builder().with_tool_config({"sandbox": True})
        assert b.config["tool_config"] == {"sandbox": True}

    def test_with_capabilities(self):
        caps = MagicMock()
        b = self._make_builder().with_capabilities(caps)
        assert b.config["capabilities"] is caps

    def test_with_knowledge_config(self):
        b = self._make_builder().with_knowledge_config(max_items=5, relevance_threshold=0.8)
        assert b.config["knowledge_max_items"] == 5
        assert b.config["knowledge_relevance_threshold"] == 0.8

    def test_with_done_tool(self):
        b = self._make_builder().with_done_tool(False)
        assert b.config["require_done_tool"] is False

    def test_chaining(self):
        b = (
            self._make_builder()
            .with_system_prompt("prompt")
            .with_iterations(10)
            .with_memory(4000)
        )
        assert b.config["system_prompt"] == "prompt"
        assert b.config["max_iterations"] == 10
        assert b.config["max_context_tokens"] == 4000

    def test_build(self):
        with patch("loom.agent.core.Agent.create") as mock_create:
            mock_create.return_value = MagicMock()
            llm = MagicMock()
            b = AgentBuilder(llm)
            b.config["system_prompt"] = "test"
            b.build()
            mock_create.assert_called_once_with(llm, system_prompt="test")


# ==================== ToolHandlerMixin ====================


class TestToolHandlerGetAvailableTools:
    def _make_handler(self, **overrides):
        handler = ToolHandlerMixin()
        handler.tools = overrides.get("tools", [])
        handler.all_tools = overrides.get("all_tools", [])
        handler.tool_registry = overrides.get("tool_registry")
        handler.sandbox_manager = overrides.get("sandbox_manager")
        handler.tool_policy = overrides.get("tool_policy")
        handler.memory = overrides.get("memory")
        handler.event_bus = overrides.get("event_bus")
        handler._dynamic_tool_executor = overrides.get("_dynamic_tool_executor")
        handler._pending_tool_callables = []
        config = MagicMock()
        config.extra_tools = overrides.get("extra_tools", [])
        config.disabled_tools = overrides.get("disabled_tools", [])
        handler.config = config
        return handler

    def test_empty(self):
        h = self._make_handler()
        assert h._get_available_tools() == []

    def test_base_tools(self):
        tools = [
            {"type": "function", "function": {"name": "bash", "description": "Run"}},
            {"type": "function", "function": {"name": "search", "description": "Find"}},
        ]
        h = self._make_handler(tools=tools)
        result = h._get_available_tools()
        assert len(result) == 2

    def test_dedup_tools(self):
        tool = {"type": "function", "function": {"name": "bash"}}
        h = self._make_handler(tools=[tool, tool])
        result = h._get_available_tools()
        assert len(result) == 1

    def test_skips_non_dict(self):
        h = self._make_handler(tools=["not_a_dict", 42])
        result = h._get_available_tools()
        assert result == []

    def test_extra_tools_from_registry(self):
        defn = MagicMock()
        defn.name = "extra"
        defn.description = "Extra tool"
        defn.input_schema = {}
        registry = MagicMock()
        registry.get_definition.return_value = defn
        h = self._make_handler(tool_registry=registry, extra_tools=["extra"])
        result = h._get_available_tools()
        assert len(result) == 1
        assert result[0]["function"]["name"] == "extra"

    def test_sandbox_tools(self):
        mcp_def = MagicMock()
        mcp_def.name = "sandbox_tool"
        mcp_def.description = "Sandbox"
        mcp_def.input_schema = {}
        sandbox = MagicMock()
        sandbox.list_tools.return_value = [mcp_def]
        h = self._make_handler(sandbox_manager=sandbox)
        result = h._get_available_tools()
        assert len(result) == 1

    def test_disabled_tools_filtered(self):
        tools = [
            {"type": "function", "function": {"name": "bash"}},
            {"type": "function", "function": {"name": "search"}},
        ]
        h = self._make_handler(tools=tools, disabled_tools=["bash"])
        result = h._get_available_tools()
        assert len(result) == 1
        assert result[0]["function"]["name"] == "search"


class TestToolHandlerExecuteSingleTool:
    def _make_handler(self, **overrides):
        handler = ToolHandlerMixin()
        handler.tools = []
        handler.all_tools = []
        handler.tool_registry = overrides.get("tool_registry")
        handler.sandbox_manager = overrides.get("sandbox_manager")
        handler.tool_policy = overrides.get("tool_policy")
        handler.memory = overrides.get("memory")
        handler.event_bus = overrides.get("event_bus")
        handler._dynamic_tool_executor = overrides.get("_dynamic_tool_executor")
        handler._pending_tool_callables = []
        handler.config = MagicMock()
        handler.config.extra_tools = []
        handler.config.disabled_tools = []
        return handler

    async def test_permission_denied(self):
        policy = MagicMock()
        policy.is_allowed.return_value = False
        policy.get_denial_reason.return_value = "blocked"
        h = self._make_handler(tool_policy=policy)
        try:
            await h._execute_single_tool("bash", {"cmd": "ls"})
            raise AssertionError("Should have raised")
        except PermissionDenied as e:
            assert e.tool_name == "bash"

    async def test_permission_denied_with_str_args(self):
        policy = MagicMock()
        policy.is_allowed.return_value = False
        policy.get_denial_reason.return_value = "no"
        h = self._make_handler(tool_policy=policy)
        try:
            await h._execute_single_tool("bash", '{"cmd": "ls"}')
            raise AssertionError("Should have raised")
        except PermissionDenied:
            pass

    async def test_invalid_json_args(self):
        h = self._make_handler()
        result = await h._execute_single_tool("some_tool", "not json{{{")
        # tool_registry is None → returns error
        assert "错误" in result

    async def test_registry_tool_execution(self):
        func = AsyncMock(return_value="result_data")
        registry = MagicMock()
        registry.get_callable.return_value = func
        h = self._make_handler(tool_registry=registry)
        result = await h._execute_single_tool("my_tool", {"arg": "val"})
        assert result == "result_data"

    async def test_registry_tool_not_found(self):
        registry = MagicMock()
        registry.get_callable.return_value = None
        h = self._make_handler(tool_registry=registry)
        result = await h._execute_single_tool("missing", {})
        assert "未找到" in result

    async def test_no_registry(self):
        h = self._make_handler(tool_registry=None)
        result = await h._execute_single_tool("tool", {})
        assert "未找到" in result or "未初始化" in result

    async def test_sandbox_tool(self):
        sandbox = MagicMock()
        sandbox.__contains__ = MagicMock(return_value=True)
        sandbox.execute_tool = AsyncMock(return_value="sandbox_result")
        h = self._make_handler(sandbox_manager=sandbox)
        result = await h._execute_single_tool("sandbox_tool", {"x": 1})
        assert result == "sandbox_result"

    async def test_sandbox_tool_error(self):
        sandbox = MagicMock()
        sandbox.__contains__ = MagicMock(return_value=True)
        sandbox.execute_tool = AsyncMock(side_effect=RuntimeError("boom"))
        h = self._make_handler(sandbox_manager=sandbox)
        result = await h._execute_single_tool("sandbox_tool", {})
        assert "沙盒工具执行失败" in result

    async def test_unified_browse_memory(self):
        memory = MagicMock()
        h = self._make_handler(memory=memory)
        with patch("loom.tools.memory.browse.execute_unified_browse_tool", new_callable=AsyncMock) as mock_browse:
            mock_browse.return_value = {"items": []}
            result = await h._execute_single_tool("browse_memory", {"action": "list"})
            data = json.loads(result)
            assert data == {"items": []}

    async def test_unified_tool_no_resource(self):
        h = self._make_handler(memory=None, event_bus=None)
        result = await h._execute_single_tool("browse_memory", {})
        assert "未初始化" in result

    async def test_dynamic_tool_execution(self):
        executor = MagicMock()
        executor.created_tools = {"custom_tool": True}
        executor.execute_tool = AsyncMock(return_value="dynamic_result")
        h = self._make_handler(_dynamic_tool_executor=executor)
        result = await h._execute_single_tool("custom_tool", {"a": 1})
        assert result == "dynamic_result"

    async def test_registry_tool_exception(self):
        func = AsyncMock(side_effect=ValueError("bad input"))
        registry = MagicMock()
        registry.get_callable.return_value = func
        h = self._make_handler(tool_registry=registry)
        result = await h._execute_single_tool("my_tool", {})
        assert "工具执行失败" in result


# ==================== create_plan_tool / create_delegate_task_tool ====================


class TestMetaToolCreation:
    def test_create_plan_tool(self):
        tool = create_plan_tool()
        assert tool["type"] == "function"
        assert tool["function"]["name"] == "create_plan"
        assert "goal" in tool["function"]["parameters"]["properties"]
        assert "steps" in tool["function"]["parameters"]["properties"]

    def test_create_delegate_task_tool(self):
        tool = create_delegate_task_tool()
        assert tool["type"] == "function"
        assert tool["function"]["name"] == "delegate_task"
        assert "subtask_description" in tool["function"]["parameters"]["properties"]


# ==================== PlannerMixin ====================


class TestPlannerMixin:
    def test_build_plan_summary(self):
        planner = PlannerMixin()
        summary = planner._build_plan_summary(
            "Build feature",
            "Need modular approach",
            ["Step 1", "Step 2"],
        )
        assert "Build feature" in summary
        assert "Need modular approach" in summary
        assert "Step 1" in summary
        assert "Step 2" in summary
        assert "2" in summary  # step count

    def test_build_plan_summary_no_reasoning(self):
        planner = PlannerMixin()
        summary = planner._build_plan_summary("Goal", "", ["A", "B"])
        assert "Goal" in summary
        assert "Reasoning" not in summary


# ==================== DelegatorMixin ====================


class TestDelegatorMixin:
    async def test_ensure_shared_task_context(self):
        delegator = DelegatorMixin()
        delegator.memory = MagicMock()
        delegator.memory.add_context = AsyncMock()
        from loom.runtime import Task
        task = Task(
            taskId="t1",
            action="execute",
            parameters={"content": "Do something"},
        )
        result = await delegator._ensure_shared_task_context(task)
        assert result == "task_context:t1"
        delegator.memory.add_context.assert_called_once()

    async def test_ensure_shared_task_context_empty(self):
        delegator = DelegatorMixin()
        delegator.memory = MagicMock()
        delegator.memory.add_context = AsyncMock()
        from loom.runtime import Task
        task = Task(
            taskId="t1",
            action="execute",
            parameters={},
        )
        result = await delegator._ensure_shared_task_context(task)
        assert result is None

    async def test_sync_memory_from_child_noop(self):
        delegator = DelegatorMixin()
        child = MagicMock()
        # Should not raise - it's a no-op in new architecture
        await delegator._sync_memory_from_child(child)
