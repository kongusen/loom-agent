"""Test utils"""

from loom.utils import ContextOverflowError, LoomError, MaxDepthError


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
