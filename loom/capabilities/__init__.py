"""Capability system"""

from .registry import Capability, CapabilityRegistry
from .loader import CapabilityLoader
from .catalog import CapabilityCatalog
from .plugin import Plugin, PluginManager

__all__ = [
    "Capability",
    "CapabilityRegistry",
    "CapabilityLoader",
    "CapabilityCatalog",
    "Plugin",
    "PluginManager",
]
