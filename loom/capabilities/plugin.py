"""Plugin system"""

from abc import ABC, abstractmethod


class Plugin(ABC):
    """Plugin interface"""
    
    @abstractmethod
    def on_load(self, agent):
        """Called when plugin is loaded"""
        pass
    
    @abstractmethod
    def on_unload(self):
        """Called when plugin is unloaded"""
        pass


class PluginManager:
    """Manage plugins"""
    
    def __init__(self):
        self.plugins: dict[str, Plugin] = {}
    
    def load_plugin(self, name: str, plugin: Plugin, agent):
        """Load a plugin"""
        plugin.on_load(agent)
        self.plugins[name] = plugin
    
    def unload_plugin(self, name: str):
        """Unload a plugin"""
        if name in self.plugins:
            self.plugins[name].on_unload()
            del self.plugins[name]
