"""
Unit tests for SecurityValidator

Tests multi-layer security validation system.
"""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, Mock

from loom.security import (
    RiskLevel,
    SecurityDecision,
    PathSecurityResult,
    PathSecurityValidator,
    SecurityValidator
)
from loom.core.types import ToolCall
from loom.interfaces.tool import BaseTool
from pydantic import BaseModel


# Mock tools for testing
class MockSafeTool(BaseTool):
    name = "mock_safe"
    description = "Safe tool"
    args_schema = BaseModel
    is_read_only = True
    category = "general"

    async def run(self, **kwargs):
        return "safe_result"


class MockDestructiveTool(BaseTool):
    name = "mock_destructive"
    description = "Destructive tool"
    args_schema = BaseModel
    is_read_only = False
    category = "destructive"

    async def run(self, **kwargs):
        return "destructive_result"


class TestSecurityDecision:
    """Test SecurityDecision model."""

    def test_decision_creation(self):
        """Test SecurityDecision creation."""
        decision = SecurityDecision(
            allow=True,
            risk_level=RiskLevel.LOW,
            reason="Test reason"
        )
        assert decision.allow is True
        assert decision.risk_level == RiskLevel.LOW
        assert decision.reason == "Test reason"

    def test_is_safe_property_low(self):
        """Test is_safe with low risk."""
        decision = SecurityDecision(
            allow=True,
            risk_level=RiskLevel.LOW,
            reason="Safe"
        )
        assert decision.is_safe is True

    def test_is_safe_property_high(self):
        """Test is_safe with high risk."""
        decision = SecurityDecision(
            allow=True,
            risk_level=RiskLevel.HIGH,
            reason="Risky"
        )
        assert decision.is_safe is False

    def test_is_safe_property_blocked(self):
        """Test is_safe when blocked."""
        decision = SecurityDecision(
            allow=False,
            risk_level=RiskLevel.LOW,
            reason="Blocked"
        )
        assert decision.is_safe is False


class TestRiskLevel:
    """Test RiskLevel enum."""

    def test_risk_level_comparison(self):
        """Test risk level comparisons."""
        assert RiskLevel.LOW < RiskLevel.MEDIUM
        assert RiskLevel.MEDIUM < RiskLevel.HIGH
        assert RiskLevel.HIGH < RiskLevel.CRITICAL

    def test_risk_level_max(self):
        """Test max() works with RiskLevel."""
        result = max(RiskLevel.LOW, RiskLevel.HIGH)
        assert result == RiskLevel.HIGH


class TestPathSecurityValidator:
    """Test PathSecurityValidator."""

    def test_safe_relative_path(self):
        """Test safe relative path."""
        validator = PathSecurityValidator(working_dir=Path("/tmp/project"))
        result = validator.validate_path("src/main.py")

        assert result.is_safe is True
        assert len(result.violations) == 0

    def test_path_traversal_detection(self):
        """Test ../ detection."""
        validator = PathSecurityValidator(working_dir=Path("/tmp/project"))
        result = validator.validate_path("../../etc/passwd")

        assert result.is_safe is False
        assert any("traversal" in v.lower() for v in result.violations)

    def test_system_path_blocking(self):
        """Test system path protection."""
        validator = PathSecurityValidator(working_dir=Path("/tmp/project"))
        result = validator.validate_path("/etc/passwd")

        assert result.is_safe is False
        # Should have either "system path" or "outside working directory" violation
        assert len(result.violations) > 0

    def test_is_safe_path_method(self):
        """Test is_safe_path shortcut."""
        validator = PathSecurityValidator(working_dir=Path("/tmp/project"))
        assert validator.is_safe_path("src/main.py") is True
        assert validator.is_safe_path("../../etc/passwd") is False


