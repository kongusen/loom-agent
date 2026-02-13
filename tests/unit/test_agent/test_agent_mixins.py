"""
Tests for agent mixins: ExecutorMixin, PlannerMixin, SkillHandlerMixin, DelegatorMixin

Covers uncovered methods in executor.py, planner.py, skill_handler.py, delegator.py.
"""

import sys
import types
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from loom.agent.delegator import create_delegate_task_tool
from loom.agent.executor import ExecutorMixin
from loom.agent.planner import PlannerMixin, create_plan_tool
from loom.agent.skill_handler import SkillHandlerMixin
from loom.runtime import Task

# ==================== ExecutorMixin ====================


class TestExecutorMixinGetToolEphemeralCount:
    def _make_mixin(self, config=None):
        mixin = ExecutorMixin.__new__(ExecutorMixin)
        mixin._ephemeral_tool_config = config or {}
        return mixin

    def test_returns_count_for_configured_tool(self):
        mixin = self._make_mixin({"search": 3, "browse": 1})
        assert mixin._get_tool_ephemeral_count("search") == 3
        assert mixin._get_tool_ephemeral_count("browse") == 1

    def test_returns_zero_for_unconfigured_tool(self):
        mixin = self._make_mixin({"search": 3})
        assert mixin._get_tool_ephemeral_count("unknown_tool") == 0

    def test_returns_zero_when_config_empty(self):
        mixin = self._make_mixin({})
        assert mixin._get_tool_ephemeral_count("anything") == 0


class TestExecutorMixinFilterEphemeralMessages:
    def _make_mixin(self, config=None):
        mixin = ExecutorMixin.__new__(ExecutorMixin)
        mixin._ephemeral_tool_config = config or {}
        return mixin

    def test_empty_config_returns_messages_unchanged(self):
        mixin = self._make_mixin({})
        messages = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
        ]
        result = mixin._filter_ephemeral_messages(messages)
        assert result == messages

    def test_no_tool_calls_returns_messages_unchanged(self):
        mixin = self._make_mixin({"search": 1})
        messages = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
        ]
        result = mixin._filter_ephemeral_messages(messages)
        assert result == messages

    def test_filters_old_ephemeral_keeps_recent(self):
        """With keep_count=1, only the most recent call is kept."""
        mixin = self._make_mixin({"search": 1})
        messages = [
            {"role": "assistant", "tool_calls": [{"function": {"name": "search"}}]},
            {"role": "tool", "content": "result1"},
            {"role": "assistant", "tool_calls": [{"function": {"name": "search"}}]},
            {"role": "tool", "content": "result2"},
        ]
        result = mixin._filter_ephemeral_messages(messages)
        # First assistant+tool pair (indices 0,1) removed; second pair (indices 2,3) kept
        assert len(result) == 2
        assert result[0]["tool_calls"][0]["function"]["name"] == "search"
        assert result[1]["content"] == "result2"

    def test_keeps_all_when_within_limit(self):
        """When call count <= keep_count, nothing is removed."""
        mixin = self._make_mixin({"search": 5})
        messages = [
            {"role": "assistant", "tool_calls": [{"function": {"name": "search"}}]},
            {"role": "tool", "content": "result1"},
            {"role": "assistant", "tool_calls": [{"function": {"name": "search"}}]},
            {"role": "tool", "content": "result2"},
        ]
        result = mixin._filter_ephemeral_messages(messages)
        assert len(result) == 4

    def test_handles_tool_response_removal(self):
        """Tool response message immediately after assistant is also removed."""
        mixin = self._make_mixin({"search": 1})
        messages = [
            {"role": "user", "content": "query"},
            {"role": "assistant", "tool_calls": [{"function": {"name": "search"}}]},
            {"role": "tool", "content": "old_result"},
            {"role": "assistant", "tool_calls": [{"function": {"name": "search"}}]},
            {"role": "tool", "content": "new_result"},
        ]
        result = mixin._filter_ephemeral_messages(messages)
        # user msg kept, old assistant+tool removed, new assistant+tool kept
        assert len(result) == 3
        assert result[0]["role"] == "user"
        assert result[1]["role"] == "assistant"
        assert result[2]["content"] == "new_result"

    def test_non_ephemeral_tools_unaffected(self):
        """Messages for tools not in ephemeral config are never removed."""
        mixin = self._make_mixin({"search": 1})
        messages = [
            {"role": "assistant", "tool_calls": [{"function": {"name": "calculator"}}]},
            {"role": "tool", "content": "42"},
            {"role": "assistant", "tool_calls": [{"function": {"name": "search"}}]},
            {"role": "tool", "content": "result"},
        ]
        result = mixin._filter_ephemeral_messages(messages)
        assert len(result) == 4

    def test_multiple_ephemeral_tools(self):
        """Each ephemeral tool is tracked independently."""
        mixin = self._make_mixin({"search": 1, "browse": 1})
        messages = [
            {"role": "assistant", "tool_calls": [{"function": {"name": "search"}}]},
            {"role": "tool", "content": "search_old"},
            {"role": "assistant", "tool_calls": [{"function": {"name": "browse"}}]},
            {"role": "tool", "content": "browse_old"},
            {"role": "assistant", "tool_calls": [{"function": {"name": "search"}}]},
            {"role": "tool", "content": "search_new"},
            {"role": "assistant", "tool_calls": [{"function": {"name": "browse"}}]},
            {"role": "tool", "content": "browse_new"},
        ]
        result = mixin._filter_ephemeral_messages(messages)
        # Old search pair (0,1) and old browse pair (2,3) removed
        assert len(result) == 4
        contents = [m.get("content") for m in result]
        assert "search_new" in contents
        assert "browse_new" in contents


