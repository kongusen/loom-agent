"""Steering Control: Simplified abort/pause signal management.

Replaces legacy EventBus with focus on cancel signals only.
For real-time steering, use cancel_token (US1 pattern) instead.
"""

from __future__ import annotations

import asyncio


class SteeringControl:
    """Lightweight steering control for abort/pause signals.

    Note: For cancellation, prefer using cancel_token (asyncio.Event) directly
    with Agent.run(input, cancel_token=token). This class is kept for legacy
    compatibility and may be removed in v5.0.0.
    """

    def __init__(self) -> None:
        self._abort_signal = asyncio.Event()
        self._pause_signal = asyncio.Event()

    def abort(self) -> None:
        """Signal abort request."""
        self._abort_signal.set()

    def is_aborted(self) -> bool:
        """Check if abort was requested."""
        return self._abort_signal.is_set()

    def pause(self) -> None:
        """Signal pause request."""
        self._pause_signal.set()

    def resume(self) -> None:
        """Clear pause signal."""
        self._pause_signal.clear()

    def is_paused(self) -> bool:
        """Check if paused."""
        return self._pause_signal.is_set()

    def reset(self) -> None:
        """Reset all signals."""
        self._abort_signal.clear()
        self._pause_signal.clear()
