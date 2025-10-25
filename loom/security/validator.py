"""
Security Validator

Multi-layer security validation system for tool execution.
"""

from pathlib import Path
from typing import Dict, List, Optional
import time

from loom.security.models import RiskLevel, SecurityDecision
from loom.security.path_validator import PathSecurityValidator
from loom.core.types import ToolCall
from loom.core.permissions import PermissionManager, PermissionAction
from loom.interfaces.tool import BaseTool


class SecurityValidator:
    """
    Multi-layer security validator for tool execution.

    Provides 4 layers of independent security checks:
    1. Permission rules (policy-based access control)
    2. Tool category validation (destructive/network/general)
    3. Path security (traversal detection, working dir enforcement)
    4. Sandbox support (automatic sandboxing recommendations)

    Example:
        ```python
        validator = SecurityValidator(
            working_dir=Path("/Users/project"),
            allowed_categories=["general", "network"],
            require_confirmation_for=["destructive"]
        )

        decision = await validator.validate(
            tool_call=ToolCall(name="write_file", arguments={...}),
            tool=WriteFileTool(),
            context={"user_approved": False}
        )

        if decision.allow:
            await tool.run(**tool_call.arguments)
        else:
            print(f"Blocked: {decision.reason}")
        ```
    """

    def __init__(
        self,
        working_dir: Optional[Path] = None,
        allowed_categories: Optional[List[str]] = None,
        require_confirmation_for: Optional[List[str]] = None,
        permission_manager: Optional[PermissionManager] = None,
        enable_sandbox: bool = True
    ):
        """
        Initialize security validator.

        Args:
            working_dir: Working directory for path validation
            allowed_categories: Allowed tool categories
            require_confirmation_for: Categories requiring confirmation
            permission_manager: Optional permission manager
            enable_sandbox: Enable sandbox recommendations
        """
        self.working_dir = working_dir or Path.cwd()
        self.allowed_categories = allowed_categories or ["general", "network", "destructive"]
        self.require_confirmation_for = require_confirmation_for or ["destructive"]
        self.permission_manager = permission_manager
        self.enable_sandbox = enable_sandbox

        # Initialize sub-validators
        self.path_validator = PathSecurityValidator(working_dir=self.working_dir)

        # Audit log
        self.audit_log: List[Dict] = []

    async def validate(
        self,
        tool_call: ToolCall,
        tool: BaseTool,
        context: Optional[Dict] = None
    ) -> SecurityDecision:
        """
        Validate tool execution through all 4 security layers.

        Args:
            tool_call: Tool call to validate
            tool: Tool instance
            context: Additional context (user_approved, etc.)

        Returns:
            SecurityDecision with allow/deny and risk assessment
        """
        context = context or {}
        failed_layers: List[str] = []
        warnings: List[str] = []
        max_risk = RiskLevel.LOW

        # Layer 1: Permission Rules
        layer1_result = await self.layer1_permission_check(tool_call, tool, context)
        if not layer1_result.allow:
            failed_layers.append("permission")
            max_risk = max(max_risk, layer1_result.risk_level)

        # Layer 2: Tool Category Validation
        layer2_result = await self.layer2_category_check(tool, context)
        if not layer2_result.allow:
            failed_layers.append("category")
            max_risk = max(max_risk, layer2_result.risk_level)

        # Layer 3: Path Security
        layer3_result = await self.layer3_path_security(tool_call, tool)
        if not layer3_result.allow:
            failed_layers.append("path_security")
            max_risk = max(max_risk, layer3_result.risk_level)

        # Layer 4: Sandbox Support
        layer4_result = await self.layer4_sandbox_check(tool, context)
        if layer4_result.warnings:
            warnings.extend(layer4_result.warnings)
        max_risk = max(max_risk, layer4_result.risk_level)

        # Aggregate decision
        allow = len(failed_layers) == 0
        reason = self._build_reason(failed_layers, warnings)

        decision = SecurityDecision(
            allow=allow,
            risk_level=max_risk,
            reason=reason,
            failed_layers=failed_layers,
            warnings=warnings
        )

        # Audit log
        self._log_decision(tool_call, tool, decision)

        return decision

    async def layer1_permission_check(
        self,
        tool_call: ToolCall,
        tool: BaseTool,
        context: Dict
    ) -> SecurityDecision:
        """
        Layer 1: Check permission policy.

        Integrates with existing PermissionManager.
        """
        if not self.permission_manager:
            # No permission manager - allow by default
            return SecurityDecision(
                allow=True,
                risk_level=RiskLevel.LOW,
                reason="No permission manager configured"
            )

        action = self.permission_manager.check(tool_call.name, tool_call.arguments)

        if action == PermissionAction.DENY:
            return SecurityDecision(
                allow=False,
                risk_level=RiskLevel.HIGH,
                reason=f"Tool {tool_call.name} denied by permission policy"
            )
        elif action == PermissionAction.ASK:
            # Check if user already approved
            if context.get("user_approved", False):
                return SecurityDecision(
                    allow=True,
                    risk_level=RiskLevel.MEDIUM,
                    reason="User approved"
                )
            else:
                return SecurityDecision(
                    allow=False,
                    risk_level=RiskLevel.MEDIUM,
                    reason=f"Tool {tool_call.name} requires user confirmation"
                )
        else:  # ALLOW
            return SecurityDecision(
                allow=True,
                risk_level=RiskLevel.LOW,
                reason="Allowed by permission policy"
            )

    async def layer2_category_check(
        self,
        tool: BaseTool,
        context: Dict
    ) -> SecurityDecision:
        """
        Layer 2: Validate tool category.

        - Destructive tools require confirmation
        - Network tools checked against whitelist
        - Unknown categories treated as high-risk
        """
        category = getattr(tool, "category", "unknown")

        # Check if category is allowed
        if category not in self.allowed_categories:
            return SecurityDecision(
                allow=False,
                risk_level=RiskLevel.HIGH,
                reason=f"Tool category '{category}' not in allowed categories"
            )

        # Check if confirmation required
        if category in self.require_confirmation_for:
            if not context.get("user_approved", False):
                return SecurityDecision(
                    allow=False,
                    risk_level=RiskLevel.MEDIUM,
                    reason=f"Category '{category}' requires user confirmation"
                )

        # Assess risk based on category
        risk_map = {
            "general": RiskLevel.LOW,
            "network": RiskLevel.MEDIUM,
            "destructive": RiskLevel.HIGH
        }
        risk = risk_map.get(category, RiskLevel.HIGH)

        return SecurityDecision(
            allow=True,
            risk_level=risk,
            reason=f"Category '{category}' allowed"
        )

    async def layer3_path_security(
        self,
        tool_call: ToolCall,
        tool: BaseTool
    ) -> SecurityDecision:
        """
        Layer 3: Validate file paths.

        - Detect path traversal attempts (../)
        - Enforce working directory boundaries
        - Block system paths (/etc, /sys, etc.)
        """
        # Extract path arguments
        path_args = []
        for key in ["path", "file_path", "directory", "folder"]:
            if key in tool_call.arguments:
                path_args.append(tool_call.arguments[key])

        # If no path arguments, skip this layer
        if not path_args:
            return SecurityDecision(
                allow=True,
                risk_level=RiskLevel.LOW,
                reason="No path arguments to validate"
            )

        # Validate all paths
        violations = []
        for path in path_args:
            result = self.path_validator.validate_path(str(path))
            if not result.is_safe:
                violations.extend(result.violations)

        if violations:
            return SecurityDecision(
                allow=False,
                risk_level=RiskLevel.CRITICAL,
                reason=f"Path security violations: {'; '.join(violations)}"
            )

        return SecurityDecision(
            allow=True,
            risk_level=RiskLevel.LOW,
            reason="All paths validated"
        )

    async def layer4_sandbox_check(
        self,
        tool: BaseTool,
        context: Dict
    ) -> SecurityDecision:
        """
        Layer 4: Check sandbox support.

        - Recommend sandbox for safe operations
        - Warn if sandbox unavailable for risky ops
        """
        warnings = []

        if self.enable_sandbox:
            # Check if tool is read-only (safe for sandbox)
            is_read_only = getattr(tool, "is_read_only", False)
            if is_read_only:
                warnings.append("Consider running in sandbox for additional safety")

            # Check if tool is destructive (should use sandbox)
            category = getattr(tool, "category", "general")
            if category == "destructive":
                warnings.append("Destructive tool - sandbox recommended")

        return SecurityDecision(
            allow=True,  # Layer 4 never blocks, only warns
            risk_level=RiskLevel.LOW,
            reason="Sandbox check complete",
            warnings=warnings
        )

    def _build_reason(self, failed_layers: List[str], warnings: List[str]) -> str:
        """Build human-readable reason for decision."""
        if failed_layers:
            layers_str = ", ".join(failed_layers)
            return f"Security check failed in layers: {layers_str}"
        elif warnings:
            return f"Allowed with {len(warnings)} warning(s)"
        else:
            return "All security checks passed"

    def _log_decision(
        self,
        tool_call: ToolCall,
        tool: BaseTool,
        decision: SecurityDecision
    ):
        """Log security decision for audit trail."""
        self.audit_log.append({
            "timestamp": time.time(),
            "tool_name": tool_call.name,
            "tool_category": getattr(tool, "category", "unknown"),
            "decision": decision.allow,
            "risk_level": decision.risk_level.value,
            "reason": decision.reason,
            "failed_layers": decision.failed_layers,
            "warnings": decision.warnings
        })

    def get_audit_log(self) -> List[Dict]:
        """Get security audit log."""
        return self.audit_log.copy()

    def clear_audit_log(self):
        """Clear audit log."""
        self.audit_log.clear()
