"""Event bus - V(e) = ΔH

定理二：通信协议
T2.1: publish(e) 当且仅当 ΔH(e) > δ_min
T2.2: H(payload) > ε → compress，保持 ΔH ≈ 不变
T2.3: 任务难(H_task高) ≠ 事件重要(ΔH高)
"""

from typing import Callable
from ..types import Event


class EventBus:
    """Event bus for multi-agent communication via M_f"""

    def __init__(self, delta_min: float = 0.1):
        self.delta_min = delta_min  # δ_min
        self._subscribers: dict[str, list[Callable]] = {}
        self.published_events: list[Event] = []
    
    def publish(self, event: Event):
        """Publish event if ΔH > δ_min"""
        if event.delta_h < self.delta_min:
            return
        
        for callback in self._subscribers.get(event.topic, []):
            callback(event)
    
    def subscribe(self, topic: str, callback: Callable):
        """Subscribe to topic"""
        if topic not in self._subscribers:
            self._subscribers[topic] = []
        self._subscribers[topic].append(callback)
    
    def unsubscribe(self, topic: str, callback: Callable):
        """Unsubscribe from topic"""
        if topic in self._subscribers:
            self._subscribers[topic].remove(callback)

    def publish(self, event: Event):
        """T2.1: publish(e) 当且仅当 ΔH(e) > δ_min"""
        if event.delta_h < self.delta_min:
            return  # 信息熵增量太小，不发布
        
        self.published_events.append(event)
        
        for callback in self._subscribers.get(event.topic, []):
            callback(event)

    def subscribe(self, topic: str, callback: Callable):
        """Subscribe to topic"""
        if topic not in self._subscribers:
            self._subscribers[topic] = []
        self._subscribers[topic].append(callback)

    def unsubscribe(self, topic: str, callback: Callable):
        """Unsubscribe from topic"""
        if topic in self._subscribers:
            self._subscribers[topic].remove(callback)
