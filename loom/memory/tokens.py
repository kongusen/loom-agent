"""Token estimation helpers."""

from __future__ import annotations

from ..types import AssistantMessage, Message

_CHARS_PER_TOKEN = 4


def _estimate_tokens(text: str) -> int:
    return len(text) // _CHARS_PER_TOKEN + 1


def _msg_tokens(msg: Message) -> int:
    t = _estimate_tokens(msg.content if isinstance(msg.content, str) else str(msg.content))
    if isinstance(msg, AssistantMessage):
        for tc in msg.tool_calls:
            t += _estimate_tokens(tc.arguments) + _estimate_tokens(tc.name)
    return t


class EstimatorTokenizer:
    """Tokenizer implementation — char-ratio estimation."""

    def __init__(self, chars_per_token: int = _CHARS_PER_TOKEN) -> None:
        self._ratio = chars_per_token

    def count(self, text: str) -> int:
        return len(text) // self._ratio + 1

    def truncate(self, text: str, max_tokens: int) -> str:
        max_chars = max_tokens * self._ratio
        return text if len(text) <= max_chars else text[:max_chars]
