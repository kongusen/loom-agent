"""Agent communication protocol"""

from ..types import Event


class CommunicationProtocol:
    """Protocol for agent-to-agent communication"""
    
    def __init__(self):
        self.messages: list[Event] = []
    
    def send(self, event: Event):
        """Send message"""
        self.messages.append(event)
    
    def receive(self, topic: str) -> list[Event]:
        """Receive messages for topic"""
        return [e for e in self.messages if e.topic == topic]