class TestExecutorMixinSelfEvaluate:
    def _make_mixin(self):
        mixin = ExecutorMixin.__new__(ExecutorMixin)
        mixin.llm_provider = AsyncMock()
        return mixin

    @pytest.mark.asyncio
    async def test_self_evaluate_task_complete(self):
        mixin = self._make_mixin()
        response = MagicMock()
        response.content = "Everything looks good. TASK_COMPLETE"
        mixin.llm_provider.chat.return_value = response

        task = Task(
            taskId="eval-1",
            action="execute",
            parameters={"content": "Write a poem"},
        )
        # Should complete without error
        await mixin._self_evaluate(task)
        mixin.llm_provider.chat.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_self_evaluate_not_complete(self):
        mixin = self._make_mixin()
        response = MagicMock()
        response.content = "The response is missing the conclusion section."
        mixin.llm_provider.chat.return_value = response

        task = Task(
            taskId="eval-2",
            action="execute",
            parameters={"content": "Write a report"},
        )
        # Should complete without error (the pass branch)
        await mixin._self_evaluate(task)
        mixin.llm_provider.chat.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_self_evaluate_exception_is_swallowed(self):
        mixin = self._make_mixin()
        mixin.llm_provider.chat.side_effect = RuntimeError("LLM unavailable")

        task = Task(
            taskId="eval-3",
            action="execute",
            parameters={"content": "Do something"},
        )
        # Exception should be silently caught
        await mixin._self_evaluate(task)

    @pytest.mark.asyncio
    async def test_self_evaluate_includes_task_content_in_prompt(self):
        mixin = self._make_mixin()
        response = MagicMock()
        response.content = "TASK_COMPLETE"
        mixin.llm_provider.chat.return_value = response

        task = Task(
            taskId="eval-4",
            action="execute",
            parameters={"content": "Summarize the article"},
        )
        await mixin._self_evaluate(task)

        call_args = mixin.llm_provider.chat.call_args
        prompt_content = call_args.kwargs["messages"][0]["content"]
        assert "Summarize the article" in prompt_content


# ==================== PlannerMixin ====================


class TestCreatePlanTool:
    def test_returns_correct_structure(self):
        tool = create_plan_tool()
        assert tool["type"] == "function"
        func = tool["function"]
        assert func["name"] == "create_plan"
        assert "description" in func
        params = func["parameters"]
        assert params["type"] == "object"
        assert "goal" in params["properties"]
        assert "steps" in params["properties"]
        assert "reasoning" in params["properties"]
        assert "goal" in params["required"]
        assert "steps" in params["required"]

    def test_steps_is_array_of_strings(self):
        tool = create_plan_tool()
        steps_prop = tool["function"]["parameters"]["properties"]["steps"]
        assert steps_prop["type"] == "array"
        assert steps_prop["items"]["type"] == "string"

    def test_reasoning_not_required(self):
        tool = create_plan_tool()
        required = tool["function"]["parameters"]["required"]
        assert "reasoning" not in required


