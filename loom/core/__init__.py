"""
Loom Core - "The Atoms"
=======================

This module defines the fundamental interfaces and data structures.

## ⚛️ Atomic Units

### 1. Runnable (`Runnable`)
The universal interface for ANY executable component.
- **Protocol**: `await invoke(input) -> output`
- **Streaming**: `await stream(input) -> chunk_iterator`
- **Batching**: `await batch(inputs) -> outputs`
> EVERYTHING is a Runnable: Agent, LLM, Tool, and Sequence.

### 2. Message (`Message`)
The universal data packet flowing through the system.
- **SystemMessage**: Instructions, Context.
- **UserMessage**: Input, Query.
- **AssistantMessage**: Output, Thought, Tool Call.
- **ToolMessage**: Tool Execution Result.
"""

from .runnable import (
    Runnable,
    RunnableConfig,
    RunnableSequence,
    RunnableParallel,
    RunnableBranch,
)

from .message import (
    Message,
    BaseMessage,
    SystemMessage,
    UserMessage,
    AssistantMessage,
    ToolMessage,
    TextContent,
    ImageContent,
    AudioContent,
    VideoContent,
    ToolCall,
    FunctionCall,
    create_message,
    messages_to_openai_format,
)

__all__ = [
    # Runnable
    "Runnable",
    "RunnableConfig",
    "RunnableSequence",
    "RunnableParallel",
    "RunnableBranch",

    # Message
    "Message",
    "BaseMessage",
    "SystemMessage",
    "UserMessage",
    "AssistantMessage",
    "ToolMessage",
    "TextContent",
    "ImageContent",
    "AudioContent",
    "VideoContent",
    "ToolCall",
    "FunctionCall",
    "create_message",
    "messages_to_openai_format",
]
