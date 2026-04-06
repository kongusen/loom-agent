"""Capability loader"""

from .registry import Capability, CapabilityRegistry
from ..tools import ToolRegistry


class CapabilityLoader:
    """Load capabilities progressively"""

    def __init__(self, capability_registry: CapabilityRegistry, tool_registry: ToolRegistry):
        self.capability_registry = capability_registry
        self.tool_registry = tool_registry
        self.loaded: set[str] = set()

    def load(self, capability_name: str) -> bool:
        """Load a capability and activate its tools"""
        if capability_name in self.loaded:
            return True
        capability = self.capability_registry.get(capability_name)
        if not capability:
            return False
        # Resolve dependencies first
        for dep in getattr(capability, "dependencies", []):
            self.load(dep)
        # Activate via registry (registers tools + injects skill context)
        self.capability_registry.activate(capability_name, self.tool_registry)
        self.loaded.add(capability_name)
        return True

    def unload(self, capability_name: str) -> bool:
        """Unload a capability and deactivate its tools"""
        if capability_name not in self.loaded:
            return False
        self.capability_registry.deactivate(capability_name, self.tool_registry)
        self.loaded.discard(capability_name)
        return True

    def is_loaded(self, capability_name: str) -> bool:
        return capability_name in self.loaded