@pytest.mark.asyncio
class TestLayer1PermissionCheck:
    """Test Layer 1: Permission rules."""

    async def test_no_permission_manager(self):
        """Test when no permission manager configured."""
        validator = SecurityValidator()
        tool = MockSafeTool()
        tool_call = ToolCall(id="1", name="mock_safe", arguments={})

        decision = await validator.layer1_permission_check(tool_call, tool, {})

        assert decision.allow is True
        assert decision.risk_level == RiskLevel.LOW

    async def test_with_permission_manager_allow(self):
        """Test permission manager allowing tool."""
        from loom.core.permissions import PermissionManager

        pm = PermissionManager(policy={"mock_safe": "allow"})
        validator = SecurityValidator(permission_manager=pm)

        tool = MockSafeTool()
        tool_call = ToolCall(id="1", name="mock_safe", arguments={})

        decision = await validator.layer1_permission_check(tool_call, tool, {})

        assert decision.allow is True


@pytest.mark.asyncio
class TestLayer2CategoryCheck:
    """Test Layer 2: Tool category validation."""

    async def test_general_category_allowed(self):
        """Test general category tools allowed."""
        validator = SecurityValidator(allowed_categories=["general"])
        tool = MockSafeTool()

        decision = await validator.layer2_category_check(tool, {})

        assert decision.allow is True
        assert decision.risk_level == RiskLevel.LOW

    async def test_destructive_requires_confirmation(self):
        """Test destructive tools require confirmation."""
        validator = SecurityValidator(
            allowed_categories=["general", "destructive"],
            require_confirmation_for=["destructive"]
        )
        tool = MockDestructiveTool()

        # Without user approval
        decision = await validator.layer2_category_check(tool, {})
        assert decision.allow is False

        # With user approval
        decision = await validator.layer2_category_check(tool, {"user_approved": True})
        assert decision.allow is True

    async def test_disallowed_category(self):
        """Test disallowed category blocked."""
        validator = SecurityValidator(allowed_categories=["general"])
        tool = MockDestructiveTool()  # category="destructive"

        decision = await validator.layer2_category_check(tool, {})

        assert decision.allow is False
        assert decision.risk_level == RiskLevel.HIGH


@pytest.mark.asyncio
class TestLayer3PathSecurity:
    """Test Layer 3: Path security."""

    async def test_no_path_arguments(self):
        """Test tools without path arguments."""
        validator = SecurityValidator()
        tool = MockSafeTool()
        tool_call = ToolCall(id="1", name="mock_safe", arguments={})

        decision = await validator.layer3_path_security(tool_call, tool)

        assert decision.allow is True
        assert decision.risk_level == RiskLevel.LOW

    async def test_safe_path_allowed(self):
        """Test safe paths allowed."""
        validator = SecurityValidator(working_dir=Path("/tmp/project"))
        tool = MockSafeTool()
        tool_call = ToolCall(id="1", name="mock_safe", arguments={"path": "src/main.py"})

        decision = await validator.layer3_path_security(tool_call, tool)

        assert decision.allow is True

    async def test_path_traversal_blocked(self):
        """Test path traversal blocked."""
        validator = SecurityValidator(working_dir=Path("/tmp/project"))
        tool = MockSafeTool()
        tool_call = ToolCall(id="1", name="mock_safe", arguments={"path": "../../etc/passwd"})

        decision = await validator.layer3_path_security(tool_call, tool)

        assert decision.allow is False
        assert decision.risk_level == RiskLevel.CRITICAL


@pytest.mark.asyncio
class TestLayer4SandboxCheck:
    """Test Layer 4: Sandbox support."""

    async def test_sandbox_recommendation(self):
        """Test sandbox recommended for safe ops."""
        validator = SecurityValidator(enable_sandbox=True)
        tool = MockSafeTool()  # read-only

        decision = await validator.layer4_sandbox_check(tool, {})

        assert decision.allow is True  # Never blocks
        assert len(decision.warnings) > 0

    async def test_sandbox_disabled(self):
        """Test with sandbox disabled."""
        validator = SecurityValidator(enable_sandbox=False)
        tool = MockSafeTool()

        decision = await validator.layer4_sandbox_check(tool, {})

        assert decision.allow is True
        assert len(decision.warnings) == 0


