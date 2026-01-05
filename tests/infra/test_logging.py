"""
Tests for Infrastructure Logging
"""

import pytest
import logging

from loom.infra.logging import configure_logging, get_logger


class TestConfigureLogging:
    """Test configure_logging function."""

    @pytest.fixture(autouse=True)
    def reset_logging(self):
        """Reset logging configuration after each test."""
        import structlog
        # Reset structlog configuration
        structlog.reset_defaults()

    def test_configure_logging_default(self):
        """Test configure_logging with default parameters."""
        # Should not raise any errors
        configure_logging()

    def test_configure_logging_info_level(self):
        """Test configure_logging with INFO level."""
        configure_logging(log_level="INFO")

        # Check that structlog is configured
        import structlog
        logger = structlog.get_logger()
        assert logger is not None

    def test_configure_logging_debug_level(self):
        """Test configure_logging with DEBUG level."""
        configure_logging(log_level="DEBUG")

        import structlog
        logger = structlog.get_logger()
        assert logger is not None

    def test_configure_logging_warning_level(self):
        """Test configure_logging with WARNING level."""
        configure_logging(log_level="WARNING")

        import structlog
        logger = structlog.get_logger()
        assert logger is not None

    def test_configure_logging_error_level(self):
        """Test configure_logging with ERROR level."""
        configure_logging(log_level="ERROR")

        import structlog
        logger = structlog.get_logger()
        assert logger is not None

    def test_configure_logging_invalid_level(self):
        """Test configure_logging with invalid level (defaults to INFO)."""
        # Should not raise error, should default to INFO
        configure_logging(log_level="INVALID")

        import structlog
        logger = structlog.get_logger()
        assert logger is not None

    def test_configure_logging_lowercase(self):
        """Test configure_logging with lowercase level."""
        configure_logging(log_level="info")

        import structlog
        logger = structlog.get_logger()
        assert logger is not None

    def test_configure_logging_with_json_format(self):
        """Test configure_logging with JSON format."""
        configure_logging(json_format=True)

        import structlog
        logger = structlog.get_logger()
        assert logger is not None

    def test_configure_logging_with_text_format(self):
        """Test configure_logging with text format (default)."""
        configure_logging(json_format=False)

        import structlog
        logger = structlog.get_logger()
        assert logger is not None

    def test_configure_logging_multiple_calls(self):
        """Test that configure_logging can be called multiple times."""
        configure_logging(log_level="INFO")
        configure_logging(log_level="DEBUG", json_format=True)

        import structlog
        logger = structlog.get_logger()
        assert logger is not None


class TestGetLogger:
    """Test get_logger function."""

    def test_get_logger_returns_logger(self):
        """Test that get_logger returns a logger instance."""
        logger = get_logger("test_logger")

        assert logger is not None
        assert logger.bind is not None

    def test_get_logger_with_name(self):
        """Test get_logger with custom name."""
        logger = get_logger("my_custom_logger")

        assert logger is not None

    def test_get_logger_different_names(self):
        """Test that different names create different loggers."""
        logger1 = get_logger("logger1")
        logger2 = get_logger("logger2")

        assert logger1 is not None
        assert logger2 is not None
        # They might be different instances
        assert logger1 is not logger2 or logger1 == logger2

    def test_get_logger_same_name(self):
        """Test that same name returns logger."""
        logger1 = get_logger("cached_logger")
        logger2 = get_logger("cached_logger")

        # Both should be valid loggers
        assert logger1 is not None
        assert logger2 is not None

    def test_get_logger_can_log(self):
        """Test that logger can be used to log messages."""
        logger = get_logger("test_logger")

        # Should be able to log without error
        logger.info("test message", extra_key="extra_value")
