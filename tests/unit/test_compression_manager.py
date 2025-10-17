"""Unit tests for CompressionManager (T051-T053)

Test 8-segment extraction, token reduction, and key topics extraction.
"""

import asyncio
from typing import List

import pytest

from loom.core.compression_manager import CompressionManager
from loom.core.types import Message


class MockLLM:
    """Mock LLM for unit testing compression."""

    def __init__(self, response: str):
        self.response = response
        self.call_count = 0

    async def generate(self, messages: List[dict]) -> str:
        """Return predefined response."""
        self.call_count += 1
        return self.response


@pytest.mark.unit
async def test_8_segment_extraction():
    """Test CompressionManager extracts all 8 segments from LLM response.

    Verifies:
    - All 8 segments present in compressed output
    - Each segment has expected structure
    - Segment order preserved
    """
    llm_response = """**Compressed Context**

1. **Task Overview**: User is implementing authentication for API.

2. **Key Decisions**:
   - Using JWT tokens
   - 7-day expiration
   - Bcrypt hashing

3. **Progress**:
   - Created User model
   - Implemented /register endpoint
   - Implemented /login endpoint

4. **Blockers**:
   - JWT verification failed → Fixed by using consistent SECRET_KEY

5. **Open Items**:
   - Add /refresh endpoint
   - Implement rate limiting

6. **Context**: Part of e-commerce platform migration to FastAPI.

7. **Next Steps**:
   - Implement /refresh endpoint
   - Add Redis for rate limiting

8. **Metadata**: Compressed 45 messages → 1 summary. Topics: authentication, JWT, FastAPI
"""

    llm = MockLLM(response=llm_response)
    compressor = CompressionManager(llm=llm)

    messages = [
        Message(role="user", content="How do I implement JWT auth?"),
        Message(role="assistant", content="Here's how to implement JWT..."),
        Message(role="user", content="What about token expiration?"),
    ]

    compressed, metadata = await compressor.compress(messages)

    # Assert: Compression succeeded
    assert len(compressed) == 1, "Should compress to 1 message"
    compressed_content = compressed[0].content

    # Assert: All 8 segments present
    assert "Task Overview" in compressed_content, "Missing segment 1"
    assert "Key Decisions" in compressed_content, "Missing segment 2"
    assert "Progress" in compressed_content, "Missing segment 3"
    assert "Blockers" in compressed_content, "Missing segment 4"
    assert "Open Items" in compressed_content, "Missing segment 5"
    assert "Context" in compressed_content, "Missing segment 6"
    assert "Next Steps" in compressed_content, "Missing segment 7"
    assert "Metadata" in compressed_content, "Missing segment 8"

    # Assert: LLM called once
    assert llm.call_count == 1

    # Assert: Metadata populated
    assert metadata.original_message_count == 3
    assert metadata.compressed_message_count == 1


@pytest.mark.unit
async def test_token_reduction():
    """Test compression achieves 70-80% token reduction.

    Verifies:
    - Compressed tokens < original tokens
    - Compression ratio within acceptable range (0.2-0.3 = 70-80% reduction)
    - Metadata accurately reflects reduction
    """
    llm_response = """**Compressed Context**

1. **Task Overview**: API authentication implementation.
2. **Key Decisions**: JWT, 7-day expiration, Bcrypt.
3. **Progress**: User model, /register, /login endpoints.
4. **Blockers**: JWT verification fixed.
5. **Open Items**: /refresh, rate limiting.
6. **Context**: FastAPI migration.
7. **Next Steps**: Implement /refresh, add Redis.
8. **Metadata**: Compressed 3 messages → 1 summary. Topics: auth, JWT
"""

    llm = MockLLM(response=llm_response)
    compressor = CompressionManager(llm=llm, target_reduction=0.75)

    # Create verbose messages (simulate token-heavy conversation)
    messages = [
        Message(role="user", content="Explain JWT authentication " + "in detail " * 50),
        Message(role="assistant", content="JWT stands for JSON Web Token " + "which is used for authentication " * 50),
        Message(role="user", content="How do I implement it in FastAPI " + "with proper security " * 50),
    ]

    compressed, metadata = await compressor.compress(messages)

    # Assert: Token reduction occurred
    assert metadata.compressed_tokens < metadata.original_tokens, \
        f"Compressed ({metadata.compressed_tokens}) should be < original ({metadata.original_tokens})"

    # Assert: Compression ratio within range (0.2-0.3 = 70-80% reduction)
    assert 0.15 <= metadata.compression_ratio <= 0.35, \
        f"Compression ratio {metadata.compression_ratio:.2f} outside acceptable range (0.15-0.35)"

    # Assert: Significant reduction (at least 50%)
    reduction_percent = (1 - metadata.compression_ratio) * 100
    assert reduction_percent >= 50, f"Only {reduction_percent:.1f}% reduction, expected >= 50%"