@pytest.mark.asyncio
class TestSecurityValidatorIntegration:
    """Test SecurityValidator full integration."""

    async def test_all_layers_pass(self):
        """Test all layers passing."""
        validator = SecurityValidator(
            working_dir=Path("/tmp/project"),
            allowed_categories=["general"]
        )
        tool = MockSafeTool()
        tool_call = ToolCall(id="1", name="mock_safe", arguments={"path": "src/main.py"})

        decision = await validator.validate(tool_call, tool, {})

        assert decision.allow is True
        assert len(decision.failed_layers) == 0

    async def test_single_layer_failure(self):
        """Test single layer failure blocks execution."""
        validator = SecurityValidator(
            working_dir=Path("/tmp/project"),
            allowed_categories=["general"]  # destructive not allowed
        )
        tool = MockDestructiveTool()
        tool_call = ToolCall(id="1", name="mock_destructive", arguments={})

        decision = await validator.validate(tool_call, tool, {})

        assert decision.allow is False
        assert "category" in decision.failed_layers

    async def test_multiple_layer_failures(self):
        """Test multiple layer failures."""
        validator = SecurityValidator(
            working_dir=Path("/tmp/project"),
            allowed_categories=["general"]
        )
        tool = MockDestructiveTool()
        tool_call = ToolCall(
            id="1",
            name="mock_destructive",
            arguments={"path": "../../etc/passwd"}
        )

        decision = await validator.validate(tool_call, tool, {})

        assert decision.allow is False
        assert len(decision.failed_layers) >= 1

    async def test_audit_logging(self):
        """Test audit log captures decisions."""
        validator = SecurityValidator()
        tool = MockSafeTool()
        tool_call = ToolCall(id="1", name="mock_safe", arguments={})

        await validator.validate(tool_call, tool, {})

        audit_log = validator.get_audit_log()
        assert len(audit_log) == 1
        assert audit_log[0]["tool_name"] == "mock_safe"
        assert "decision" in audit_log[0]


@pytest.mark.asyncio
class TestToolOrchestrationWithSecurity:
    """Test security integration with ToolOrchestrator."""

    async def test_orchestrator_with_security_validator(self):
        """Test orchestrator uses security validator."""
        from loom.core.tool_orchestrator import ToolOrchestrator

        validator = SecurityValidator(
            allowed_categories=["general", "destructive"],
            require_confirmation_for=["destructive"]
        )

        tools = {
            "safe": MockSafeTool(),
            "destructive": MockDestructiveTool()
        }

        orchestrator = ToolOrchestrator(
            tools=tools,
            security_validator=validator
        )

        # Safe tool should work
        tool_call = ToolCall(id="1", name="safe", arguments={})
        events = []
        async for event in orchestrator.execute_one(tool_call):
            events.append(event)

        # Should have execution start and result
        from loom.core.events import AgentEventType
        event_types = [e.type for e in events]
        assert AgentEventType.TOOL_EXECUTION_START in event_types

    async def test_security_blocks_dangerous_tool(self):
        """Test security validator blocks dangerous tools."""
        from loom.core.tool_orchestrator import ToolOrchestrator

        validator = SecurityValidator(
            working_dir=Path("/tmp/project"),
            allowed_categories=["general"]
        )

        tools = {"destructive": MockDestructiveTool()}

        orchestrator = ToolOrchestrator(
            tools=tools,
            security_validator=validator
        )

        # Destructive tool should be blocked
        tool_call = ToolCall(id="1", name="destructive", arguments={})
        events = []
        async for event in orchestrator.execute_one(tool_call):
            events.append(event)

        # Should have error event
        from loom.core.events import AgentEventType
        event_types = [e.type for e in events]
        assert AgentEventType.TOOL_ERROR in event_types
