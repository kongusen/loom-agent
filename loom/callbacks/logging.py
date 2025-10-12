from __future__ import annotations

from typing import Any, Dict

from .base import BaseCallback


class LoggingCallback(BaseCallback):
    async def on_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        # 最小实现：打印事件
        print(f"[loom] {event_type}: {payload}")