class TestPlannerMixinBuildPlanSummary:
    def _make_mixin(self):
        mixin = PlannerMixin.__new__(PlannerMixin)
        return mixin

    def test_with_reasoning(self):
        mixin = self._make_mixin()
        summary = mixin._build_plan_summary(
            goal="Deploy app",
            reasoning="Need staged rollout",
            steps=["Build", "Test", "Deploy"],
        )
        assert "Goal: Deploy app" in summary
        assert "Reasoning: Need staged rollout" in summary
        assert "Steps (3):" in summary
        assert "1. Build" in summary
        assert "2. Test" in summary
        assert "3. Deploy" in summary

    def test_without_reasoning(self):
        mixin = self._make_mixin()
        summary = mixin._build_plan_summary(
            goal="Fix bug",
            reasoning="",
            steps=["Identify", "Fix"],
        )
        assert "Goal: Fix bug" in summary
        assert "Reasoning:" not in summary
        assert "Steps (2):" in summary
        assert "1. Identify" in summary
        assert "2. Fix" in summary

    def test_single_step(self):
        mixin = self._make_mixin()
        summary = mixin._build_plan_summary(
            goal="Simple task",
            reasoning="",
            steps=["Do it"],
        )
        assert "Steps (1):" in summary
        assert "1. Do it" in summary


class TestPlannerMixinSynthesizePlanResults:
    def _make_mixin(self):
        mixin = PlannerMixin.__new__(PlannerMixin)
        mixin.llm_provider = AsyncMock()
        return mixin

    @pytest.mark.asyncio
    async def test_successful_synthesis(self):
        mixin = self._make_mixin()
        response = MagicMock()
        response.content = "The analysis shows three key findings."
        mixin.llm_provider.chat.return_value = response

        result = await mixin._synthesize_plan_results(
            goal="Analyze data",
            original_question="What are the trends?",
            results=["Step 1: Found upward trend", "Step 2: Identified outliers"],
        )
        assert result == "The analysis shows three key findings."
        mixin.llm_provider.chat.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_synthesis_prompt_contains_context(self):
        mixin = self._make_mixin()
        response = MagicMock()
        response.content = "Summary"
        mixin.llm_provider.chat.return_value = response

        await mixin._synthesize_plan_results(
            goal="Research topic",
            original_question="Tell me about X",
            results=["Step 1: Found info"],
        )
        call_args = mixin.llm_provider.chat.call_args
        prompt = call_args.kwargs["messages"][0]["content"]
        assert "Tell me about X" in prompt
        assert "Step 1: Found info" in prompt

    @pytest.mark.asyncio
    async def test_exception_fallback(self):
        mixin = self._make_mixin()
        mixin.llm_provider.chat.side_effect = RuntimeError("LLM down")

        result = await mixin._synthesize_plan_results(
            goal="Analyze data",
            original_question="What happened?",
            results=["Step 1: OK", "Step 2: Done"],
        )
        assert result == "Plan 'Analyze data' completed:\nStep 1: OK\nStep 2: Done"

    @pytest.mark.asyncio
    async def test_fallback_with_empty_results(self):
        mixin = self._make_mixin()
        mixin.llm_provider.chat.side_effect = Exception("fail")

        result = await mixin._synthesize_plan_results(
            goal="Empty plan",
            original_question="?",
            results=[],
        )
        assert result == "Plan 'Empty plan' completed:\n"


# ==================== SkillHandlerMixin ====================


