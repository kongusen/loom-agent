"""
Tests for LLM Event Validation

Tests the validate_llm_event() function to ensure it correctly validates
event formats from LLM implementations.
"""

import pytest
from loom.interfaces.llm import validate_llm_event


class TestLLMEventValidation:
    """Test suite for LLM event validation"""

    def test_valid_content_delta_event(self):
        """Valid content_delta event should pass"""
        event = {
            "type": "content_delta",
            "content": "Hello world"
        }
        # Should not raise
        validate_llm_event(event, strict=True)

    def test_valid_tool_calls_event(self):
        """Valid tool_calls event should pass"""
        event = {
            "type": "tool_calls",
            "tool_calls": [
                {
                    "id": "call_1",
                    "name": "search",
                    "arguments": {"query": "test"}
                }
            ]
        }
        # Should not raise
        validate_llm_event(event, strict=True)

    def test_valid_finish_event(self):
        """Valid finish event should pass"""
        event = {
            "type": "finish",
            "finish_reason": "stop"
        }
        # Should not raise
        validate_llm_event(event, strict=True)

    def test_invalid_event_not_dict(self):
        """Event must be a dict"""
        event = "not a dict"
        with pytest.raises(ValueError, match="must be a dict"):
            validate_llm_event(event, strict=True)

    def test_invalid_event_missing_type(self):
        """Event must have 'type' field"""
        event = {"content": "hello"}
        with pytest.raises(ValueError, match="must have 'type' field"):
            validate_llm_event(event, strict=True)

    def test_invalid_content_delta_missing_content(self):
        """content_delta must have 'content' field"""
        event = {"type": "content_delta"}
        with pytest.raises(ValueError, match="must have 'content' field"):
            validate_llm_event(event, strict=True)

    def test_invalid_content_delta_wrong_type(self):
        """content_delta.content must be str"""
        event = {
            "type": "content_delta",
            "content": 123  # Wrong type
        }
        with pytest.raises(ValueError, match="must be str"):
            validate_llm_event(event, strict=True)

    def test_invalid_tool_calls_missing_field(self):
        """tool_calls event must have 'tool_calls' field"""
        event = {"type": "tool_calls"}
        with pytest.raises(ValueError, match="must have 'tool_calls' field"):
            validate_llm_event(event, strict=True)

    def test_invalid_tool_calls_not_list(self):
        """tool_calls must be a list"""
        event = {
            "type": "tool_calls",
            "tool_calls": "not a list"
        }
        with pytest.raises(ValueError, match="must be a list"):
            validate_llm_event(event, strict=True)

    def test_invalid_tool_call_missing_required_fields(self):
        """Each tool call must have id, name, arguments"""
        event = {
            "type": "tool_calls",
            "tool_calls": [
                {"id": "call_1"}  # Missing name and arguments
            ]
        }
        with pytest.raises(ValueError, match="missing required fields"):
            validate_llm_event(event, strict=True)

    def test_invalid_tool_call_arguments_not_dict(self):
        """Tool call arguments must be dict"""
        event = {
            "type": "tool_calls",
            "tool_calls": [
                {
                    "id": "call_1",
                    "name": "search",
                    "arguments": "not a dict"  # Wrong type
                }
            ]
        }
        with pytest.raises(ValueError, match="arguments must be dict"):
            validate_llm_event(event, strict=True)

    def test_invalid_finish_missing_reason(self):
        """finish event must have 'finish_reason' field"""
        event = {"type": "finish"}
        with pytest.raises(ValueError, match="must have 'finish_reason' field"):
            validate_llm_event(event, strict=True)

    def test_invalid_finish_reason_not_str(self):
        """finish_reason must be str"""
        event = {
            "type": "finish",
            "finish_reason": 123  # Wrong type
        }
        with pytest.raises(ValueError, match="must be str"):
            validate_llm_event(event, strict=True)

    def test_unknown_event_type(self):
        """Unknown event types should raise error"""
        event = {"type": "unknown_type"}
        with pytest.raises(ValueError, match="Unknown event type"):
            validate_llm_event(event, strict=True)

    def test_non_strict_mode_warnings(self):
        """Non-strict mode should issue warnings instead of raising"""
        event = {
            "type": "content_delta",
            "content": 123  # Wrong type
        }
        # Should not raise in non-strict mode
        with pytest.warns(UserWarning, match="must be str"):
            validate_llm_event(event, strict=False)
