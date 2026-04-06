"""Token counting utilities"""


def count_tokens(text: str, model: str = "claude-3-5-sonnet-20241022") -> int:
    """Estimate token count (simplified)"""
    # Rough estimation: ~4 chars per token
    return len(text) // 4


def count_messages_tokens(messages: list) -> int:
    """Count tokens in message list"""
    total = 0
    for msg in messages:
        if hasattr(msg, 'content'):
            total += count_tokens(msg.content)
    return total
