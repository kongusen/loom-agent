"""Test safety module - constraints, veto, hooks, permissions"""

from unittest.mock import MagicMock

import pytest

from loom.safety.constraints import ConstraintValidator
from loom.safety.hooks import HookDecision, HookOutcome
from loom.safety.hooks import HookManager as SafetyHookManager
from loom.safety.permissions import PermissionManager as SafetyPermissionManager
from loom.safety.permissions import PermissionMode
from loom.safety.veto import VetoAuthority
from loom.types import ToolCall

# ── ConstraintValidator ──


class TestConstraintValidator:
    def test_creation(self):
        cv = ConstraintValidator()
        assert cv.constraints == {}

    def test_add_constraint(self):
        cv = ConstraintValidator()

        def constraint(tc):
            return True

        cv.add_constraint("tool_1", constraint)
        assert "tool_1" in cv.constraints
        assert len(cv.constraints["tool_1"]) == 1

    def test_validate_no_constraints(self):
        cv = ConstraintValidator()
        tc = ToolCall(id="1", name="tool_1", arguments={})
        ok, msg = cv.validate(tc)
        assert ok is True
        assert msg == ""

    def test_validate_pass(self):
        cv = ConstraintValidator()
        cv.add_constraint("tool_1", lambda tc: True)
        tc = ToolCall(id="1", name="tool_1", arguments={})
        ok, msg = cv.validate(tc)
        assert ok is True

    def test_validate_fail(self):
        cv = ConstraintValidator()
        cv.add_constraint("tool_1", lambda tc: False)
        tc = ToolCall(id="1", name="tool_1", arguments={})
        ok, msg = cv.validate(tc)
        assert ok is False
        assert "Constraint violation" in msg

    def test_validate_multiple_constraints(self):
        cv = ConstraintValidator()
        cv.add_constraint("tool_1", lambda tc: True)
        cv.add_constraint("tool_1", lambda tc: False)
        tc = ToolCall(id="1", name="tool_1", arguments={})
        ok, msg = cv.validate(tc)
        assert ok is False

    def test_validate_wrong_tool(self):
        cv = ConstraintValidator()
        cv.add_constraint("tool_1", lambda tc: False)
        tc = ToolCall(id="1", name="tool_2", arguments={})
        ok, msg = cv.validate(tc)
        assert ok is True

    def test_validate_with_details_returns_structured_violation(self):
        cv = ConstraintValidator()
        cv.add_constraint("tool_1", lambda tc: (False, "path is forbidden"))
        tc = ToolCall(id="1", name="tool_1", arguments={"path": "/tmp"})

        result = cv.validate_with_details(tc)

        assert result.ok is False
        assert result.message == "path is forbidden"
        assert len(result.violations) == 1
        assert result.violations[0].tool == "tool_1"
        assert result.violations[0].arguments["path"] == "/tmp"

    def test_validate_with_details_handles_constraint_exception(self):
        cv = ConstraintValidator()

        def _boom(_tc):
            raise RuntimeError("unexpected validator crash")

        cv.add_constraint("tool_1", _boom)
        tc = ToolCall(id="1", name="tool_1", arguments={})

        result = cv.validate_with_details(tc)

        assert result.ok is False
        assert "Constraint exception" in result.message


# ── VetoAuthority ──


class TestVetoAuthority:
    def test_creation(self):
        va = VetoAuthority()
        assert va.enabled is True
        assert va.veto_log == []

    def test_veto(self):
        va = VetoAuthority()
        result = va.veto("dangerous action")
        assert result is True
        assert len(va.veto_log) == 1

    def test_veto_disabled(self):
        va = VetoAuthority()
        va.enabled = False
        result = va.veto("action")
        assert result is False
        assert len(va.veto_log) == 0

    def test_veto_records(self):
        va = VetoAuthority()
        va.veto("reason 1")
        va.veto("reason 2")
        records = va.get_veto_records()
        assert len(records) == 2
        assert records[0].reason == "reason 1"
        assert records[1].reason == "reason 2"

    def test_veto_empty_records(self):
        va = VetoAuthority()
        assert va.get_veto_records() == []

    def test_veto_records_capture_context(self):
        va = VetoAuthority()
        va.veto(
            "dangerous action",
            tool="Bash",
            action="execute",
            context={"risk": "critical"},
            source="policy",
        )

        records = va.get_veto_records()

        assert len(records) == 1
        assert records[0].tool == "Bash"
        assert records[0].context["risk"] == "critical"
        assert va.audit_summary()["sources"] == ["policy"]


# ── Safety HookManager ──


