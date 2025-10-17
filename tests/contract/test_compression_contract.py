"""Contract tests for US2: Context Compression (T040-T041)

Test CompressionManager API contract and metadata structure.

Written FIRST per TDD workflow before CompressionManager implementation.
"""

import asyncio
from typing import List

import pytest

from loom.core.types import Message, CompressionMetadata


# These tests define the expected API contract for CompressionManager
# Implementation must conform to these interfaces


@pytest.mark.contract
async def test_compress_8_segment_structure():
    """Test CompressionManager.compress() returns valid 8-segment structure.

    API Contract:
    - Input: List[Message] (user/assistant messages)
    - Output: Tuple[List[Message], CompressionMetadata]
    - Compressed messages contain 8-segment summary
    - System messages preserved (not compressed)
    """
    # Import will fail until CompressionManager is implemented
    try:
        from loom.core.compression_manager import CompressionManager
    except ImportError:
        pytest.skip("CompressionManager not yet implemented")

    # Mock LLM for compression
    class MockCompressorLLM:
        async def generate(self, messages: List[dict]) -> str:
            # Simulate 8-segment compression
            return """**Compressed Context**

1. **Task Overview**: User requested file analysis
2. **Key Decisions**: Decided to analyze files sequentially
3. **Progress**: Analyzed 5 out of 10 files
4. **Blockers**: None
5. **Open Items**: Continue with remaining 5 files
6. **Context**: File analysis workflow
7. **Next Steps**: Process next file
8. **Metadata**: 20 messages compressed to 1 summary
"""

    compressor = CompressionManager(llm=MockCompressorLLM())

    # Create test messages
    messages = [
        Message(role="system", content="You are a helpful assistant"),
        Message(role="user", content="Analyze file1.txt"),
        Message(role="assistant", content="Analyzing file1.txt..."),
        Message(role="user", content="Analyze file2.txt"),
        Message(role="assistant", content="Analyzing file2.txt..."),
    ]

    # Compress
    compressed_messages, metadata = await compressor.compress(messages)

    # Assert: Output is valid tuple
    assert isinstance(compressed_messages, list), "Output should be list of messages"
    assert isinstance(metadata, CompressionMetadata), "Metadata should be CompressionMetadata instance"

    # Assert: System message preserved
    assert any(m.role == "system" for m in compressed_messages), "System message should be preserved"

    # Assert: Compressed message contains 8 segments
    compressed_content = ""
    for msg in compressed_messages:
        if "Task Overview" in msg.content:
            compressed_content = msg.content
            break

    assert "Task Overview" in compressed_content, "Missing segment 1: Task Overview"
    assert "Key Decisions" in compressed_content, "Missing segment 2: Key Decisions"
    assert "Progress" in compressed_content, "Missing segment 3: Progress"
    assert "Blockers" in compressed_content, "Missing segment 4: Blockers"
    assert "Open Items" in compressed_content, "Missing segment 5: Open Items"
    assert "Context" in compressed_content, "Missing segment 6: Context"
    assert "Next Steps" in compressed_content, "Missing segment 7: Next Steps"
    assert "Metadata" in compressed_content, "Missing segment 8: Metadata"

    # Assert: Fewer messages after compression
    user_assistant_before = len([m for m in messages if m.role in ("user", "assistant")])
    user_assistant_after = len([m for m in compressed_messages if m.role in ("user", "assistant")])
    assert user_assistant_after < user_assistant_before, "Compression should reduce message count"


@pytest.mark.contract
async def test_compression_metadata():
    """Test CompressionMetadata structure conforms to specification.

    API Contract:
    - original_message_count: int >= 1
    - compressed_message_count: int >= 1
    - compression_ratio: float in [0.0, 1.0]
    - original_tokens: int >= 0
    - compressed_tokens: int >= 0
    - key_topics: List[str] (0-10 topics)
    """
    try:
        from loom.core.compression_manager import CompressionManager
    except ImportError:
        pytest.skip("CompressionManager not yet implemented")

    class MockCompressorLLM:
        async def generate(self, messages: List[dict]) -> str:
            return """**Compressed Context**

1. **Task Overview**: File analysis task
2. **Key Decisions**: Sequential processing
3. **Progress**: 50% complete
4. **Blockers**: None
5. **Open Items**: Continue analysis
6. **Context**: File workflow
7. **Next Steps**: Next batch
8. **Metadata**: Summary complete
"""

    compressor = CompressionManager(llm=MockCompressorLLM())

    messages = [
        Message(role="user", content="Message 1 " + "word " * 100),
        Message(role="assistant", content="Response 1 " + "word " * 100),
        Message(role="user", content="Message 2 " + "word " * 100),
    ]

    _, metadata = await compressor.compress(messages)

    # Assert: Metadata fields exist with correct types
    assert isinstance(metadata.original_message_count, int), "original_message_count must be int"
    assert metadata.original_message_count >= 1, "original_message_count must be >= 1"

    assert isinstance(metadata.compressed_message_count, int), "compressed_message_count must be int"
    assert metadata.compressed_message_count >= 1, "compressed_message_count must be >= 1"

    assert isinstance(metadata.compression_ratio, float), "compression_ratio must be float"
    assert 0.0 <= metadata.compression_ratio <= 1.0, "compression_ratio must be in [0.0, 1.0]"

    assert isinstance(metadata.original_tokens, int), "original_tokens must be int"
    assert metadata.original_tokens >= 0, "original_tokens must be >= 0"

    assert isinstance(metadata.compressed_tokens, int), "compressed_tokens must be int"
    assert metadata.compressed_tokens >= 0, "compressed_tokens must be >= 0"

    assert isinstance(metadata.key_topics, list), "key_topics must be list"
    assert len(metadata.key_topics) <= 10, "key_topics should have <= 10 topics"
    assert all(isinstance(topic, str) for topic in metadata.key_topics), "All topics must be strings"

    # Assert: Compression ratio calculation is correct
    expected_ratio = metadata.compressed_tokens / metadata.original_tokens if metadata.original_tokens > 0 else 0.0
    assert abs(metadata.compression_ratio - expected_ratio) < 0.01, "compression_ratio calculation incorrect"

    # Assert: Token reduction occurred
    assert metadata.compressed_tokens < metadata.original_tokens, "Compression should reduce token count"


