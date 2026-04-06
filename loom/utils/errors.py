"""Error definitions"""


class LoomError(Exception):
    """Base exception for Loom framework"""
    pass


class ContextOverflowError(LoomError):
    """Context exceeds max tokens (ρ >= 1.0)"""
    pass


class MaxDepthError(LoomError):
    """Max recursion depth exceeded"""
    pass


class ToolError(LoomError):
    """Tool execution error"""
    pass


class VetoError(LoomError):
    """Harness veto error"""
    pass
