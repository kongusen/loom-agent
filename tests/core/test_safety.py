"""Test safety module - constraints, veto, hooks, permissions"""


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

    def test_veto_history(self):
        va = VetoAuthority()
        va.veto("reason 1")
        va.veto("reason 2")
        history = va.get_veto_history()
        assert len(history) == 2
        assert history[0] == "reason 1"
        assert history[1] == "reason 2"

    def test_veto_empty_history(self):
        va = VetoAuthority()
        assert va.get_veto_history() == []

    def test_veto_records_capture_context(self):
        va = VetoAuthority()
        va.veto("dangerous action", tool="Bash", action="execute", context={"risk": "critical"}, source="policy")

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

    def test_trigger_allow(self):
        hm = SafetyHookManager()
        hm.register("tool_use", lambda ctx: HookDecision.ALLOW)
        decision, msg = hm.trigger("tool_use", {})
        assert decision == HookDecision.ALLOW
        assert msg == ""

    def test_trigger_deny(self):
        hm = SafetyHookManager()
        hm.register("tool_use", lambda ctx: HookDecision.DENY)
        decision, msg = hm.trigger("tool_use", {})
        assert decision == HookDecision.DENY

    def test_trigger_ask(self):
        hm = SafetyHookManager()
        hm.register("tool_use", lambda ctx: HookDecision.ASK)
        decision, msg = hm.trigger("tool_use", {})
        assert decision == HookDecision.ASK

    def test_trigger_no_hooks(self):
        hm = SafetyHookManager()
        decision, msg = hm.trigger("unknown", {})
        assert decision == HookDecision.ALLOW

    def test_trigger_deny_short_circuits(self):
        hm = SafetyHookManager()
        call_count = {"n": 0}

        def deny_hook(ctx):
            return HookDecision.DENY

        def counting_hook(ctx):
            call_count["n"] += 1
            return HookDecision.ALLOW

        hm.register("event", deny_hook)
        hm.register("event", counting_hook)
        decision, _ = hm.trigger("event", {})
        assert decision == HookDecision.DENY
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