@pytest.mark.contract
async def test_should_compress_threshold():
    """Test CompressionManager.should_compress() threshold logic.

    API Contract:
    - should_compress(tokens, max_tokens) -> bool
    - Returns True when tokens >= 92% of max_tokens
    - Returns False otherwise
    """
    try:
        from loom.core.compression_manager import CompressionManager
    except ImportError:
        pytest.skip("CompressionManager not yet implemented")

    class MockCompressorLLM:
        async def generate(self, messages: List[dict]) -> str:
            return "Compressed"

    compressor = CompressionManager(llm=MockCompressorLLM())

    # Test cases for threshold
    assert compressor.should_compress(920, 1000) is True, "92% threshold should trigger"
    assert compressor.should_compress(950, 1000) is True, "Above 92% should trigger"
    assert compressor.should_compress(910, 1000) is False, "Below 92% should not trigger"
    assert compressor.should_compress(500, 1000) is False, "50% should not trigger"
    assert compressor.should_compress(0, 1000) is False, "0 tokens should not trigger"


@pytest.mark.contract
async def test_retry_logic_interface():
    """Test CompressionManager retry logic with exponential backoff.

    API Contract:
    - Max 3 retry attempts on LLM failure
    - Exponential backoff: 1s, 2s, 4s
    - After 3 failures, raise or fallback to sliding window
    """
    try:
        from loom.core.compression_manager import CompressionManager
    except ImportError:
        pytest.skip("CompressionManager not yet implemented")

    class FailingLLM:
        def __init__(self):
            self.call_count = 0

        async def generate(self, messages: List[dict]) -> str:
            self.call_count += 1
            raise Exception(f"LLM failure {self.call_count}")

    failing_llm = FailingLLM()
    compressor = CompressionManager(llm=failing_llm, max_retries=3)

    messages = [
        Message(role="user", content="Test message 1"),
        Message(role="assistant", content="Test response 1"),
    ]

    # Attempt compression - should retry 3 times then fallback
    start_time = asyncio.get_event_loop().time()

    try:
        compressed, metadata = await compressor.compress(messages)
        # If we get here, sliding window fallback succeeded
        assert metadata.key_topics == ["fallback"], "Should indicate fallback was used"
    except Exception as e:
        # Alternatively, may raise after 3 retries
        assert "3 attempts" in str(e) or "max retries" in str(e).lower()

    elapsed = asyncio.get_event_loop().time() - start_time

    # Assert: 3 attempts made
    assert failing_llm.call_count == 3, f"Expected 3 retry attempts, got {failing_llm.call_count}"

    # Assert: Exponential backoff applied (1s + 2s + 4s = ~7s total)
    assert elapsed >= 6.5, f"Expected ~7s with backoff, got {elapsed:.1f}s"
    assert elapsed < 10, f"Backoff too slow: {elapsed:.1f}s"


@pytest.mark.contract
async def test_sliding_window_fallback_interface():
    """Test sliding window fallback returns valid structure.

    API Contract:
    - Input: List[Message], window_size: int
    - Output: List[Message] (last N messages)
    - System messages always preserved
    - Metadata indicates fallback was used
    """
    try:
        from loom.core.compression_manager import CompressionManager
    except ImportError:
        pytest.skip("CompressionManager not yet implemented")

    class MockCompressorLLM:
        async def generate(self, messages: List[dict]) -> str:
            return "Summary"

    compressor = CompressionManager(llm=MockCompressorLLM())

    messages = [
        Message(role="system", content="System prompt"),
        Message(role="user", content="Message 1"),
        Message(role="assistant", content="Response 1"),
        Message(role="user", content="Message 2"),
        Message(role="assistant", content="Response 2"),
        Message(role="user", content="Message 3"),
        Message(role="assistant", content="Response 3"),
    ]

    # Apply sliding window (keep last 4 messages + system)
    windowed = compressor.sliding_window_fallback(messages, window_size=4)

    # Assert: System message preserved
    assert windowed[0].role == "system", "System message should be first"
    assert windowed[0].content == "System prompt", "System content should be unchanged"

    # Assert: Only last 4 user/assistant messages kept
    user_assistant = [m for m in windowed if m.role in ("user", "assistant")]
    assert len(user_assistant) == 4, f"Expected 4 messages, got {len(user_assistant)}"

    # Assert: Most recent messages kept (Message 2, Response 2, Message 3, Response 3)
    assert "Message 2" in user_assistant[0].content or "Message 3" in user_assistant[0].content
    assert "Response 3" in user_assistant[-1].content, "Most recent response should be last"
