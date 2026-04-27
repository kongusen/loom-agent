"""Typed stream events for Mode B (full-stream + event annotation).

Every token the agent emits carries a ``type`` discriminant so frontends can
render thinking tokens, tool invocations, tool results, and final text
independently — matching the behaviour of Claude.ai / ChatGPT agent mode.

Usage::

    async for event in agent.run_streaming("research quantum computing"):
        if event.type == "text_delta":
            print(event.delta, end="", flush=True)
        elif event.type == "tool_call":
            print(f"\\n[→ {event.name}({event.arguments})]")
        elif event.type == "tool_result":
            print(f"[← {event.name}: {event.content[:80]}]")
        elif event.type == "done":
            print(f"\\nFinished in {event.iterations} iterations")
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ThinkingDelta:
    """Streaming token from the model's extended-thinking block.

    Only emitted by providers that surface chain-of-thought reasoning
    (e.g. Claude with extended thinking enabled).
    """

    type: str = "thinking"
    delta: str = ""


@dataclass
class TextDelta:
    """One streaming text token from the assistant's final answer."""

    type: str = "text_delta"
    delta: str = ""


@dataclass
class ToolCallEvent:
    """The LLM decided to call a tool.

    Emitted *once* after the provider has fully assembled the tool-call
    arguments (not mid-stream), so ``arguments`` is always a complete dict.
    """

    type: str = "tool_call"
    id: str = ""
    name: str = ""
    arguments: dict = field(default_factory=dict)


@dataclass
class ToolResultEvent:
    """A tool finished executing."""

    type: str = "tool_result"
    tool_call_id: str = ""
    name: str = ""
    content: str = ""
    is_error: bool = False


@dataclass
class DoneEvent:
    """The agent loop finished (goal reached or max iterations)."""

    type: str = "done"
    output: str = ""
    iterations: int = 0
    status: str = "success"


@dataclass
class ErrorEvent:
    """A fatal error aborted the streaming run."""

    type: str = "error"
    message: str = ""


# Union alias used in type annotations throughout the framework.
StreamEvent = ThinkingDelta | TextDelta | ToolCallEvent | ToolResultEvent | DoneEvent | ErrorEvent