class TestSkillHandlerMixinBuildSkillContext:
    def _make_mixin(self, registry=None, enabled_skills=None):
        mixin = SkillHandlerMixin.__new__(SkillHandlerMixin)
        mixin.skill_registry = registry
        mixin.config = MagicMock()
        mixin.config.enabled_skills = enabled_skills or []
        return mixin

    @pytest.mark.asyncio
    async def test_no_registry_returns_empty(self):
        mixin = self._make_mixin(registry=None, enabled_skills=["s1"])
        result = await mixin._build_skill_context()
        assert result == ""

    @pytest.mark.asyncio
    async def test_no_enabled_skills_returns_empty(self):
        mixin = self._make_mixin(registry=MagicMock(), enabled_skills=[])
        result = await mixin._build_skill_context()
        assert result == ""

    @pytest.mark.asyncio
    async def test_with_skills(self):
        registry = AsyncMock()
        skill_def = MagicMock()
        skill_def.name = "CodeReview"
        skill_def.description = "Reviews code quality"
        skill_def.required_tools = []
        registry.get_skill.return_value = skill_def

        mixin = self._make_mixin(registry=registry, enabled_skills=["code_review"])
        result = await mixin._build_skill_context()
        assert "Available Skills" in result
        assert "CodeReview" in result
        assert "Reviews code quality" in result

    @pytest.mark.asyncio
    async def test_with_required_tools(self):
        registry = AsyncMock()
        skill_def = MagicMock()
        skill_def.name = "WebSearch"
        skill_def.description = "Searches the web"
        skill_def.required_tools = ["http_get", "parse_html"]
        registry.get_skill.return_value = skill_def

        mixin = self._make_mixin(registry=registry, enabled_skills=["web_search"])
        result = await mixin._build_skill_context()
        assert "Required Tools: http_get, parse_html" in result

    @pytest.mark.asyncio
    async def test_skill_not_found_returns_empty(self):
        registry = AsyncMock()
        registry.get_skill.return_value = None

        mixin = self._make_mixin(registry=registry, enabled_skills=["missing"])
        result = await mixin._build_skill_context()
        # Only the header line was added, so len(lines)==1 -> returns ""
        assert result == ""

    @pytest.mark.asyncio
    async def test_exception_in_get_skill_is_skipped(self):
        registry = AsyncMock()
        registry.get_skill.side_effect = RuntimeError("DB error")

        mixin = self._make_mixin(registry=registry, enabled_skills=["broken"])
        result = await mixin._build_skill_context()
        assert result == ""

    @pytest.mark.asyncio
    async def test_mixed_skills_some_fail(self):
        registry = AsyncMock()
        good_skill = MagicMock()
        good_skill.name = "GoodSkill"
        good_skill.description = "Works fine"
        good_skill.required_tools = []

        async def get_skill_side_effect(skill_id):
            if skill_id == "good":
                return good_skill
            raise RuntimeError("not found")

        registry.get_skill.side_effect = get_skill_side_effect

        mixin = self._make_mixin(
            registry=registry, enabled_skills=["bad", "good"]
        )
        result = await mixin._build_skill_context()
        assert "GoodSkill" in result
        assert "Works fine" in result


class TestSkillHandlerMixinActivateSkills:
    def _make_mixin(self, activator=None, registry=None):
        mixin = SkillHandlerMixin.__new__(SkillHandlerMixin)
        mixin.skill_activator = activator
        mixin.skill_registry = registry
        mixin.config = MagicMock()
        mixin._active_skills = set()
        return mixin

    @pytest.mark.asyncio
    async def test_no_activator_returns_empty(self):
        mixin = self._make_mixin(activator=None, registry=MagicMock())
        result = await mixin._activate_skills("do something")
        assert result == {"injected_instructions": []}

    @pytest.mark.asyncio
    async def test_no_registry_returns_empty(self):
        mixin = self._make_mixin(activator=MagicMock(), registry=None)
        result = await mixin._activate_skills("do something")
        assert result == {"injected_instructions": []}

    @pytest.mark.asyncio
    async def test_successful_activation(self):
        registry = AsyncMock()
        activator = AsyncMock()

        skill_def = MagicMock()
        registry.get_skill.return_value = skill_def
        registry.get_all_metadata = AsyncMock(return_value=[{"id": "s1"}])

        activator.find_relevant_skills.return_value = ["s1"]
        activation_result = MagicMock()
        activation_result.success = True
        activation_result.content = "Use search tool for queries"
        activator.activate.return_value = activation_result

        mixin = self._make_mixin(activator=activator, registry=registry)
        result = await mixin._activate_skills("search the web")
        assert "Use search tool for queries" in result["injected_instructions"]

    @pytest.mark.asyncio
    async def test_skill_not_found_skipped(self):
        registry = AsyncMock()
        activator = AsyncMock()

        registry.get_skill.return_value = None
        registry.get_all_metadata = AsyncMock(return_value=[])
        activator.find_relevant_skills.return_value = ["missing_skill"]

        mixin = self._make_mixin(activator=activator, registry=registry)
        result = await mixin._activate_skills("do task")
        assert result["injected_instructions"] == []

    @pytest.mark.asyncio
    async def test_activation_not_successful_skipped(self):
        registry = AsyncMock()
        activator = AsyncMock()

        skill_def = MagicMock()
        registry.get_skill.return_value = skill_def
        registry.get_all_metadata = AsyncMock(return_value=[])
        activator.find_relevant_skills.return_value = ["s1"]

        activation_result = MagicMock()
        activation_result.success = False
        activation_result.content = None
        activator.activate.return_value = activation_result

        mixin = self._make_mixin(activator=activator, registry=registry)
        result = await mixin._activate_skills("task")
        assert result["injected_instructions"] == []

    @pytest.mark.asyncio
    async def test_exception_is_caught(self, capsys):
        activator = AsyncMock()

        activator.find_relevant_skills.side_effect = RuntimeError("boom")
        # Registry without get_all_metadata
        registry_obj = AsyncMock()
        del registry_obj.get_all_metadata

        mixin = self._make_mixin(activator=activator, registry=registry_obj)
        result = await mixin._activate_skills("task")
        assert result["injected_instructions"] == []

    @pytest.mark.asyncio
    async def test_registry_without_get_all_metadata(self):
        """When registry lacks get_all_metadata, skill_metadata stays empty."""
        registry = AsyncMock(spec=[])  # no attributes
        registry.get_skill = AsyncMock(return_value=MagicMock())
        activator = AsyncMock()

        activation_result = MagicMock()
        activation_result.success = True
        activation_result.content = "instructions"
        activator.activate.return_value = activation_result
        activator.find_relevant_skills.return_value = ["s1"]

        mixin = self._make_mixin(activator=activator, registry=registry)
        result = await mixin._activate_skills("task")
        assert "instructions" in result["injected_instructions"]


