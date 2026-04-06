"""事件总线 - V(e) = ΔH"""

from dataclasses import dataclass
from typing import Callable
import json
from pathlib import Path


@dataclass
class Event:
    """事件定义"""
    event_id: str
    source: str
    data: dict
    delta_H: float  # 信息熵增量
    timestamp: str


class EventBus:
    """M_f 事件总线"""

    def __init__(self, mf_path: Path):
        self.mf_path = mf_path
        self.mf_path.mkdir(parents=True, exist_ok=True)
        self.subscribers: dict[str, list[Callable]] = {}

    def publish(self, event: Event):
        """发布事件到 M_f"""
        event_file = self.mf_path / f"{event.event_id}.json"
        event_file.write_text(json.dumps({
            "event_id": event.event_id,
            "source": event.source,
            "data": event.data,
            "delta_H": event.delta_H,
            "timestamp": event.timestamp,
        }))

        # 通知订阅者
        for callback in self.subscribers.get(event.source, []):
            callback(event)

    def subscribe(self, source: str, callback: Callable):
        """订阅事件"""
        if source not in self.subscribers:
            self.subscribers[source] = []
        self.subscribers[source].append(callback)

    def read_events(self, since: str | None = None) -> list[Event]:
        """读取事件"""
        events = []
        for event_file in self.mf_path.glob("*.json"):
            data = json.loads(event_file.read_text())
            events.append(Event(**data))
        return events
