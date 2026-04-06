"""Test the fixed GeminiProvider implementation"""

from loom.providers.gemini import GeminiProvider
from loom.providers.base import CompletionParams


def test_gemini_provider_structure():
    """Test that GeminiProvider has proper structure and methods"""

    print("=" * 70)
    print("GeminiProvider Structure Test")
    print("=" * 70)

    # Test 1: Initialization
    print("\n1. Test: Provider initialization")
    provider = GeminiProvider(api_key="test-api-key")
    assert provider.api_key == "test-api-key", "API key should be stored"
    assert provider._client is None, "Client should be lazy-loaded"
    print("   ✅ Provider initialized correctly")

    # Test 2: Message conversion - basic
    print("\n2. Test: Message conversion (basic)")
    messages = [
        {"role": "user", "content": "Hello"}
    ]
    converted = provider._convert_messages(messages)
    assert len(converted) == 1, "Should have 1 message"
    assert converted[0]["role"] == "user", "Role should be 'user'"
    assert converted[0]["parts"][0]["text"] == "Hello", "Content should be in parts"
    print("   ✅ Basic message conversion works")

    # Test 3: Message conversion - assistant to model
    print("\n3. Test: Message conversion (assistant -> model)")
    messages = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there"}
    ]
    converted = provider._convert_messages(messages)
    assert len(converted) == 2, "Should have 2 messages"
    assert converted[1]["role"] == "model", "Assistant should become 'model'"
    assert converted[1]["parts"][0]["text"] == "Hi there", "Content preserved"
    print("   ✅ Assistant role converted to 'model'")

    # Test 4: Message conversion - system messages
    print("\n4. Test: Message conversion (system messages)")
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello"}
    ]
    converted = provider._convert_messages(messages)
    assert len(converted) == 1, "System should be merged into user message"
    assert converted[0]["role"] == "user", "Should be user message"
    assert "You are a helpful assistant." in converted[0]["parts"][0]["text"], "System content prepended"
    assert "Hello" in converted[0]["parts"][0]["text"], "User content preserved"
    print("   ✅ System messages prepended to first user message")

    # Test 5: Message conversion - multiple system messages
    print("\n5. Test: Message conversion (multiple system messages)")
    messages = [
        {"role": "system", "content": "System 1"},
        {"role": "system", "content": "System 2"},
        {"role": "user", "content": "Hello"}
    ]
    converted = provider._convert_messages(messages)
    assert len(converted) == 1, "All system messages merged"
    text = converted[0]["parts"][0]["text"]
    assert "System 1" in text, "First system message included"
    assert "System 2" in text, "Second system message included"
    assert "Hello" in text, "User message included"
    print("   ✅ Multiple system messages merged correctly")

    # Test 6: Message conversion - complex conversation
    print("\n6. Test: Message conversion (complex conversation)")
    messages = [
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "Question 1"},
        {"role": "assistant", "content": "Answer 1"},
        {"role": "user", "content": "Question 2"}
    ]
    converted = provider._convert_messages(messages)
    assert len(converted) == 3, "Should have 3 messages (system merged)"
    assert converted[0]["role"] == "user", "First is user (with system)"
    assert converted[1]["role"] == "model", "Second is model"
    assert converted[2]["role"] == "user", "Third is user"
    print("   ✅ Complex conversation converted correctly")

    # Test 7: Extract text - mock response with text attribute
    print("\n7. Test: Extract text from response")

    class MockResponse:
        def __init__(self, text):
            self.text = text

    response = MockResponse("Test response")
    extracted = provider._extract_text(response)
    assert extracted == "Test response", "Should extract text attribute"
    print("   ✅ Text extraction works")

    # Test 8: Extract text - empty response
    print("\n8. Test: Extract text from empty response")

    class EmptyResponse:
        pass

    response = EmptyResponse()
    extracted = provider._extract_text(response)
    assert extracted == "", "Should return empty string for invalid response"
    print("   ✅ Empty response handled gracefully")

    # Test 9: Method signatures
    print("\n9. Test: Method signatures")
    import inspect

    # Check complete method
    complete_sig = inspect.signature(provider.complete)
    assert "messages" in complete_sig.parameters, "complete() should have messages param"
    assert "params" in complete_sig.parameters, "complete() should have params param"

    # Check stream method
    stream_sig = inspect.signature(provider.stream)
    assert "messages" in stream_sig.parameters, "stream() should have messages param"
    assert "params" in stream_sig.parameters, "stream() should have params param"

    print("   ✅ Method signatures correct")

    # Test 10: Lazy client loading
    print("\n10. Test: Lazy client loading")
    provider2 = GeminiProvider(api_key="test-key")
    assert provider2._client is None, "Client should not be loaded on init"

    # Try to access client (will fail without SDK, but that's expected)
    try:
        _ = provider2.client
        print("   ✅ Client property accessible (SDK installed)")
    except ImportError as e:
        assert "google-generativeai" in str(e), "Should mention missing package"
        print("   ✅ Client loading fails gracefully without SDK")

    print("\n" + "=" * 70)
    print("Summary:")
    print("=" * 70)
    print("✅ All 10 structure tests passed!")
    print("\nGeminiProvider now has:")
    print("  • Proper initialization with API key")
    print("  • Lazy client loading with clear error messages")
    print("  • Message conversion (user/assistant/system)")
    print("  • Role mapping (assistant -> model)")
    print("  • System message handling (prepend to first user)")
    print("  • Text extraction from responses")
    print("  • Complete and stream methods with correct signatures")
    print("  • Consistent with OpenAI and Anthropic providers")
    print("\n" + "=" * 70)

    return True


if __name__ == "__main__":
    success = test_gemini_provider_structure()
    exit(0 if success else 1)