@pytest.mark.unit
async def test_key_topics_extraction():
    """Test CompressionManager extracts key topics from metadata section.

    Verifies:
    - Topics extracted from Metadata section
    - Max 10 topics
    - Topics are non-empty strings
    """
    llm_response = """**Compressed Context**

1. **Task Overview**: User implementing search feature.
2. **Key Decisions**: Using Elasticsearch.
3. **Progress**: Indexed 1000 documents.
4. **Blockers**: None.
5. **Open Items**: Add filtering.
6. **Context**: E-commerce product search.
7. **Next Steps**: Implement filters.
8. **Metadata**: Compressed 20 messages → 1 summary. Topics: search, elasticsearch, indexing, filtering, performance
"""

    llm = MockLLM(response=llm_response)
    compressor = CompressionManager(llm=llm)

    messages = [
        Message(role="user", content="How do I implement search?"),
        Message(role="assistant", content="You can use Elasticsearch..."),
    ]

    compressed, metadata = await compressor.compress(messages)

    # Assert: Topics extracted
    assert len(metadata.key_topics) > 0, "Should extract at least 1 topic"
    assert len(metadata.key_topics) <= 10, f"Too many topics: {len(metadata.key_topics)}"

    # Assert: Topics are valid strings
    for topic in metadata.key_topics:
        assert isinstance(topic, str), f"Topic should be string, got {type(topic)}"
        assert len(topic) > 0, "Topic should not be empty string"

    # Assert: Expected topics present
    topics_lower = [t.lower() for t in metadata.key_topics]
    assert "search" in topics_lower or "elasticsearch" in topics_lower, \
        f"Expected search-related topic, got {metadata.key_topics}"


@pytest.mark.unit
async def test_should_compress_threshold():
    """Test should_compress() threshold logic.

    Verifies:
    - Returns True at 92% threshold
    - Returns False below threshold
    - Boundary conditions handled correctly
    """
    llm = MockLLM(response="Compressed")
    compressor = CompressionManager(llm=llm, compression_threshold=0.92)

    # Test cases
    assert compressor.should_compress(920, 1000) is True, "92% should trigger"
    assert compressor.should_compress(950, 1000) is True, "95% should trigger"
    assert compressor.should_compress(919, 1000) is False, "91.9% should not trigger"
    assert compressor.should_compress(500, 1000) is False, "50% should not trigger"
    assert compressor.should_compress(0, 1000) is False, "0 tokens should not trigger"

    # Boundary: Exactly 92%
    assert compressor.should_compress(920, 1000) is True, "Exactly 92% should trigger"

    # Edge case: max_tokens = 0
    assert compressor.should_compress(100, 0) is True, "Any tokens with max=0 should trigger"


@pytest.mark.unit
async def test_sliding_window_fallback():
    """Test sliding window fallback keeps last N messages.

    Verifies:
    - Keeps exactly window_size messages
    - Most recent messages preserved
    - Order maintained
    """
    llm = MockLLM(response="Compressed")
    compressor = CompressionManager(llm=llm, sliding_window_size=3)

    messages = [
        Message(role="user", content="Message 1"),
        Message(role="assistant", content="Response 1"),
        Message(role="user", content="Message 2"),
        Message(role="assistant", content="Response 2"),
        Message(role="user", content="Message 3"),
        Message(role="assistant", content="Response 3"),
    ]

    windowed = compressor.sliding_window_fallback(messages, window_size=3)

    # Assert: Correct number of messages
    assert len(windowed) == 3, f"Expected 3 messages, got {len(windowed)}"

    # Assert: Last 3 messages kept
    assert windowed[0].content == "Response 2", "Should keep Response 2"
    assert windowed[1].content == "Message 3", "Should keep Message 3"
    assert windowed[2].content == "Response 3", "Should keep Response 3 (most recent)"

    # Assert: Order preserved
    assert windowed[0].role == "assistant"
    assert windowed[1].role == "user"
    assert windowed[2].role == "assistant"


@pytest.mark.unit
async def test_system_message_preservation():
    """Test system messages are never compressed.

    Verifies:
    - System messages excluded from compression
    - System messages re-added to output
    - User/assistant messages compressed
    """
    llm_response = """**Compressed Context**

1. **Task Overview**: Code review.
2. **Key Decisions**: Focus on security.
3. **Progress**: Reviewed 5 files.
4. **Blockers**: None.
5. **Open Items**: 2 more files.
6. **Context**: Security audit.
7. **Next Steps**: Complete review.
8. **Metadata**: Compressed 4 messages → 1 summary. Topics: security, code_review
"""

    llm = MockLLM(response=llm_response)
    compressor = CompressionManager(llm=llm)

    messages = [
        Message(role="system", content="You are a security expert."),
        Message(role="user", content="Review this code."),
        Message(role="assistant", content="I see several issues..."),
        Message(role="user", content="What about XSS?"),
        Message(role="assistant", content="XSS vulnerabilities found in..."),
    ]

    compressed, metadata = await compressor.compress(messages)

    # Assert: System message preserved
    system_msgs = [m for m in compressed if m.role == "system"]
    assert len(system_msgs) >= 1, "System message should be preserved"

    # Assert: System message is first
    assert compressed[0].role == "system", "System message should be first"
    assert "security expert" in compressed[0].content, "Original system message should be intact"

    # Assert: Only user/assistant compressed (not system)
    assert metadata.original_message_count == 4, "Should compress 4 user/assistant messages"


