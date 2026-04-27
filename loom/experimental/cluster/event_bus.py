"""事件总线 - V(e) = ΔH"""

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ClusterEvent:
    """事件定义"""

    event_id: str
    source: str
    data: dict
    delta_H: float  # 信息熵增量
    timestamp: str


class ClusterEventBus:
    """M_f 事件总线"""

    def __init__(self, mf_path: Path):
        self.mf_path = mf_path
        self.mf_path.mkdir(parents=True, exist_ok=True)
        self.subscribers: dict[str, list[Callable]] = {}

    def publish(self, event: ClusterEvent):
        """发布事件到 M_f"""
        event_file = self.mf_path / f"{event.event_id}.json"
        event_file.write_text(
            json.dumps(
                {
                    "event_id": event.event_id,
                    "source": event.source,
                    "data": event.data,
                    "delta_H": event.delta_H,
                    "timestamp": event.timestamp,
                }
            )
        )

        # 通知订阅者
        for callback in self.subscribers.get(event.source, []):
            callback(event)

    def subscribe(self, source: str, callback: Callable):
        """订阅事件"""
        if source not in self.subscribers:
            self.subscribers[source] = []
        self.subscribers[source].append(callback)

    def read_events(self, since: str | None = None) -> list[ClusterEvent]:
        """读取事件

        Args:
            since: 时间戳过滤（当前未使用，预留用于未来过滤功能）
        """
        _ = since  # 预留参数，未来用于时间过滤
        events = []
        for event_file in self.mf_path.glob("*.json"):
            data = json.loads(event_file.read_text())
            events.append(ClusterEvent(**data))
        return events


# Backward-compatible aliases for older cluster imports.
Event = ClusterEvent
EventBus = ClusterEventBus
