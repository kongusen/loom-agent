from __future__ import annotations

from typing import Any, Dict


class BaseCallback:
    async def on_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        return None

