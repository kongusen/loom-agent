"""CompressionManager: AU2 8-segment context compression (US2)

Implements intelligent context compression using LLM-based 8-segment summarization
with automatic fallback to sliding window on failure.

Features:
- 92% threshold detection
- 70-80% token reduction via 8-segment structured summarization
- Retry logic with exponential backoff (1s, 2s, 4s)
- Sliding window fallback after 3 failures
- System message preservation
- Compression metadata tracking

Architecture:
- LLM-based compression (primary): Structured 8-segment summary
- Sliding window (fallback): Keep last N messages
- Token counting: tiktoken (cl100k_base for GPT-4/Claude)
"""

from __future__ import annotations

import asyncio
import time
from typing import List, Tuple, Optional

from loom.core.types import Message, CompressionMetadata
from loom.interfaces.llm import BaseLLM
from loom.utils.token_counter import count_messages_tokens


class CompressionManager:
    """Manages context compression with 8-segment LLM-based summarization."""

    # 8-segment compression prompt template
    COMPRESSION_PROMPT_TEMPLATE = """You are a context compression expert. Your task is to compress a long conversation history into a concise 8-segment structured summary while preserving all critical information.

**Input Conversation** ({message_count} messages, {token_count} tokens):
{conversation}

**Compression Requirements**:
1. Extract and preserve ALL critical information (decisions, blockers, data, context)
2. Reduce token count by 70-80% (target: {target_tokens} tokens)
3. Structure output using exactly 8 segments below
4. Use markdown formatting for readability
5. Be concise but comprehensive - no detail too small if relevant

**Output Format** (8 Segments):

1. **Task Overview**: What is the user trying to accomplish? (1-2 sentences)
2. **Key Decisions**: What important decisions or approaches were chosen? (bullet points)
3. **Progress**: What has been completed so far? (bullet points with specific data/results)
4. **Blockers**: What issues or errors occurred? How were they resolved? (bullet points, "None" if none)
5. **Open Items**: What still needs to be done? What questions remain unanswered? (bullet points)
6. **Context**: What background information or domain knowledge is relevant? (1-2 sentences)
7. **Next Steps**: What should happen next based on the conversation? (bullet points)
8. **Metadata**: Compression statistics and key topics (format: "Compressed {message_count} messages → 1 summary. Topics: topic1, topic2, topic3")

**Example Output**:
```
**Compressed Context**

1. **Task Overview**: User is implementing a REST API for user authentication with JWT tokens.

2. **Key Decisions**:
   - Using PostgreSQL for user storage
   - JWT with 7-day expiration
   - Bcrypt for password hashing (cost factor 12)

3. **Progress**:
   - Created User model with email/password fields
   - Implemented /register endpoint (working)
   - Implemented /login endpoint (returns JWT)
   - Added password validation (min 8 chars, 1 special char)

4. **Blockers**:
   - Initial JWT verification failed due to incorrect secret key → Fixed by using consistent SECRET_KEY env var
   - Database connection timeout → Fixed by increasing pool size to 20

5. **Open Items**:
   - Add /refresh endpoint for token renewal
   - Implement rate limiting (5 login attempts per minute)
   - Add email verification flow

6. **Context**: This is part of a larger e-commerce platform migration from Django to FastAPI. Authentication needs to be compatible with existing mobile app using JWT.

7. **Next Steps**:
   - Implement /refresh endpoint with refresh token logic
   - Add Redis for rate limiting
   - Write integration tests for auth flow

8. **Metadata**: Compressed 45 messages → 1 summary. Topics: authentication, JWT, PostgreSQL, FastAPI, API_design
```

Now compress the conversation above following this exact structure:"""

    def __init__(
        self,
        llm: BaseLLM,
        max_retries: int = 3,
        compression_threshold: float = 0.92,
        target_reduction: float = 0.75,  # 75% reduction
        sliding_window_size: int = 20,
    ):
        """Initialize CompressionManager.

        Args:
            llm: LLM instance for compression (should support long context)
            max_retries: Max retry attempts on LLM failure (default: 3)
            compression_threshold: Token usage % to trigger compression (default: 0.92)
            target_reduction: Target compression ratio (default: 0.75 = 75% reduction)
            sliding_window_size: Fallback window size in messages (default: 20)
        """
        self.llm = llm
        self.max_retries = max_retries
        self.compression_threshold = compression_threshold
        self.target_reduction = target_reduction
        self.sliding_window_size = sliding_window_size

    def should_compress(self, current_tokens: int, max_tokens: int) -> bool:
        """Check if compression should be triggered.

        Args:
            current_tokens: Current context token count
            max_tokens: Maximum allowed context tokens

        Returns:
            True if current_tokens >= threshold * max_tokens
        """
        threshold_tokens = int(max_tokens * self.compression_threshold)
        return current_tokens >= threshold_tokens

    async def compress(
        self, messages: List[Message]
    ) -> Tuple[List[Message], CompressionMetadata]:
        """Compress conversation history using 8-segment LLM summarization.

        Process:
        1. Separate system messages (never compress)
        2. Extract user/assistant messages for compression
        3. Attempt LLM compression with retry logic
        4. Fall back to sliding window after max_retries failures
        5. Return compressed messages + metadata

        Args:
            messages: Full conversation history

        Returns:
            Tuple of (compressed_messages, compression_metadata)
        """
        if not messages:
            return messages, CompressionMetadata(
                original_message_count=0,
                compressed_message_count=0,
                original_tokens=0,
                compressed_tokens=0,
                compression_ratio=0.0,
                key_topics=[],
            )

        # Separate system messages (preserve) from compressible messages
        system_messages = [m for m in messages if m.role == "system"]
        compressible = [m for m in messages if m.role in ("user", "assistant", "tool")]

        if not compressible:
            # No messages to compress, return as-is
            return messages, CompressionMetadata(
                original_message_count=len(messages),
                compressed_message_count=len(messages),
                original_tokens=count_messages_tokens(messages),
                compressed_tokens=count_messages_tokens(messages),
                compression_ratio=1.0,
                key_topics=[],
            )

        # Count tokens
        original_tokens = count_messages_tokens(compressible)
        target_tokens = int(original_tokens * self.target_reduction)

        # Attempt LLM compression with retry logic
        compressed_summary = None
        key_topics = []

        for attempt in range(1, self.max_retries + 1):
            try:
                compressed_summary, key_topics = await self._llm_compress(
                    compressible, original_tokens, target_tokens
                )
                break  # Success
            except Exception as e:
                if attempt < self.max_retries:
                    # Exponential backoff: 1s, 2s, 4s
                    backoff_delay = 2 ** (attempt - 1)
                    await asyncio.sleep(backoff_delay)
                else:
                    # Max retries exhausted - fall back to sliding window
                    compressed_summary = None
                    key_topics = ["fallback"]

        # Fall back to sliding window if LLM compression failed
        if compressed_summary is None:
            windowed_messages = self.sliding_window_fallback(compressible, self.sliding_window_size)
            final_messages = system_messages + windowed_messages
            compressed_tokens = count_messages_tokens(windowed_messages)

            metadata = CompressionMetadata(
                original_message_count=len(compressible),
                compressed_message_count=len(windowed_messages),
                original_tokens=original_tokens,
                compressed_tokens=compressed_tokens,
                compression_ratio=compressed_tokens / original_tokens if original_tokens > 0 else 0.0,
                key_topics=["fallback"],
            )
            return final_messages, metadata

        # LLM compression succeeded - create compressed message
        compressed_message = Message(
            role="system",
            content=compressed_summary,
            metadata={"type": "compressed_context", "original_count": len(compressible)},
        )

        compressed_tokens = count_messages_tokens([compressed_message])

        # Combine system messages + compressed summary
        final_messages = system_messages + [compressed_message]

        metadata = CompressionMetadata(
            original_message_count=len(compressible),
            compressed_message_count=1,
            original_tokens=original_tokens,
            compressed_tokens=compressed_tokens,
            compression_ratio=compressed_tokens / original_tokens if original_tokens > 0 else 0.0,
            key_topics=key_topics,
        )

        return final_messages, metadata

    async def _llm_compress(
        self, messages: List[Message], original_tokens: int, target_tokens: int
    ) -> Tuple[str, List[str]]:
        """Use LLM to compress messages into 8-segment summary.

        Args:
            messages: Messages to compress
            original_tokens: Original token count
            target_tokens: Target token count after compression

        Returns:
            Tuple of (compressed_summary_str, key_topics_list)

        Raises:
            Exception: If LLM call fails
        """
        # Format conversation for prompt
        conversation_text = self._format_messages_for_prompt(messages)

        # Build compression prompt
        prompt = self.COMPRESSION_PROMPT_TEMPLATE.format(
            message_count=len(messages),
            token_count=original_tokens,
            target_tokens=target_tokens,
            conversation=conversation_text,
        )

        # Call LLM
        compressed_summary = await self.llm.generate([{"role": "user", "content": prompt}])

        # Extract key topics from summary (simple regex extraction)
        key_topics = self._extract_key_topics(compressed_summary)

        return compressed_summary, key_topics

    def _format_messages_for_prompt(self, messages: List[Message]) -> str:
        """Format messages as readable conversation for LLM prompt.

        Args:
            messages: Messages to format

        Returns:
            Formatted conversation string
        """
        lines = []
        for i, msg in enumerate(messages, 1):
            role_label = msg.role.upper()
            content = msg.content[:500] if len(msg.content) > 500 else msg.content  # Truncate long messages
            lines.append(f"[{i}] {role_label}: {content}")

        return "\n".join(lines)

    def _extract_key_topics(self, compressed_summary: str) -> List[str]:
        """Extract key topics from compressed summary metadata section.

        Args:
            compressed_summary: 8-segment compressed summary

        Returns:
            List of key topics (max 10)
        """
        # Look for "Topics:" in Metadata section
        topics = []
        if "Topics:" in compressed_summary:
            topics_line = compressed_summary.split("Topics:")[-1].strip()
            # Extract comma-separated topics
            raw_topics = topics_line.split(",")
            topics = [t.strip() for t in raw_topics[:10] if t.strip()]

        # Fallback: extract topics from content if metadata missing
        if not topics:
            topics = ["general_compression"]

        return topics

    def sliding_window_fallback(
        self, messages: List[Message], window_size: int
    ) -> List[Message]:
        """Fallback compression using sliding window (keep last N messages).

        Args:
            messages: Messages to compress
            window_size: Number of recent messages to keep

        Returns:
            Last window_size messages
        """
        if len(messages) <= window_size:
            return messages

        # Keep last N messages
        return messages[-window_size:]
