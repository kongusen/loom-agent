"""Event types for multi-agent communication"""

import time
from dataclasses import dataclass


@dataclass
class CoordinationEvent:
    """Event definition - V(e) = ΔH"""

    id: str
    sender: str
    topic: str
    payload: dict
    delta_h: float
    priority: str
    timestamp: float = 0.0

    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()


@dataclass
class HeartbeatEvent:
    """Heartbeat perception event"""

    source: str
    event_type: str
    data: dict
    delta_h: float
    timestamp: float = 0.0

    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()
