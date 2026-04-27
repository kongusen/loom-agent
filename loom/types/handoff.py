"""HandoffArtifact - structured output from context renewal"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class HandoffArtifact:
    """Structured handoff document produced by ContextRenewer.renew().

    Passed to the next sprint so it can cold-start with full context awareness.
    """

    goal: str                                  # original goal, never compressed
    sprint: int                                # which renew/sprint number this is
    progress_summary: str                      # what has been done (from goal_progress / scratchpad)
    produced_artifacts: dict[str, str]         # {name: description} of outputs created
    open_tasks: list[str]                      # remaining plan steps
    context_snapshot: dict                     # key dashboard fields at renew time
    handoff_ts: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_system_prompt(self) -> str:
        """Render as Markdown system message for cold-starting the next sprint."""
        artifacts_md = "\n".join(
            f"- **{name}**: {desc}"
            for name, desc in self.produced_artifacts.items()
        ) or "_(none)_"

        open_tasks_md = "\n".join(
            f"- {task}" for task in self.open_tasks
        ) or "_(none)_"

        return f"""# Handoff Document (Sprint {self.sprint})

## Goal
{self.goal}

## Progress Summary
{self.progress_summary or '_(no progress recorded)_'}

## Produced Artifacts
{artifacts_md}

## Open Tasks
{open_tasks_md}

## Context Snapshot
- rho: {self.context_snapshot.get('rho', 'N/A')}
- error_count: {self.context_snapshot.get('error_count', 'N/A')}
- depth: {self.context_snapshot.get('depth', 'N/A')}

_Handoff generated at {self.handoff_ts}_
"""
