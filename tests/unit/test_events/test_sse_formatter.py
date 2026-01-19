"""
Tests for SSE Formatter
"""

import pytest

from loom.events.sse_formatter import SSEFormatter


class TestSSEFormatter:
    """Test suite for SSEFormatter"""

    def test_format_sse_message_basic(self):
        """Test basic SSE message formatting"""
        result = SSEFormatter.format_sse_message("update", "test data")

        expected = "event: update\ndata: test data\n\n"
        assert result == expected

    def test_format_sse_message_with_id(self):
        """Test SSE message with ID"""
        result = SSEFormatter.format_sse_message("update", "test data", "msg123")

        lines = result.strip().split("\n")
        assert "id: msg123" in lines
        assert "event: update" in lines
        assert "data: test data" in lines

    def test_format_sse_message_empty_data(self):
        """Test SSE message with empty data"""
        result = SSEFormatter.format_sse_message("update", "")

        expected = "event: update\ndata: \n\n"
        assert result == expected

    def test_format_sse_message_multiline_data(self):
        """Test SSE message with multiline data"""
        data = "line1\nline2\nline3"
        result = SSEFormatter.format_sse_message("update", data)

        assert "event: update" in result
        assert "data: line1\nline2\nline3" in result

    def test_format_sse_message_with_special_characters(self):
        """Test SSE message with special characters in data"""
        data = "data with \"quotes\" and 'apostrophes'"
        result = SSEFormatter.format_sse_message("update", data)

        assert "event: update" in result
        assert "data: data with \"quotes\" and 'apostrophes'" in result

    def test_format_sse_message_with_unicode(self):
        """Test SSE message with unicode characters"""
        data = "Hello 世界 🌍"
        result = SSEFormatter.format_sse_message("update", data)

        assert "event: update" in result
        assert "data: Hello 世界 🌍" in result

    def test_format_sse_message_endsWith_newline(self):
        """Test that SSE message ends with double newline"""
        result = SSEFormatter.format_sse_message("update", "data")

        assert result.endswith("\n\n")

    def test_format_sse_message_none_id(self):
        """Test SSE message with None ID (should not include id line)"""
        result = SSEFormatter.format_sse_message("update", "data", None)

        lines = result.strip().split("\n")
        assert "id:" not in lines
        assert "event: update" in lines
        assert "data: data" in lines

    def test_format_sse_message_empty_id(self):
        """Test SSE message with empty string ID"""
        result = SSEFormatter.format_sse_message("update", "data", "")

        # Empty string is falsy, so no id line
        lines = result.strip().split("\n")
        assert "id:" not in lines

    def test_format_sse_message_long_id(self):
        """Test SSE message with long ID"""
        long_id = "msg-" + "x" * 100
        result = SSEFormatter.format_sse_message("update", "data", long_id)

        assert f"id: {long_id}" in result

    def test_format_sse_message_various_event_types(self):
        """Test various event type names"""
        event_types = ["message", "error", "done", "progress", "custom-event"]

        for event_type in event_types:
            result = SSEFormatter.format_sse_message(event_type, "data")
            assert f"event: {event_type}" in result

    def test_format_sse_message_data_with_colon(self):
        """Test data containing colon characters"""
        data = "key:value"
        result = SSEFormatter.format_sse_message("update", data)

        assert "data: key:value" in result

    def test_format_sse_message_data_with_newline_handling(self):
        """Test that newlines in data are preserved"""
        data = "first line\nsecond line"
        result = SSEFormatter.format_sse_message("update", data)

        # The data should preserve the newline
        assert "data: first line\nsecond line" in result

    def test_format_sse_message_json_data(self):
        """Test SSE message with JSON data"""
        import json

        data = json.dumps({"status": "ok", "value": 42})
        result = SSEFormatter.format_sse_message("update", data)

        assert "event: update" in result
        assert f"data: {data}" in result

    def test_format_sse_message_numeric_data(self):
        """Test SSE message with numeric data converted to string"""
        result = SSEFormatter.format_sse_message("update", "42")

        assert "data: 42" in result

    def test_format_sse_message_order_of_fields(self):
        """Test that fields are in correct order: id, event, data"""
        result = SSEFormatter.format_sse_message("test", "data", "id123")
        lines = [l for l in result.split("\n") if l.strip()]

        assert lines[0].startswith("id:")
        assert lines[1].startswith("event:")
        assert lines[2].startswith("data:")

    def test_format_sse_message_is_static_method(self):
        """Test that format_sse_message is a static method"""
        # Can be called without instantiating
        result = SSEFormatter.format_sse_message("test", "data")
        assert result is not None

    def test_format_sse_message_multiple_calls(self):
        """Test multiple consecutive calls produce correct results"""
        messages = []
        for i in range(3):
            msg = SSEFormatter.format_sse_message("event", f"data{i}", f"id{i}")
            messages.append(msg)

        for i, msg in enumerate(messages):
            assert f"id: id{i}" in msg
            assert "event: event" in msg
            assert f"data: data{i}" in msg

    def test_format_sse_message_empty_event_type(self):
        """Test with empty event type"""
        result = SSEFormatter.format_sse_message("", "data")

        assert "event: " in result
        assert "data: data" in result
