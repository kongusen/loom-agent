"""
Example: LLM Compliance Testing

Demonstrates how to use the LLMComplianceSuite to validate LLM implementations.

Run this test:
    pytest tests/unit/test_llm_compliance_example.py -v -s
"""

import pytest
from loom.testing import LLMComplianceSuite
from loom.builtin.llms.mock import MockLLM


class TestMockLLMCompliance:
    """Test MockLLM compliance with BaseLLM Protocol"""

    @pytest.mark.asyncio
    async def test_mock_llm_full_compliance(self):
        """Run full compliance suite on MockLLM"""

        # Create test suite
        suite = LLMComplianceSuite(
            llm_factory=lambda: MockLLM(
                name="mock-gpt-4",
                responses=["Hello, how can I help you?"]
            ),
            strict_validation=True
        )

        # Run all tests
        report = await suite.run_all_tests()

        # Print report
        report.print_summary()

        # Assert all tests passed
        assert report.success_rate == 100, (
            f"MockLLM compliance failed: {report.failed_tests} tests failed"
        )

    @pytest.mark.asyncio
    async def test_mock_llm_protocol_implementation(self):
        """Test MockLLM implements Protocol correctly"""

        suite = LLMComplianceSuite(
            llm_factory=lambda: MockLLM(name="mock")
        )

        result = await suite.test_protocol_implementation()

        assert result.passed, f"Protocol test failed: {result.error_message}"
        assert result.metadata["has_model_name"]
        assert result.metadata["has_stream"]

    @pytest.mark.asyncio
    async def test_mock_llm_text_generation(self):
        """Test MockLLM text generation"""

        suite = LLMComplianceSuite(
            llm_factory=lambda: MockLLM(
                name="mock",
                responses=["Hello World!"]
            )
        )

        result = await suite.test_simple_text_generation()

        assert result.passed, f"Text generation failed: {result.error_message}"
        assert result.metadata["content_deltas"] > 0
        assert result.metadata["finish_events"] == 1

    @pytest.mark.asyncio
    async def test_mock_llm_tool_calling(self):
        """Test MockLLM tool calling"""

        # Configure MockLLM to call tools
        suite = LLMComplianceSuite(
            llm_factory=lambda: MockLLM(
                name="mock",
                responses=["Let me check that for you."],
                tool_calls=[
                    {
                        "id": "call_1",
                        "name": "get_weather",
                        "arguments": {"location": "Tokyo"}
                    }
                ],
                should_call_tools=True
            )
        )

        result = await suite.test_tool_calling()

        assert result.passed, f"Tool calling failed: {result.error_message}"
        # Note: Tool calling is optional, so we just check it didn't error


@pytest.mark.skipif(
    True,  # Skip by default (requires API key)
    reason="Requires OpenAI API key - uncomment to run"
)
class TestOpenAILLMCompliance:
    """Test OpenAI LLM compliance (requires API key)"""

    @pytest.mark.asyncio
    async def test_openai_llm_full_compliance(self):
        """
        Run full compliance suite on OpenAILLM.

        Note: Uncomment @pytest.mark.skipif and set your API key to run this test.
        """
        from loom.builtin.llms import OpenAILLM

        # Create test suite
        suite = LLMComplianceSuite(
            llm_factory=lambda: OpenAILLM(
                api_key="your-api-key-here",  # Replace with actual key
                model="gpt-3.5-turbo",
                temperature=0.7
            ),
            strict_validation=True
        )

        # Run all tests
        report = await suite.run_all_tests()

        # Print report
        report.print_summary()

        # Assert high compliance (allow some flexibility)
        assert report.success_rate >= 85, (
            f"OpenAI LLM compliance too low: {report.success_rate}%"
        )


# ============================================================================
# Standalone Example
# ============================================================================

async def example_usage():
    """
    Standalone example showing how to use the compliance suite.

    Run this directly:
        python -c "import asyncio; from tests.unit.test_llm_compliance_example import example_usage; asyncio.run(example_usage())"
    """
    from loom.builtin.llms.mock import MockLLM
    from loom.testing import LLMComplianceSuite

    print("Running LLM Compliance Tests\n")

    # Test MockLLM
    print("Testing MockLLM...")
    suite = LLMComplianceSuite(
        llm_factory=lambda: MockLLM(
            name="mock-gpt-4",
            responses=[
                "Hello! I'm a helpful assistant.",
                "The weather in Tokyo is sunny.",
                "I can help you with various tasks."
            ],
            tool_calls=[
                {
                    "id": "call_weather_1",
                    "name": "get_weather",
                    "arguments": {"location": "Tokyo"}
                }
            ],
            should_call_tools=True
        ),
        strict_validation=True
    )

    report = await suite.run_all_tests()
    report.print_summary()

    if report.success_rate == 100:
        print("\n✓ MockLLM is fully compliant with BaseLLM Protocol!")
    else:
        print(f"\n✗ MockLLM has {report.failed_tests} failing test(s)")

    return report


if __name__ == "__main__":
    import asyncio
    asyncio.run(example_usage())
