"""Test utils"""

from loom.utils import (
    ContextError,
    ContextOverflowError,
    LoomError,
    MaxDepthError,
    ProviderError,
    ProviderUnavailableError,
    RateLimitError,
    ToolError,
    ToolExecutionError,
    ToolNotFoundError,
    ToolPermissionError,
)


class TestUtils:
    """Test utils"""

    def test_loom_error(self):
        """Test LoomError"""
        error = LoomError("Test error")
        assert str(error) == "Test error"

    def test_context_overflow_error(self):
        """Test ContextOverflowError"""
        error = ContextOverflowError("Overflow")
        assert isinstance(error, LoomError)

    def test_max_depth_error(self):
        """Test MaxDepthError"""
        error = MaxDepthError("Max depth")
        assert isinstance(error, LoomError)

    def test_error_hierarchy_provider(self):
        error = ProviderUnavailableError("offline")
        assert isinstance(error, ProviderError)
        assert isinstance(error, LoomError)

    def test_error_hierarchy_rate_limit(self):
        error = RateLimitError("too many requests")
        assert isinstance(error, ProviderError)

    def test_error_hierarchy_tool(self):
        assert isinstance(ToolNotFoundError("missing"), ToolError)
        assert isinstance(ToolPermissionError("denied"), ToolError)
        assert isinstance(ToolExecutionError("boom"), ToolError)

    def test_error_hierarchy_context(self):
        error = ContextOverflowError("overflow")
        assert isinstance(error, ContextError)
