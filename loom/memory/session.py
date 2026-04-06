"""Session memory (M_s)"""

from dataclasses import dataclass, field
from ..types import Message


@dataclass
class SessionMemory:
    """Short-term session memory"""
    messages: list[Message] = field(default_factory=list)
    max_size: int = 100
    
    def add(self, message: Message):
        """Add message to session"""
        self.messages.append(message)
        if len(self.messages) > self.max_size:
            self.messages = self.messages[-self.max_size:]
    
    def get_recent(self, n: int = 10) -> list[Message]:
        """Get recent messages"""
        return self.messages[-n:]
    
    def clear(self):
        """Clear session memory"""
        self.messages.clear()
