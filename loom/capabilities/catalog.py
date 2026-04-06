"""Capability catalog"""

from .registry import Capability


class CapabilityCatalog:
    """Catalog of available capabilities"""
    
    def __init__(self):
        self.catalog: list[Capability] = []
    
    def add(self, capability: Capability):
        """Add capability to catalog"""
        self.catalog.append(capability)
    
    def search(self, query: str) -> list[Capability]:
        """Search capabilities"""
        return [c for c in self.catalog if query.lower() in c.name.lower()]
