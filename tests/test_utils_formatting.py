"""
Tests for Formatting Utilities
"""

import pytest
from loom.utils.formatting import ErrorFormatter


class TestErrorFormatter:
    """Test ErrorFormatter functionality."""

    def test_format_tool_error_basic(self):
        """Test basic tool error formatting."""
        error = Exception("Something went wrong")
        result = ErrorFormatter.format_tool_error(error, "test_tool")

        assert "## ❌ Tool Execution Failed: `test_tool`" in result
        assert "**Error Type**: `Exception`" in result
        assert "**Message**: Something went wrong" in result

    def test_format_tool_error_with_stdout(self):
        """Test formatting with stdout."""
        error = Exception("Error")
        error.stdout = "Command output"
        result = ErrorFormatter.format_tool_error(error, "test_tool")

        assert "**stdout**:" in result
        assert "Command output" in result

    def test_format_tool_error_with_stderr(self):
        """Test formatting with stderr."""
        error = Exception("Error")
        error.stderr = "Error message"
        result = ErrorFormatter.format_tool_error(error, "test_tool")

        assert "**stderr**:" in result
        assert "Error message" in result

    def test_hints_permission_denied(self):
        """Test hints for permission errors."""
        error = PermissionError("Permission denied")
        hints = ErrorFormatter._get_hints(error, "tool", "Permission denied")

        assert len(hints) > 0
        assert any("permission" in h.lower() for h in hints)

    def test_hints_file_not_found(self):
        """Test hints for file not found errors."""
        error = FileNotFoundError("File not found")
        hints = ErrorFormatter._get_hints(error, "tool", "File not found")

        assert len(hints) > 0
        assert any("file path" in h.lower() or "not found" in h.lower() for h in hints)

    def test_hints_syntax_error(self):
        """Test hints for syntax errors."""
        error = SyntaxError("Invalid syntax")
        hints = ErrorFormatter._get_hints(error, "tool", "SyntaxError")

        assert len(hints) > 0
        assert any("syntax" in h.lower() for h in hints)

    def test_hints_json_error(self):
        """Test hints for JSON decode errors."""
        error = ValueError("JSONDecodeError: Invalid JSON")
        hints = ErrorFormatter._get_hints(error, "tool", "JSONDecodeError")

        assert len(hints) > 0
        assert any("json" in h.lower() for h in hints)

    def test_hints_returncode_127(self):
        """Test hints for command not found."""
        error = Exception("Command failed")
        error.returncode = 127
        hints = ErrorFormatter._get_hints(error, "tool", "failed")

        assert len(hints) > 0
        assert any("command" in h.lower() or "path" in h.lower() for h in hints)

    def test_hints_returncode_nonzero(self):
        """Test hints for non-zero return code."""
        error = Exception("Command failed")
        error.returncode = 1
        hints = ErrorFormatter._get_hints(error, "tool", "failed")

        assert len(hints) > 0
        assert any("stderr" in h.lower() for h in hints)

    def test_hints_default(self):
        """Test default hints when no specific hint matches."""
        error = ValueError("Some error")
        hints = ErrorFormatter._get_hints(error, "tool", "Some error")

        assert len(hints) > 0
        assert any("arguments" in h.lower() for h in hints)

    def test_format_includes_suggestions_section(self):
        """Test that suggestions section is included when hints exist."""
        error = FileNotFoundError("File not found")
        result = ErrorFormatter.format_tool_error(error, "test_tool")

        assert "### 💡 Suggestions" in result

    def test_format_default_hint_when_no_match(self):
        """Test that default hint is provided when no specific hint matches."""
        error = ValueError("Error without specific hints")
        result = ErrorFormatter.format_tool_error(error, "test_tool")

        # Should have default hint in suggestions
        assert "### 💡 Suggestions" in result
        assert "Review the arguments provided to the tool" in result

    def test_format_with_context(self):
        """Test formatting with context parameter."""
        error = Exception("Error")
        context = {"arg1": "value1"}
        # Context is currently unused but should not error
        result = ErrorFormatter.format_tool_error(error, "test_tool", context=context)

        assert "## ❌ Tool Execution Failed" in result