class TestSafetyHookManager:
    def test_creation(self):
        hm = SafetyHookManager()
        assert hm.hooks == {}

    def test_register(self):
        hm = SafetyHookManager()
        hm.register("tool_use", lambda ctx: HookDecision.ALLOW)
        assert "tool_use" in hm.hooks

    def test_evaluate_allow(self):
        hm = SafetyHookManager()
        hm.register("tool_use", lambda ctx: HookDecision.ALLOW)
        outcome = hm.evaluate("tool_use", {})
        assert outcome.decision == HookDecision.ALLOW
        assert outcome.message == ""

    def test_evaluate_deny(self):
        hm = SafetyHookManager()
        hm.register("tool_use", lambda ctx: HookDecision.DENY)
        outcome = hm.evaluate("tool_use", {})
        assert outcome.decision == HookDecision.DENY

    def test_evaluate_ask(self):
        hm = SafetyHookManager()
        hm.register("tool_use", lambda ctx: HookDecision.ASK)
        outcome = hm.evaluate("tool_use", {})
        assert outcome.decision == HookDecision.ASK

    def test_evaluate_no_hooks(self):
        hm = SafetyHookManager()
        outcome = hm.evaluate("unknown", {})
        assert outcome.decision == HookDecision.ALLOW

    def test_evaluate_deny_short_circuits(self):
        hm = SafetyHookManager()
        call_count = {"n": 0}

        def deny_hook(ctx):
            return HookDecision.DENY

        def counting_hook(ctx):
            call_count["n"] += 1
            return HookDecision.ALLOW

        hm.register("event", deny_hook)
        hm.register("event", counting_hook)
        outcome = hm.evaluate("event", {})
        assert outcome.decision == HookDecision.DENY
        assert call_count["n"] == 0

    def test_evaluate_merges_context_updates(self):
        hm = SafetyHookManager()
        hm.register(
            "tool_use",
            lambda ctx: HookOutcome(
                decision=HookDecision.ASK,
                message="Needs review",
                context_updates={"approval_reason": "write access"},
            ),
        )

        outcome = hm.evaluate("tool_use", {"tool": "Write"})

        assert outcome.decision == HookDecision.ASK
        assert outcome.message == "Needs review"
        assert outcome.context_updates["approval_reason"] == "write access"


# ── Safety PermissionManager ──


class TestSafetyPermissionManager:
    def test_creation(self):
        pm = SafetyPermissionManager()
        assert pm.mode == PermissionMode.DEFAULT
        assert pm.permissions == {}

    def test_creation_plan_mode(self):
        pm = SafetyPermissionManager(mode=PermissionMode.PLAN)
        assert pm.mode == PermissionMode.PLAN

    def test_grant(self):
        pm = SafetyPermissionManager()
        pm.grant("bash", "execute")
        key = "bash:execute"
        assert key in pm.permissions
        assert pm.permissions[key].allowed is True

    def test_revoke(self):
        pm = SafetyPermissionManager()
        pm.grant("bash", "execute")
        pm.revoke("bash", "execute")
        key = "bash:execute"
        assert pm.permissions[key].allowed is False

    def test_check_granted(self):
        pm = SafetyPermissionManager()
        pm.grant("bash", "execute")
        ok, msg = pm.check("bash", "execute")
        assert ok is True

    def test_check_revoked(self):
        pm = SafetyPermissionManager()
        pm.grant("bash", "execute")
        pm.revoke("bash", "execute")
        ok, msg = pm.check("bash", "execute")
        assert ok is False

    def test_check_not_set_default_mode(self):
        pm = SafetyPermissionManager()
        ok, msg = pm.check("unknown", "action")
        assert ok is False

    def test_check_not_set_auto_mode(self):
        pm = SafetyPermissionManager(mode=PermissionMode.AUTO)
        ok, msg = pm.check("unknown", "action")
        assert ok is True  # AUTO mode allows unspecified

    def test_check_plan_mode_blocks_all(self):
        pm = SafetyPermissionManager(mode=PermissionMode.PLAN)
        pm.grant("bash", "execute")
        ok, msg = pm.check("bash", "execute")
        assert ok is False
        assert "Plan mode" in msg

    def test_grant_multiple(self):
        pm = SafetyPermissionManager()
        pm.grant("tool_1", "read")
        pm.grant("tool_2", "write")
        assert len(pm.permissions) == 2

    def test_grant_requires_approval(self):
        pm = SafetyPermissionManager()
        pm.grant("bash", "execute", requires_approval=True)

        ok, msg = pm.check("bash", "execute")

        assert ok is False
        assert "Approval required" in msg

    def test_check_high_risk_requires_explicit_permission(self):
        pm = SafetyPermissionManager()

        ok, msg = pm.check("bash", "execute", context={"risk": "critical"})

        assert ok is False
        assert "critical-risk" in msg

    def test_check_risk_rule_in_default_mode(self):
        pm = SafetyPermissionManager()
        pm.grant("deploy", "execute", risk_levels=("high",), note="review deploys")

        ok, msg = pm.check("deploy", "execute", context={"risk": "high"})

        assert ok is False
        assert "review deploys" in msg

    def test_check_risk_rule_in_auto_mode(self):
        pm = SafetyPermissionManager(mode=PermissionMode.AUTO)
        pm.grant("deploy", "execute", risk_levels=("high",), note="review deploys")

        ok, msg = pm.check("deploy", "execute", context={"risk": "high"})

        assert ok is True

    def test_wildcard_permission_matches(self):
        pm = SafetyPermissionManager()
        pm.grant("filesystem", "*")

        ok, msg = pm.check("filesystem", "write")

        assert ok is True

    def test_hook_ask_interacts_with_permission_mode(self):
        pm = SafetyPermissionManager()
        pm.grant("bash", "execute")

        ok, msg = pm.check("bash", "execute", hook_decision=HookDecision.ASK)

        assert ok is False
        assert "Approval required" in msg

    def test_hook_ask_auto_mode_allows(self):
        pm = SafetyPermissionManager(mode=PermissionMode.AUTO)

        ok, msg = pm.check("bash", "execute", hook_decision=HookDecision.ASK)

        assert ok is True

    def test_evaluate_returns_structured_decision(self):
        pm = SafetyPermissionManager()
        pm.grant("bash", "execute", requires_approval=True)

        decision = pm.evaluate("bash", "execute")

        assert decision.allowed is False
        assert decision.requires_approval is True
        assert decision.matched_permission is not None