class TestSkillHandlerMixinActivateSkill:
    def _make_mixin(self, activator=None, registry=None, enabled=None, active=None):
        mixin = SkillHandlerMixin.__new__(SkillHandlerMixin)
        mixin.skill_activator = activator
        mixin.skill_registry = registry
        mixin.config = MagicMock()
        mixin.config.enabled_skills = enabled or []
        mixin._active_skills = active or set()
        return mixin

    @pytest.mark.asyncio
    async def test_not_in_enabled_skills(self):
        mixin = self._make_mixin(enabled=["other_skill"])
        result = await mixin._activate_skill("unknown_skill")
        assert result["success"] is False
        assert "not in enabled_skills" in result["error"]

    @pytest.mark.asyncio
    async def test_already_active(self):
        mixin = self._make_mixin(
            enabled=["my_skill"], active={"my_skill"}
        )
        result = await mixin._activate_skill("my_skill")
        assert result["success"] is True
        assert result["already_active"] is True

    @pytest.mark.asyncio
    async def test_no_activator(self):
        mixin = self._make_mixin(
            activator=None,
            registry=MagicMock(),
            enabled=["my_skill"],
        )
        result = await mixin._activate_skill("my_skill")
        assert result["success"] is False
        assert "not initialized" in result["error"]

    @pytest.mark.asyncio
    async def test_no_registry(self):
        mixin = self._make_mixin(
            activator=MagicMock(),
            registry=None,
            enabled=["my_skill"],
        )
        result = await mixin._activate_skill("my_skill")
        assert result["success"] is False
        assert "not initialized" in result["error"]

    @pytest.mark.asyncio
    async def test_skill_not_found(self):
        registry = AsyncMock()
        registry.get_skill.return_value = None
        activator = AsyncMock()

        mixin = self._make_mixin(
            activator=activator, registry=registry, enabled=["my_skill"]
        )
        result = await mixin._activate_skill("my_skill")
        assert result["success"] is False
        assert "not found" in result["error"]

    @pytest.mark.asyncio
    async def test_successful_activation(self):
        # Patch sys.modules so `from loom.tools.models import ActivationResult` resolves
        fake_module = types.ModuleType("loom.tools.models")
        fake_module.ActivationResult = MagicMock()
        with patch.dict(sys.modules, {"loom.tools.models": fake_module}):
            registry = AsyncMock()
            skill_def = MagicMock()
            registry.get_skill.return_value = skill_def

            activator = AsyncMock()
            activation_result = MagicMock()
            activation_result.success = True
            activation_result.mode = "INJECTION"
            activation_result.content = "Skill instructions here"
            activation_result.error = None
            activator.activate.return_value = activation_result

            mixin = self._make_mixin(
                activator=activator, registry=registry, enabled=["my_skill"]
            )
            result = await mixin._activate_skill("my_skill")
            assert result["success"] is True
            assert result["mode"] == "INJECTION"
            assert result["content"] == "Skill instructions here"
            assert result["error"] is None
            assert "my_skill" in mixin._active_skills

    @pytest.mark.asyncio
    async def test_activation_failure_does_not_add_to_active(self):
        fake_module = types.ModuleType("loom.tools.models")
        fake_module.ActivationResult = MagicMock()
        with patch.dict(sys.modules, {"loom.tools.models": fake_module}):
            registry = AsyncMock()
            skill_def = MagicMock()
            registry.get_skill.return_value = skill_def

            activator = AsyncMock()
            activation_result = MagicMock()
            activation_result.success = False
            activation_result.mode = None
            activation_result.content = None
            activation_result.error = "Missing dependency"
            activator.activate.return_value = activation_result

            mixin = self._make_mixin(
                activator=activator, registry=registry, enabled=["my_skill"]
            )
            result = await mixin._activate_skill("my_skill")
            assert result["success"] is False
            assert result["error"] == "Missing dependency"
            assert "my_skill" not in mixin._active_skills

    @pytest.mark.asyncio
    async def test_exception_returns_error(self):
        registry = AsyncMock()
        registry.get_skill.side_effect = RuntimeError("DB connection lost")
        activator = AsyncMock()

        mixin = self._make_mixin(
            activator=activator, registry=registry, enabled=["my_skill"]
        )
        result = await mixin._activate_skill("my_skill")
        assert result["success"] is False
        assert "DB connection lost" in result["error"]


