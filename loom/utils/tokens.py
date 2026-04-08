"""Token counting utilities"""


def count_tokens(text: str, model: str = "claude-3-5-sonnet-20241022") -> int:
    """Estimate token count (simplified)

    Args:
        text: 文本内容
        model: 模型名称（预留参数，未来用于不同模型的 token 计算）
    """
    _ = model  # 预留参数，未来用于模型特定的 token 计算
    # Rough estimation: ~4 chars per token
    return len(text) // 4


def count_messages_tokens(messages: list) -> int:
    """Count tokens in message list"""
    total = 0
    for msg in messages:
        if hasattr(msg, 'content'):
            total += count_tokens(msg.content)
    return total
