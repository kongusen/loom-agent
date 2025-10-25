# Task 2.2: Implement SecurityValidator

**Status**: 🔄 In Progress
**Priority**: P1 (High)
**Estimated Time**: 2 days
**Started**: 2025-10-25
**Dependencies**: Task 2.1 (ToolOrchestrator)

---

## 📋 Overview

### Objective

Implement a multi-layer security validation system that provides comprehensive protection for tool execution through 4 independent security layers.

### Current Problem

```python
# Loom 1.0 - Single layer security (PermissionManager only)
if permission_manager.check(tool, args) == "allow":
    await tool.run(**args)  # Execute

# Problems:
# 1. No category-based validation (destructive tools need extra checks)
# 2. No path security (tools can access any file)
# 3. No sandbox awareness
# 4. Binary allow/deny (no risk assessment)
```

**Real Security Risks**:
```python
# Risk 1: Destructive tool without confirmation
tool_call = ToolCall(name="write_file", arguments={
    "path": "/etc/passwd",  # System file!
    "content": "malicious"
})
# Loom 1.0: May execute if permission policy allows ❌

# Risk 2: Path traversal attack
tool_call = ToolCall(name="read_file", arguments={
    "path": "../../../etc/passwd"  # Path traversal!
})
# Loom 1.0: No path validation ❌

# Risk 3: Network tool abuse
tool_call = ToolCall(name="http_request", arguments={
    "url": "http://internal-service/admin",  # Internal endpoint!
    "method": "DELETE"
})
# Loom 1.0: No network filtering ❌
```

### Solution

```python
# Loom 2.0 - 4-Layer Security Validation
class SecurityValidator:
    async def validate(self, tool_call, tool, context):
        # Layer 1: Permission Rules
        decision = await self.layer1_permission_check(tool_call, tool)

        # Layer 2: Tool Category Validation
        decision = await self.layer2_category_check(tool, context)

        # Layer 3: Path Security
        decision = await self.layer3_path_security(tool_call, tool)

        # Layer 4: Sandbox Support
        decision = await self.layer4_sandbox_check(tool)

        return SecurityDecision(allow=True/False, risk_level=..., reason=...)
```

---

## 🎯 Goals

1. **Defense in Depth**: Multiple independent security layers
2. **Risk Assessment**: Not just allow/deny, but risk scoring
3. **Path Protection**: Prevent path traversal and unauthorized access
4. **Category-Based**: Different rules for different tool categories
5. **Auditability**: Log all security decisions

---

## 🏗️ Architecture

### 4-Layer Security Model

```
┌────────────────────────────────────────────────────────┐
│                  SecurityValidator                     │
│                                                        │
│  ┌──────────────────────────────────────────────────┐ │
│  │ Layer 1: Permission Rules                        │ │
│  │ - Policy-based access control                    │ │
│  │ - User confirmation for sensitive ops            │ │
│  │ - Integration with PermissionManager             │ │
│  └──────────────────────────────────────────────────┘ │
│                         ↓                              │
│  ┌──────────────────────────────────────────────────┐ │
│  │ Layer 2: Tool Category Validation                │ │
│  │ - Destructive tools require confirmation         │ │
│  │ - Network tools checked against whitelist        │ │
│  │ - High-risk categories flagged                   │ │
│  └──────────────────────────────────────────────────┘ │
│                         ↓                              │
│  ┌──────────────────────────────────────────────────┐ │
│  │ Layer 3: Path Security                           │ │
│  │ - Path traversal detection                       │ │
│  │ - Working directory enforcement                  │ │
│  │ - System path protection                         │ │
│  └──────────────────────────────────────────────────┘ │
│                         ↓                              │
│  ┌──────────────────────────────────────────────────┐ │
│  │ Layer 4: Sandbox Support                         │ │
│  │ - Sandbox capability detection                   │ │
│  │ - Auto-sandbox for safe operations               │ │
│  │ - Sandbox escape prevention                      │ │
│  └──────────────────────────────────────────────────┘ │
│                         ↓                              │
│              SecurityDecision(allow, risk, reason)     │
└────────────────────────────────────────────────────────┘
```

### Class Design

