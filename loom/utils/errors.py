"""Error definitions"""


class LoomError(Exception):
    """Base exception for Loom framework"""
    pass


class ProviderError(LoomError):
    """Base exception for provider failures."""
    pass


class ProviderUnavailableError(ProviderError):
    """Provider is unavailable or unreachable."""
    pass


class RateLimitError(ProviderError):
    """Provider rate-limit reached."""
    pass


class ToolError(LoomError):
    """Base exception for tool failures."""
    pass


class ToolNotFoundError(ToolError):
    """Tool was not found in registry."""
    pass


class ToolPermissionError(ToolError):
    """Tool invocation is denied by governance or permissions."""
    pass


class ToolExecutionError(ToolError):
    """Tool handler failed during execution."""
    pass


class ContextError(LoomError):
    """Base exception for context failures."""
    pass


class ContextOverflowError(ContextError):
    """Context exceeds max tokens (ρ >= 1.0)."""
    pass


class MaxDepthError(ContextError):
    """Max recursion depth exceeded."""
    pass


class VetoError(LoomError):
    """Harness veto error."""
    pass