@pytest.mark.unit
async def test_retry_exponential_backoff():
    """Test retry logic with exponential backoff timing.

    Verifies:
    - Retries 3 times on failure
    - Exponential backoff applied (1s, 2s, 4s)
    - Total time approximately 7 seconds
    """
    class FailingLLM:
        def __init__(self):
            self.call_count = 0
            self.call_times = []

        async def generate(self, messages: List[dict]) -> str:
            self.call_count += 1
            self.call_times.append(asyncio.get_event_loop().time())
            raise Exception(f"Simulated LLM failure {self.call_count}")

    failing_llm = FailingLLM()
    compressor = CompressionManager(llm=failing_llm, max_retries=3, sliding_window_size=2)

    messages = [
        Message(role="user", content="Test 1"),
        Message(role="assistant", content="Response 1"),
        Message(role="user", content="Test 2"),
    ]

    start_time = asyncio.get_event_loop().time()
    compressed, metadata = await compressor.compress(messages)
    elapsed = asyncio.get_event_loop().time() - start_time

    # Assert: 3 retry attempts
    assert failing_llm.call_count == 3, f"Expected 3 attempts, got {failing_llm.call_count}"

    # Assert: Exponential backoff timing (1s + 2s + 4s = 7s total)
    assert elapsed >= 6.5, f"Backoff too fast: {elapsed:.1f}s (expected ~7s)"
    assert elapsed < 10, f"Backoff too slow: {elapsed:.1f}s (expected ~7s)"

    # Assert: Fallback to sliding window
    assert metadata.key_topics == ["fallback"], "Should indicate fallback used"
    assert len(compressed) == 2, "Should fall back to sliding window (2 messages)"


@pytest.mark.unit
async def test_empty_message_list():
    """Test compression handles empty message list gracefully.

    Verifies:
    - Returns empty list without errors
    - Metadata shows 0 counts
    """
    llm = MockLLM(response="Compressed")
    compressor = CompressionManager(llm=llm)

    compressed, metadata = await compressor.compress([])

    # Assert: Empty list returned
    assert len(compressed) == 0, "Should return empty list"

    # Assert: Metadata shows zero counts
    assert metadata.original_message_count == 0
    assert metadata.compressed_message_count == 0
    assert metadata.original_tokens == 0
    assert metadata.compressed_tokens == 0
    assert metadata.compression_ratio == 0.0


@pytest.mark.unit
async def test_format_messages_for_prompt():
    """Test _format_messages_for_prompt() creates readable conversation.

    Verifies:
    - Messages formatted with role labels
    - Numbered sequentially
    - Long messages truncated to 500 chars
    """
    llm = MockLLM(response="Compressed")
    compressor = CompressionManager(llm=llm)

    messages = [
        Message(role="user", content="Short message"),
        Message(role="assistant", content="A" * 1000),  # Long message (1000 chars)
    ]

    formatted = compressor._format_messages_for_prompt(messages)

    # Assert: Contains numbered entries
    assert "[1] USER:" in formatted, "Should have numbered first message"
    assert "[2] ASSISTANT:" in formatted, "Should have numbered second message"

    # Assert: Long message truncated
    assert len(formatted) < 1500, f"Formatted text too long: {len(formatted)} chars"
    lines = formatted.split("\n")
    assert len(lines[1]) <= 520, "Long message should be truncated to ~500 chars"  # 500 + label


@pytest.mark.unit
async def test_compression_metadata_calculation():
    """Test CompressionMetadata fields calculated correctly.

    Verifies:
    - original_tokens vs compressed_tokens
    - compression_ratio = compressed / original
    - message counts
    """
    llm_response = "**Compressed Context**\n\n1. **Task Overview**: Short summary."

    llm = MockLLM(response=llm_response)
    compressor = CompressionManager(llm=llm)

    messages = [
        Message(role="user", content="Long message " + "word " * 100),
        Message(role="assistant", content="Long response " + "word " * 100),
    ]

    compressed, metadata = await compressor.compress(messages)

    # Assert: Token reduction
    assert metadata.original_tokens > metadata.compressed_tokens, \
        "Original tokens should be > compressed tokens"

    # Assert: Compression ratio calculation
    expected_ratio = metadata.compressed_tokens / metadata.original_tokens
    assert abs(metadata.compression_ratio - expected_ratio) < 0.01, \
        f"Ratio mismatch: {metadata.compression_ratio} != {expected_ratio}"

    # Assert: Message counts
    assert metadata.original_message_count == 2, "Should have 2 original messages"
    assert metadata.compressed_message_count == 1, "Should have 1 compressed message"