```python
# loom/security/validator.py

from enum import Enum
from dataclasses import dataclass
from typing import Optional, List, Dict
from pathlib import Path


class RiskLevel(str, Enum):
    """Security risk levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SecurityDecision:
    """Result of security validation."""
    allow: bool
    risk_level: RiskLevel
    reason: str
    failed_layers: List[str] = None
    warnings: List[str] = None

    @property
    def is_safe(self) -> bool:
        """Check if decision is safe to execute."""
        return self.allow and self.risk_level in [RiskLevel.LOW, RiskLevel.MEDIUM]


class SecurityValidator:
    """
    Multi-layer security validator for tool execution.

    Provides 4 layers of independent security checks:
    1. Permission rules (policy-based access control)
    2. Tool category validation (destructive/network/general)
    3. Path security (traversal detection, working dir enforcement)
    4. Sandbox support (automatic sandboxing for safe ops)

    Example:
        ```python
        validator = SecurityValidator(
            working_dir="/Users/project",
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
        self.working_dir = working_dir or Path.cwd()
        self.allowed_categories = allowed_categories or ["general", "network", "destructive"]
        self.require_confirmation_for = require_confirmation_for or ["destructive"]
        self.permission_manager = permission_manager
        self.enable_sandbox = enable_sandbox
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
        failed_layers = []
        warnings = []
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
        ...

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
        ...

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
        ...

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
        ...

    def _build_reason(self, failed_layers: List[str], warnings: List[str]) -> str:
        """Build human-readable reason for decision."""
        ...

    def _log_decision(
        self,
        tool_call: ToolCall,
        tool: BaseTool,
        decision: SecurityDecision
    ):
        """Log security decision for audit trail."""
        ...

    def get_audit_log(self) -> List[Dict]:
        """Get security audit log."""
        return self.audit_log
```

---

## 📝 Implementation Steps

### Step 1: Create Security Models

**File**: `loom/security/models.py` (new)

```python
from enum import Enum
from dataclasses import dataclass
from typing import List, Optional


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SecurityDecision:
    allow: bool
    risk_level: RiskLevel
    reason: str
    failed_layers: List[str] = None
    warnings: List[str] = None

    @property
    def is_safe(self) -> bool:
        return self.allow and self.risk_level in [RiskLevel.LOW, RiskLevel.MEDIUM]


@dataclass
class PathSecurityResult:
    is_safe: bool
    normalized_path: str
    warnings: List[str]
    violations: List[str]
```

### Step 2: Implement Path Security Validator

**File**: `loom/security/path_validator.py` (new)

```python
from pathlib import Path
from typing import List, Optional

SYSTEM_PATHS = [
    "/etc",
    "/sys",
    "/proc",
    "/dev",
    "/boot",
    "/root",
    "/var/log",
]


class PathSecurityValidator:
    """Validate file paths for security."""

    def __init__(self, working_dir: Path):
        self.working_dir = working_dir.resolve()

    def validate_path(self, path: str) -> PathSecurityResult:
        """
        Validate a file path for security issues.

        Checks:
        1. Path traversal (../)
        2. Absolute path outside working dir
        3. System paths
        4. Symlink attacks (future)
        """
        violations = []
        warnings = []

        # Detect path traversal
        if ".." in path:
            violations.append("Path traversal detected")

        # Resolve and check boundaries
        try:
            resolved = (self.working_dir / path).resolve()

            # Check if within working dir
            if not str(resolved).startswith(str(self.working_dir)):
                violations.append(f"Path outside working directory: {resolved}")

            # Check system paths
            for sys_path in SYSTEM_PATHS:
                if str(resolved).startswith(sys_path):
                    violations.append(f"System path access denied: {sys_path}")

        except Exception as e:
            violations.append(f"Path resolution failed: {e}")

        is_safe = len(violations) == 0

        return PathSecurityResult(
            is_safe=is_safe,
            normalized_path=str(resolved) if is_safe else path,
            warnings=warnings,
            violations=violations
        )
```

### Step 3: Implement SecurityValidator

**File**: `loom/security/validator.py` (new)

Main implementation with all 4 layers.

### Step 4: Integrate into ToolOrchestrator

**File**: `loom/core/tool_orchestrator.py` (modify)

```python
# Add SecurityValidator support
class ToolOrchestrator:
    def __init__(
        self,
        tools: Dict[str, BaseTool],
        permission_manager: Optional[PermissionManager] = None,
        security_validator: Optional[SecurityValidator] = None,  # 🆕
        max_parallel: int = 5
    ):
        self.tools = tools
        self.permission_manager = permission_manager
        self.security_validator = security_validator  # 🆕
        self.max_parallel = max_parallel

    async def execute_one(self, tool_call: ToolCall):
        # ... existing code ...

        # 🆕 Security validation
        if self.security_validator:
            decision = await self.security_validator.validate(
                tool_call=tool_call,
                tool=tool,
                context={}
            )

            if not decision.allow:
                # Emit security error event
                yield AgentEvent(
                    type=AgentEventType.TOOL_ERROR,
                    tool_result=ToolResult(
                        tool_call_id=tool_call.id,
                        tool_name=tool_call.name,
                        content=f"Security check failed: {decision.reason}",
                        is_error=True
                    ),
                    error=SecurityError(decision.reason)
                )
                return

        # ... continue with execution ...
```

---

## 🧪 Testing Requirements

### Unit Tests

**File**: `tests/unit/test_security_validator.py`

**Test cases** (target 20-25 tests):

```python
class TestSecurityDecision:
    def test_decision_creation(self):
        """Test SecurityDecision creation."""
        ...

    def test_is_safe_property(self):
        """Test is_safe property logic."""
        ...


class TestPathSecurityValidator:
    def test_path_traversal_detection(self):
        """Test ../ detection."""
        ...

    def test_absolute_path_outside_workdir(self):
        """Test absolute path restrictions."""
        ...

    def test_system_path_blocking(self):
        """Test system path protection."""
        ...

    def test_safe_relative_path(self):
        """Test safe relative paths."""
        ...


class TestLayer1PermissionCheck:
    async def test_permission_allow(self):
        """Test permission layer allows valid tools."""
        ...

    async def test_permission_deny(self):
        """Test permission layer blocks denied tools."""
        ...


class TestLayer2CategoryCheck:
    async def test_general_category_allowed(self):
        """Test general category tools allowed."""
        ...

    async def test_destructive_requires_confirmation(self):
        """Test destructive tools require confirmation."""
        ...

    async def test_unknown_category_high_risk(self):
        """Test unknown categories flagged as high risk."""
        ...


class TestLayer3PathSecurity:
    async def test_blocks_path_traversal(self):
        """Test path traversal blocked."""
        ...

    async def test_blocks_system_paths(self):
        """Test system path access blocked."""
        ...

    async def test_allows_safe_paths(self):
        """Test safe paths allowed."""
        ...


class TestLayer4SandboxCheck:
    async def test_sandbox_recommendation(self):
        """Test sandbox recommended for safe ops."""
        ...


class TestSecurityValidatorIntegration:
    async def test_all_layers_pass(self):
        """Test all layers passing."""
        ...

    async def test_single_layer_failure(self):
        """Test single layer failure blocks execution."""
        ...

    async def test_multiple_layer_failures(self):
        """Test multiple layer failures."""
        ...

    async def test_audit_logging(self):
        """Test audit log captures decisions."""
        ...


class TestToolOrchestrationWithSecurity:
    async def test_security_blocks_dangerous_tool(self):
        """Test security validator blocks dangerous tools."""
        ...

    async def test_security_allows_safe_tool(self):
        """Test security validator allows safe tools."""
        ...
```

---

## ✅ Acceptance Criteria

- [ ] SecurityDecision model implemented
- [ ] PathSecurityValidator implemented
- [ ] SecurityValidator implemented with 4 layers
  - [ ] Layer 1: Permission check
  - [ ] Layer 2: Category validation
  - [ ] Layer 3: Path security
  - [ ] Layer 4: Sandbox support
- [ ] Integrated into ToolOrchestrator
- [ ] Test coverage ≥ 80%
  - [ ] 20-25 unit tests
  - [ ] All tests pass
- [ ] Audit logging works
- [ ] Path traversal prevented
- [ ] System paths protected
- [ ] Backward compatible

---

## 📦 Deliverables

1. **Core Implementation**
   - [ ] `loom/security/models.py` (~100 lines)
   - [ ] `loom/security/path_validator.py` (~150 lines)
   - [ ] `loom/security/validator.py` (~400 lines)

2. **Integration**
   - [ ] Modified `loom/core/tool_orchestrator.py`
   - [ ] Modified `loom/core/agent_executor.py`

3. **Tests**
   - [ ] `tests/unit/test_security_validator.py` (20-25 tests)
   - [ ] All tests passing

4. **Documentation**
   - [ ] Code docstrings complete
   - [ ] Example usage
   - [ ] `docs/TASK_2.2_COMPLETION_SUMMARY.md`

---

## 🔍 Testing Checklist

Before marking as complete:

- [ ] All unit tests pass
- [ ] Path traversal attacks blocked
- [ ] System paths protected
- [ ] Audit log captures decisions
- [ ] Integration with orchestrator works
- [ ] No regressions in existing tests
- [ ] Code coverage ≥ 80%
- [ ] Documentation complete

---

**Created**: 2025-10-25
**Last Updated**: 2025-10-25
**Status**: 🔄 In Progress
