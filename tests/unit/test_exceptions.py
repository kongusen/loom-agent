"""
Tests for Loom Exceptions
"""

import pytest

from loom.exceptions import LoomError, TaskComplete


class TestLoomError:
    """Test suite for LoomError"""

    def test_loom_error_base_exception(self):
        """Test LoomError is an Exception subclass"""
        assert issubclass(LoomError, Exception)

    def test_loom_error_can_be_raised(self):
        """Test LoomError can be raised"""
        with pytest.raises(LoomError):
            raise LoomError("Test error")

    def test_loom_error_message(self):
        """Test LoomError message"""
        error = LoomError("Test message")
        assert str(error) == "Test message"

    def test_loom_error_inheritance(self):
        """Test TaskComplete inherits from LoomError"""
        assert issubclass(TaskComplete, LoomError)


class TestTaskComplete:
    """Test suite for TaskComplete"""

    def test_task_complete_creation(self):
        """Test creating TaskComplete exception"""
        exception = TaskComplete("Task completed successfully")
        assert exception.message == "Task completed successfully"

    def test_task_complete_string_representation(self):
        """Test TaskComplete string representation"""
        exception = TaskComplete("Done!")
        assert "Task completed:" in str(exception)
        assert "Done!" in str(exception)

    def test_task_complete_can_be_raised(self):
        """Test TaskComplete can be raised"""
        with pytest.raises(TaskComplete) as exc_info:
            raise TaskComplete("Test completion")

        assert exc_info.value.message == "Test completion"

    def test_task_complete_message_attribute(self):
        """Test TaskComplete has message attribute"""
        exception = TaskComplete("Test message")
        assert hasattr(exception, "message")
        assert exception.message == "Test message"

    def test_task_complete_empty_message(self):
        """Test TaskComplete with empty message"""
        exception = TaskComplete("")
        assert exception.message == ""
        assert "Task completed:" in str(exception)

    def test_task_complete_unicode_message(self):
        """Test TaskComplete with unicode characters"""
        message = "任务完成 🎉"
        exception = TaskComplete(message)
        assert exception.message == message

    def test_task_complete_long_message(self):
        """Test TaskComplete with long message"""
        long_message = "x" * 1000
        exception = TaskComplete(long_message)
        assert exception.message == long_message
