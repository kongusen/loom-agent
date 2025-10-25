"""
Path Security Validator

Validates file paths for security issues like path traversal and system path access.
"""

from pathlib import Path
from typing import List, Optional
from loom.security.models import PathSecurityResult


# System paths that should never be accessed
SYSTEM_PATHS = [
    "/etc",
    "/sys",
    "/proc",
    "/dev",
    "/boot",
    "/root",
    "/var/log",
    "/bin",
    "/sbin",
    "/usr/bin",
    "/usr/sbin",
]


class PathSecurityValidator:
    """
    Validate file paths for security issues.

    Checks for:
    - Path traversal attacks (../)
    - Absolute paths outside working directory
    - System path access
    - Invalid path constructions

    Example:
        ```python
        validator = PathSecurityValidator(working_dir=Path("/Users/project"))

        # Safe path
        result = validator.validate_path("src/main.py")
        assert result.is_safe

        # Path traversal attempt
        result = validator.validate_path("../../etc/passwd")
        assert not result.is_safe
        ```
    """

    def __init__(self, working_dir: Optional[Path] = None):
        """
        Initialize path validator.

        Args:
            working_dir: Working directory to enforce boundaries (defaults to cwd)
        """
        self.working_dir = (working_dir or Path.cwd()).resolve()

    def validate_path(self, path: str) -> PathSecurityResult:
        """
        Validate a file path for security issues.

        Args:
            path: File path to validate

        Returns:
            PathSecurityResult with validation outcome
        """
        violations: List[str] = []
        warnings: List[str] = []
        normalized_path = path

        # Check 1: Detect explicit path traversal
        if ".." in path:
            violations.append("Path traversal detected (..)")

        # Check 2: Resolve and validate boundaries
        try:
            # Handle both relative and absolute paths
            if Path(path).is_absolute():
                resolved = Path(path).resolve()
            else:
                resolved = (self.working_dir / path).resolve()

            normalized_path = str(resolved)

            # Check if within working directory
            try:
                resolved.relative_to(self.working_dir)
            except ValueError:
                violations.append(
                    f"Path outside working directory: {resolved} "
                    f"(working dir: {self.working_dir})"
                )

            # Check 3: System path protection
            for sys_path in SYSTEM_PATHS:
                if str(resolved).startswith(sys_path):
                    violations.append(
                        f"System path access denied: {sys_path}"
                    )
                    break

        except Exception as e:
            violations.append(f"Path resolution failed: {e}")

        is_safe = len(violations) == 0

        return PathSecurityResult(
            is_safe=is_safe,
            normalized_path=normalized_path,
            warnings=warnings,
            violations=violations
        )

    def is_safe_path(self, path: str) -> bool:
        """
        Quick check if path is safe.

        Args:
            path: Path to check

        Returns:
            True if path is safe
        """
        return self.validate_path(path).is_safe
