"""Agent communication protocol"""

from ..types import CoordinationEvent


class CommunicationProtocol:
    """Protocol for agent-to-agent communication"""

    def __init__(self):
        self.messages: list[CoordinationEvent] = []

    def send(self, event: CoordinationEvent):
        """Send message"""
        self.messages.append(event)

    def receive(self, topic: str) -> list[CoordinationEvent]:
        """Receive messages for topic"""
        return [e for e in self.messages if e.topic == topic]
