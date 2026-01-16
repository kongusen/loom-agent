"""
Context Sanitizers Implementation.
"""

from loom.protocol.memory_operations import ContextSanitizer


class BubbleUpSanitizer(ContextSanitizer):
    """
    Sanitizes child context for parent consumption.
    Extracts high-level signals.
    """
    async def sanitize(self, context: str, target_token_limit: int) -> str:
        # 1. Identify "Goal"
        # 2. Identify "Result"
        # 3. Identify "Blockers"

        # Simple string processing for prototype
        lines = context.split('\n')
        important_lines = [line for line in lines if "Result:" in line or "Error:" in line or "Goal:" in line]

        result = "\n".join(important_lines)
        if len(result) > target_token_limit * 4: # rough char approx
             return result[:target_token_limit * 4] + "..."
        return result

class CompressiveSanitizer(ContextSanitizer):
    """
    Compresses older conversation turns.
    """
    async def sanitize(self, context: str, target_token_limit: int) -> str:
        # In a real impl, calls LLM to summarize.
        # Here we just truncate the middle.

        if len(context) < target_token_limit * 4:
            return context

        head = context[:(target_token_limit * 2)]
        tail = context[-(target_token_limit * 2):]
        return f"{head}\n... [Compressed {len(context) - len(head) - len(tail)} chars] ...\n{tail}"
