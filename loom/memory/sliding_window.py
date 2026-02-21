"""L1: Sliding window — recent messages in original form."""

from __future__ import annotations

from collections import deque

from ..types import Message
from .tokens import _msg_tokens


class SlidingWindow:
    """L1: Recent messages in original form. FIFO eviction."""

    name = "sliding_window"

    def __init__(self, token_budget: int = 8000) -> None:
        self.token_budget = token_budget
        self.current_tokens = 0
        self._messages: deque[tuple[Message, int]] = deque()

    def add(self, msg: Message) -> list[Message]:
        tokens = _msg_tokens(msg)
        self._messages.append((msg, tokens))
        self.current_tokens += tokens
        evicted: list[Message] = []
        while self.current_tokens > self.token_budget and len(self._messages) > 1:
            old_msg, old_tok = self._messages.popleft()
            self.current_tokens -= old_tok
            evicted.append(old_msg)
        return evicted

    def get_messages(self) -> list[Message]:
        return [m for m, _ in self._messages]

    def clear(self) -> None:
        self._messages.clear()
        self.current_tokens = 0
