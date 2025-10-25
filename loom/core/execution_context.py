"""
Execution Context for tt Recursive Control Loop

Provides shared runtime configuration that persists across recursive calls.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, Any
from uuid import uuid4


@dataclass
class ExecutionContext:
    """
    Shared execution context for tt recursion.

    Contains runtime configuration and state that doesn't change
    between recursive calls. This is passed down the recursion chain
    alongside messages and TurnState.

    Design Principles:
    - Immutable configuration: working_dir, correlation_id don't change
    - Shared cancellation: cancel_token is shared across all recursive calls
    - Extensible: metadata dict for custom data

    Attributes:
        working_dir: Working directory for file operations
        correlation_id: Unique ID for request tracing
        cancel_token: Optional cancellation event (shared)
        git_context: Git repository context (future feature)
        project_context: Project-specific context (future feature)
        metadata: Additional runtime data

    Example:
        ```python
        context = ExecutionContext(
            working_dir=Path.cwd(),
            correlation_id="req-12345"
        )

        # All recursive tt calls share this context
        async for event in executor.tt(messages, turn_state, context):
            ...
        ```
    """

    working_dir: Path
    correlation_id: str
    cancel_token: Optional[asyncio.Event] = None
    git_context: Optional[Dict[str, Any]] = None
    project_context: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def create(
        working_dir: Optional[Path] = None,
        correlation_id: Optional[str] = None,
        cancel_token: Optional[asyncio.Event] = None,
        **metadata
    ) -> ExecutionContext:
        """
        Create execution context with defaults.

        Args:
            working_dir: Working directory (defaults to cwd)
            correlation_id: Request ID (defaults to new UUID)
            cancel_token: Cancellation event
            **metadata: Additional metadata

        Returns:
            ExecutionContext: New context
        """
        return ExecutionContext(
            working_dir=working_dir or Path.cwd(),
            correlation_id=correlation_id or str(uuid4()),
            cancel_token=cancel_token,
            metadata=metadata
        )

    def is_cancelled(self) -> bool:
        """
        Check if execution is cancelled.

        Returns:
            bool: True if cancel_token is set
        """
        return self.cancel_token is not None and self.cancel_token.is_set()

    def with_metadata(self, **kwargs) -> ExecutionContext:
        """
        Create new context with updated metadata.

        Args:
            **kwargs: Metadata updates

        Returns:
            ExecutionContext: New context with merged metadata
        """
        new_metadata = {**self.metadata, **kwargs}

        return ExecutionContext(
            working_dir=self.working_dir,
            correlation_id=self.correlation_id,
            cancel_token=self.cancel_token,
            git_context=self.git_context,
            project_context=self.project_context,
            metadata=new_metadata
        )

    def __repr__(self) -> str:
        """Human-readable representation."""
        return (
            f"ExecutionContext(cwd={self.working_dir}, "
            f"correlation_id={self.correlation_id[:8]}...)"
        )
