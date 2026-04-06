"""Working memory"""

from ..types import Dashboard


class WorkingMemory:
    """Working memory for current task"""
    
    def __init__(self):
        self.dashboard = Dashboard()
        self.scratch_pad: dict = {}
    
    def update_dashboard(self, **kwargs):
        """Update dashboard fields"""
        for key, value in kwargs.items():
            if hasattr(self.dashboard, key):
                setattr(self.dashboard, key, value)
    
    def set_scratch(self, key: str, value):
        """Set scratch pad value"""
        self.scratch_pad[key] = value
    
    def get_scratch(self, key: str):
        """Get scratch pad value"""
        return self.scratch_pad.get(key)
