from __future__ import annotations

from typing import Iterable

from loom.core.types import Message


def estimate_tokens(text: str) -> int:
    """粗略估算 token 数：采用字符数/4 的启发式。
    生产中应接入具体模型的 tokenizer。
    """
    if not text:
        return 0
    return max(1, len(text) // 4)


def count_messages_tokens(messages: Iterable[Message]) -> int:
    return sum(estimate_tokens(m.content) for m in messages)

