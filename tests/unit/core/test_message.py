
import pytest
from loom.core.message import (
    BaseMessage, SystemMessage, UserMessage, AssistantMessage, ToolMessage,
    TextContent, ImageContent, ToolCall, FunctionCall,
    create_message, messages_to_openai_format
)

def test_message_creation():
    # System
    sys_msg = SystemMessage(content="You are a helper")
    assert sys_msg.role == "system"
    assert sys_msg.content == "You are a helper"

    # User (Text)
    user_msg = UserMessage(content="Hello")
    assert user_msg.role == "user"
    assert user_msg.content == "Hello"

    # Assistant
    ast_msg = AssistantMessage(content="Hi there")
    assert ast_msg.role == "assistant"
    assert ast_msg.tool_calls is None

def test_user_message_multimodal():
    # User (Image)
    user_msg_img = UserMessage(content="Look at this", images=["http://example.com/img.png"])
    assert isinstance(user_msg_img.content, list)
    assert len(user_msg_img.content) == 2
    assert isinstance(user_msg_img.content[0], TextContent)
    assert isinstance(user_msg_img.content[1], ImageContent)
    assert user_msg_img.content[1].image_url == "http://example.com/img.png"

def test_assistant_tool_call():
    tool_call = ToolCall(
        function=FunctionCall(name="search", arguments='{"q": "python"}')
    )
    msg = AssistantMessage(tool_calls=[tool_call])
    assert msg.role == "assistant"
    assert len(msg.tool_calls) == 1
    assert msg.tool_calls[0].function.name == "search"

def test_openai_format_conversion():
    # 1. Simple Text
    msg = UserMessage(content="Hello")
    openai_fmt = msg.to_openai_format()
    assert openai_fmt == {"role": "user", "content": "Hello"}

    # 2. Tool Call
    tool_call = ToolCall(
        id="call_123",
        function=FunctionCall(name="calc", arguments='{"x": 1}')
    )
    ast_msg = AssistantMessage(tool_calls=[tool_call])
    openai_fmt_ast = ast_msg.to_openai_format()
    assert openai_fmt_ast["role"] == "assistant"
    assert "content" not in openai_fmt_ast  # explicit None content usually omitted or None
    assert openai_fmt_ast["tool_calls"][0]["id"] == "call_123"
    assert openai_fmt_ast["tool_calls"][0]["function"]["name"] == "calc"

def test_factory_function():
    msg = create_message("user", "Hello factory")
    assert isinstance(msg, UserMessage)
    assert msg.content == "Hello factory"

    with pytest.raises(ValueError):
        create_message("unknown_role", "content")