# ── Engine integration: hook → permission → veto pipeline ──


class TestEngineHookPermissionPipeline:
    """Tests for the hook→permission→veto safety pipeline in AgentEngine."""

    def _make_engine(self, provider=None):
        from loom.runtime.engine import AgentEngine, EngineConfig

        mock_provider = provider or MagicMock()
        return AgentEngine(
            provider=mock_provider,
            config=EngineConfig(enable_safety=True),
        )

    def _make_tool_call(self, name="test_tool", call_id="c1"):
        return ToolCall(id=call_id, name=name, arguments={})

    def test_hook_manager_always_created(self):
        engine = self._make_engine()
        from loom.safety.hooks import HookManager

        assert isinstance(engine.hook_manager, HookManager)

    def test_permission_manager_none_by_default(self):
        engine = self._make_engine()
        assert engine.permission_manager is None

    def test_permission_manager_injectable(self):
        from loom.runtime.engine import AgentEngine, EngineConfig
        from loom.safety.permissions import PermissionManager, PermissionMode

        pm = PermissionManager(mode=PermissionMode.AUTO)
        engine = AgentEngine(
            provider=MagicMock(),
            config=EngineConfig(),
            permission_manager=pm,
        )
        assert engine.permission_manager is pm

    @pytest.mark.asyncio
    async def test_hook_deny_blocks_execution(self):
        engine = self._make_engine()
        engine.hook_manager.register(
            "before_tool_call",
            lambda ctx: (HookDecision.DENY, "blocked by test"),
        )
        call = self._make_tool_call()
        results = await engine.tool_runtime.execute_tools([call])
        assert len(results) == 1
        assert results[0].is_error
        assert "Hook denied" in results[0].content

    @pytest.mark.asyncio
    async def test_hook_allow_proceeds(self):
        engine = self._make_engine()
        engine.hook_manager.register(
            "before_tool_call",
            lambda ctx: HookDecision.ALLOW,
        )
        # Tool not registered → executor returns error, but hook itself allowed
        call = self._make_tool_call()
        results = await engine.tool_runtime.execute_tools([call])
        assert len(results) == 1
        # Error comes from missing tool, not from hook denial
        assert "Hook denied" not in results[0].content

    @pytest.mark.asyncio
    async def test_permission_deny_blocks_execution(self):
        from loom.safety.permissions import PermissionManager, PermissionMode

        engine = self._make_engine()
        pm = PermissionManager(mode=PermissionMode.DEFAULT)
        pm.revoke("test_tool", "execute", note="not allowed")
        engine.permission_manager = pm
        engine.runtime_wiring.refresh_tool_runtime()

        call = self._make_tool_call()
        results = await engine.tool_runtime.execute_tools([call])
        assert len(results) == 1
        assert results[0].is_error
        assert "Permission denied" in results[0].content

    @pytest.mark.asyncio
    async def test_veto_still_works_after_hooks(self):
        from loom.safety.veto import VetoRule

        engine = self._make_engine()
        engine.veto_authority.add_rule(
            VetoRule(
                name="block_all",
                predicate=lambda name, args: True,
                reason="vetoed by test",
            )
        )
        call = self._make_tool_call()
        results = await engine.tool_runtime.execute_tools([call])
        assert len(results) == 1
        assert results[0].is_error
        assert "Vetoed" in results[0].content

    @pytest.mark.asyncio
    async def test_hook_deny_takes_priority_over_permission_and_veto(self):
        from loom.safety.permissions import PermissionManager, PermissionMode
        from loom.safety.veto import VetoRule

        engine = self._make_engine()
        # All three layers would deny — hook fires first
        engine.hook_manager.register(
            "before_tool_call",
            lambda ctx: (HookDecision.DENY, "hook blocked"),
        )
        pm = PermissionManager(mode=PermissionMode.DEFAULT)
        pm.revoke("test_tool", "execute")
        engine.permission_manager = pm
        engine.runtime_wiring.refresh_tool_runtime()
        engine.veto_authority.add_rule(
            VetoRule(name="block", predicate=lambda n, a: True, reason="vetoed")
        )
        call = self._make_tool_call()
        results = await engine.tool_runtime.execute_tools([call])
        assert "Hook denied" in results[0].content

    def test_current_iteration_tracked(self):
        engine = self._make_engine()
        assert engine._current_iteration == 0