class TestSkillHandlerMixinLoadRelevantSkills:
    def _make_mixin(self, activator=None, registry=None):
        mixin = SkillHandlerMixin.__new__(SkillHandlerMixin)
        mixin.skill_activator = activator
        mixin.skill_registry = registry
        mixin.config = MagicMock()
        mixin._active_skills = set()
        return mixin

    @pytest.mark.asyncio
    async def test_no_activator_returns_empty_structure(self):
        mixin = self._make_mixin(activator=None)
        result = await mixin._load_relevant_skills("some task")
        assert result == {
            "injected_instructions": [],
            "compiled_tools": [],
            "instantiated_nodes": [],
        }

    @pytest.mark.asyncio
    async def test_delegates_to_activate_skills(self):
        registry = AsyncMock()
        activator = AsyncMock()

        registry.get_all_metadata = AsyncMock(return_value=[])
        activator.find_relevant_skills.return_value = ["s1"]

        skill_def = MagicMock()
        registry.get_skill.return_value = skill_def

        activation_result = MagicMock()
        activation_result.success = True
        activation_result.content = "injected content"
        activator.activate.return_value = activation_result

        mixin = self._make_mixin(activator=activator, registry=registry)
        result = await mixin._load_relevant_skills("do task")
        assert "injected content" in result["injected_instructions"]


# ==================== DelegatorMixin ====================


class TestCreateDelegateTaskTool:
    def test_returns_correct_structure(self):
        tool = create_delegate_task_tool()
        assert tool["type"] == "function"
        func = tool["function"]
        assert func["name"] == "delegate_task"
        assert "description" in func
        params = func["parameters"]
        assert params["type"] == "object"
        assert "subtask_description" in params["properties"]
        assert "required_capabilities" in params["properties"]
        assert "context_hints" in params["properties"]
        assert params["required"] == ["subtask_description"]

    def test_subtask_description_is_string(self):
        tool = create_delegate_task_tool()
        prop = tool["function"]["parameters"]["properties"]["subtask_description"]
        assert prop["type"] == "string"

    def test_required_capabilities_is_array_of_strings(self):
        tool = create_delegate_task_tool()
        prop = tool["function"]["parameters"]["properties"]["required_capabilities"]
        assert prop["type"] == "array"
        assert prop["items"]["type"] == "string"

    def test_context_hints_is_array_of_strings(self):
        tool = create_delegate_task_tool()
        prop = tool["function"]["parameters"]["properties"]["context_hints"]
        assert prop["type"] == "array"
        assert prop["items"]["type"] == "string"
