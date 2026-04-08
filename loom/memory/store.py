"""Memory store adapters"""

from abc import ABC, abstractmethod


class MemoryStore(ABC):
    """Abstract memory store"""

    @abstractmethod
    def save(self, key: str, value: dict):
        pass

    @abstractmethod
    def load(self, key: str) -> dict | None:
        pass


class InMemoryStore(MemoryStore):
    """In-memory store"""

    def __init__(self):
        self.data: dict[str, dict] = {}

    def save(self, key: str, value: dict):
        self.data[key] = value

    def load(self, key: str) -> dict | None:
        return self.data.get(key)
