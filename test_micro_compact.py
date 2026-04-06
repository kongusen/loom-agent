"""Test the micro_compact implementation"""

from loom.context.compression import ContextCompressor
from loom.types import Message


def test_micro_compact():
    """Test that micro_compact actually works"""

    print("=" * 70)
    print("micro_compact Test")
    print("=" * 70)

    compressor = ContextCompressor(micro_max_chars=100)

    # Test 1: Basic compression - no tool messages
    print("\n1. Test: No tool messages (pass through)")
    messages = [
        Message(role="user", content="Hello"),
        Message(role="assistant", content="Hi there")
    ]
    result = compressor.micro_compact(messages)
    assert len(result) == 2, "Should have 2 messages"
    assert result[0].content == "Hello", "User message unchanged"
    assert result[1].content == "Hi there", "Assistant message unchanged"
    print("   ✅ Non-tool messages pass through unchanged")

    # Test 2: Tool message with short content
    print("\n2. Test: Tool message with short content")
    messages = [
        Message(role="user", content="Run command"),
        Message(role="tool", content="Command output: OK", tool_call_id="call_1", name="bash")
    ]
    result = compressor.micro_compact(messages)
    assert len(result) == 2, "Should have 2 messages"
    assert result[1].role == "tool", "Should be tool message"
    assert "OK" in result[1].content, "Short content should be preserved"
    print("   ✅ Short tool messages preserved")

    # Test 3: Tool message with long content (should be summarized)
    print("\n3. Test: Tool message with long content (summarized)")
    long_content = "x" * 500  # 500 chars, exceeds micro_max_chars (100)
    messages = [
        Message(role="user", content="Run command"),
        Message(role="tool", content=long_content, tool_call_id="call_1", name="bash")
    ]
    result = compressor.micro_compact(messages)
    assert len(result) == 2, "Should have 2 messages"
    assert len(result[1].content) < len(long_content), "Should be compressed"
    assert "[tool result cached:" in result[1].content, "Should indicate caching"
    assert "500 chars" in result[1].content, "Should show original length"
    print(f"   ✅ Long content compressed ({len(long_content)} → {len(result[1].content)} chars)")

    # Test 4: Duplicate tool results (same tool_call_id)
    print("\n4. Test: Duplicate tool results (same tool_call_id)")
    messages = [
        Message(role="user", content="Run command"),
        Message(role="tool", content="Output 1", tool_call_id="call_1", name="bash"),
        Message(role="user", content="Run again"),
        Message(role="tool", content="Output 1", tool_call_id="call_1", name="bash")  # Duplicate
    ]
    result = compressor.micro_compact(messages)
    assert len(result) == 4, "Should have 4 messages"
    # Second tool message should be cached
    assert "[cached" in result[3].content, "Duplicate should be cached"
    assert "call_1" in result[3].content, "Should reference original call_id"
    print("   ✅ Duplicate tool results cached by tool_call_id")

    # Test 5: Duplicate tool results (same content, different call_id)
    print("\n5. Test: Duplicate tool results (same content, different call_id)")
    messages = [
        Message(role="user", content="Run command"),
        Message(role="tool", content="Same output", tool_call_id="call_1", name="bash"),
        Message(role="user", content="Run again"),
        Message(role="tool", content="Same output", tool_call_id="call_2", name="bash")  # Same content
    ]
    result = compressor.micro_compact(messages)
    assert len(result) == 4, "Should have 4 messages"
    # Second tool message should be cached by content signature
    assert "[cached" in result[3].content, "Duplicate content should be cached"
    print("   ✅ Duplicate content cached by signature")

    # Test 6: Different tool results (not cached)
    print("\n6. Test: Different tool results (not cached)")
    messages = [
        Message(role="user", content="Run command"),
        Message(role="tool", content="Output 1", tool_call_id="call_1", name="bash"),
        Message(role="user", content="Run again"),
        Message(role="tool", content="Output 2", tool_call_id="call_2", name="bash")  # Different
    ]
    result = compressor.micro_compact(messages)
    assert len(result) == 4, "Should have 4 messages"
    # Second tool message should NOT be cached
    assert "[cached" not in result[3].content, "Different content should not be cached"
    assert "Output 2" in result[3].content, "Should preserve different content"
    print("   ✅ Different tool results not cached")

    # Test 7: Empty tool content
    print("\n7. Test: Empty tool content")
    messages = [
        Message(role="user", content="Run command"),
        Message(role="tool", content="", tool_call_id="call_1", name="bash")
    ]
    result = compressor.micro_compact(messages)
    assert len(result) == 2, "Should have 2 messages"
    assert result[1].content == "", "Empty content preserved"
    print("   ✅ Empty tool content handled")

    # Test 8: Tool message without tool_call_id
    print("\n8. Test: Tool message without tool_call_id")
    messages = [
        Message(role="user", content="Run command"),
        Message(role="tool", content="Output", name="bash")  # No tool_call_id
    ]
    result = compressor.micro_compact(messages)
    assert len(result) == 2, "Should have 2 messages"
    assert result[1].content == "Output", "Content preserved"
    print("   ✅ Tool message without tool_call_id handled")

    # Test 9: Multiple different tools
    print("\n9. Test: Multiple different tools")
    messages = [
        Message(role="tool", content="Bash output", tool_call_id="call_1", name="bash"),
        Message(role="tool", content="Web output", tool_call_id="call_2", name="web_fetch"),
        Message(role="tool", content="Bash output", tool_call_id="call_3", name="bash")  # Duplicate
    ]
    result = compressor.micro_compact(messages)
    assert len(result) == 3, "Should have 3 messages"
    # Third message should be cached (same content as first)
    assert "[cached" in result[2].content, "Duplicate bash output should be cached"
    print("   ✅ Multiple different tools handled correctly")

    # Test 10: Compression threshold
    print("\n10. Test: Compression threshold (micro_max_chars)")
    compressor_small = ContextCompressor(micro_max_chars=20)
    messages = [
        Message(role="tool", content="This is a longer message that exceeds the threshold",
                tool_call_id="call_1", name="bash")
    ]
    result = compressor_small.micro_compact(messages)
    assert len(result) == 1, "Should have 1 message"
    # The result should indicate caching and show truncated preview
    assert "[tool result cached:" in result[0].content, "Should indicate caching"
    # The preview part should be limited by micro_max_chars
    assert "51 chars" in result[0].content, "Should show original length"
    print(f"   ✅ Compression threshold works (20 chars limit)")
    print(f"      Original: {len(messages[0].content)} chars")
    print(f"      Result: {len(result[0].content)} chars (with cache prefix)")

    print("\n" + "=" * 70)
    print("Summary:")
    print("=" * 70)
    print("✅ All 10 tests passed!")
    print("\nmicro_compact now:")
    print("  • Passes through non-tool messages unchanged")
    print("  • Preserves short tool messages")
    print("  • Compresses long tool messages (> micro_max_chars)")
    print("  • Caches duplicate tool results by tool_call_id")
    print("  • Caches duplicate tool results by content signature")
    print("  • Doesn't cache different tool results")
    print("  • Handles empty tool content")
    print("  • Handles tool messages without tool_call_id")
    print("  • Handles multiple different tools")
    print("  • Respects compression threshold")
    print("\n" + "=" * 70)

    return True


if __name__ == "__main__":
    success = test_micro_compact()
    exit(0 if success else 1)
