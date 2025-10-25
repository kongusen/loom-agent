"""
Security Models

Data models for security validation results.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional


class RiskLevel(str, Enum):
    """Security risk levels for tool execution."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    def __lt__(self, other):
        """Allow comparison of risk levels."""
        order = {
            RiskLevel.LOW: 0,
            RiskLevel.MEDIUM: 1,
            RiskLevel.HIGH: 2,
            RiskLevel.CRITICAL: 3
        }
        return order[self] < order[other]

    def __gt__(self, other):
        order = {
            RiskLevel.LOW: 0,
            RiskLevel.MEDIUM: 1,
            RiskLevel.HIGH: 2,
            RiskLevel.CRITICAL: 3
        }
        return order[self] > order[other]


@dataclass
class SecurityDecision:
    """
    Result of security validation.

    Attributes:
        allow: Whether the operation is allowed
        risk_level: Assessed risk level
        reason: Human-readable reason for decision
        failed_layers: List of security layers that failed
        warnings: Non-blocking warnings
    """
    allow: bool
    risk_level: RiskLevel
    reason: str
    failed_layers: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def is_safe(self) -> bool:
        """Check if decision is safe to execute."""
        return self.allow and self.risk_level in [RiskLevel.LOW, RiskLevel.MEDIUM]

    def __repr__(self) -> str:
        status = "ALLOWED" if self.allow else "BLOCKED"
        return f"SecurityDecision({status}, risk={self.risk_level.value}, reason='{self.reason}')"


@dataclass
class PathSecurityResult:
    """
    Result of path security validation.

    Attributes:
        is_safe: Whether the path is safe to access
        normalized_path: Resolved absolute path
        warnings: Non-critical warnings
        violations: Security violations found
    """
    is_safe: bool
    normalized_path: str
    warnings: List[str] = field(default_factory=list)
    violations: List[str] = field(default_factory=list)

    def __repr__(self) -> str:
        status = "SAFE" if self.is_safe else "UNSAFE"
        return f"PathSecurityResult({status}, violations={len(self.violations)})"
