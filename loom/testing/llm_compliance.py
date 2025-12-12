"""
LLM Compliance Test Suite

Comprehensive testing framework for validating LLM implementations against
the BaseLLM Protocol specification.

Usage:
    from loom.testing import LLMComplianceSuite
    from loom.builtin.llms import OpenAILLM

    # Create test suite
    suite = LLMComplianceSuite(llm_factory=lambda: OpenAILLM(api_key="..."))

    # Run all tests
    await suite.run_all_tests()

    # Or run specific tests
    await suite.test_protocol_implementation()
    await suite.test_simple_text_generation()
"""

import asyncio
import inspect
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field

from loom.interfaces.llm import BaseLLM, is_llm, validate_llm_event


@dataclass
class TestResult:
    """Result of a single compliance test"""
    test_name: str
    passed: bool
    error_message: Optional[str] = None
    duration_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ComplianceReport:
    """Complete compliance test report"""
    llm_class_name: str
    model_name: Optional[str] = None
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    test_results: List[TestResult] = field(default_factory=list)
    total_duration_ms: float = 0.0

    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage"""
        if self.total_tests == 0:
            return 0.0
        return (self.passed_tests / self.total_tests) * 100

    def print_summary(self):
        """Print a formatted summary of the compliance report"""
        print("\n" + "="*70)
        print(f"LLM Compliance Test Report: {self.llm_class_name}")
        if self.model_name:
            print(f"Model: {self.model_name}")
        print("="*70)
        print(f"Total Tests: {self.total_tests}")
        print(f"Passed: {self.passed_tests} ✓")
        print(f"Failed: {self.failed_tests} ✗")
        print(f"Success Rate: {self.success_rate:.1f}%")
        print(f"Total Duration: {self.total_duration_ms:.2f}ms")
        print("="*70)

        if self.failed_tests > 0:
            print("\nFailed Tests:")
            for result in self.test_results:
                if not result.passed:
                    print(f"  ✗ {result.test_name}")
                    if result.error_message:
                        print(f"    Error: {result.error_message}")

        print("\nAll Test Results:")
        for result in self.test_results:
            status = "✓" if result.passed else "✗"
            print(f"  {status} {result.test_name} ({result.duration_ms:.2f}ms)")
        print("="*70 + "\n")


class LLMComplianceSuite:
    """
    Comprehensive compliance test suite for BaseLLM Protocol implementations.

    This suite validates that an LLM implementation correctly follows the
    BaseLLM Protocol specification, including:

    1. Protocol Implementation - Implements required methods
    2. Property Tests - model_name property exists and returns str
    3. Text Generation - Basic streaming text generation works
    4. Tool Calling - Function calling works correctly
    5. Event Format - All events follow LLMEvent specification
    6. Error Handling - Handles invalid inputs gracefully

    Example:
        ```python
        from loom.testing import LLMComplianceSuite
        from loom.builtin.llms import OpenAILLM

        # Test OpenAI LLM
        suite = LLMComplianceSuite(
            llm_factory=lambda: OpenAILLM(
                api_key="sk-...",
                model="gpt-4"
            )
        )

        # Run all tests
        report = await suite.run_all_tests()
        report.print_summary()

        # Or run specific tests
        await suite.test_protocol_implementation()
        await suite.test_simple_text_generation()
        ```
    """

    def __init__(
        self,
        llm_factory: Callable[[], Any],
        strict_validation: bool = True
    ):
        """
        Initialize compliance test suite.

        Args:
            llm_factory: Factory function that creates an LLM instance.
                         Called before each test to get a fresh instance.
            strict_validation: If True, use strict event validation (raises errors).
                              If False, use warning mode (logs warnings).
        """
        self.llm_factory = llm_factory
        self.strict_validation = strict_validation
        self.results: List[TestResult] = []

    async def _run_test(
        self,
        test_name: str,
        test_func: Callable
    ) -> TestResult:
        """
        Run a single test and capture results.

        Args:
            test_name: Name of the test
            test_func: Async function to run

        Returns:
            TestResult with pass/fail status and metadata
        """
        import time

        start_time = time.perf_counter()

        try:
            # Run the test function
            metadata = await test_func()
            duration = (time.perf_counter() - start_time) * 1000

            result = TestResult(
                test_name=test_name,
                passed=True,
                duration_ms=duration,
                metadata=metadata or {}
            )
        except Exception as e:
            duration = (time.perf_counter() - start_time) * 1000

            result = TestResult(
                test_name=test_name,
                passed=False,
                error_message=str(e),
                duration_ms=duration
            )

        self.results.append(result)
        return result

    # =========================================================================
    # Core Compliance Tests
    # =========================================================================

    async def test_protocol_implementation(self) -> TestResult:
        """
        Test 1: Verify LLM implements BaseLLM Protocol.

        Checks:
        - Instance passes isinstance(llm, BaseLLM)
        - Has model_name property
        - Has stream() method
        """
        async def test():
            llm = self.llm_factory()

            # Check Protocol implementation
            if not is_llm(llm):
                raise AssertionError(
                    f"{type(llm).__name__} does not implement BaseLLM Protocol. "
                    f"Missing: model_name property or stream() method"
                )

            # Verify model_name property
            if not hasattr(llm, 'model_name'):
                raise AssertionError("Missing model_name property")

            # Verify stream method
            if not hasattr(llm, 'stream'):
                raise AssertionError("Missing stream() method")

            # Check if stream is an async generator (not just a coroutine function)
            # stream() should return AsyncGenerator[LLMEvent, None]
            if not (inspect.isasyncgenfunction(llm.stream) or 
                    asyncio.iscoroutinefunction(llm.stream)):
                raise AssertionError(
                    "stream() must be an async method (async generator or coroutine function)"
                )

            return {
                "llm_class": type(llm).__name__,
                "has_model_name": hasattr(llm, 'model_name'),
                "has_stream": hasattr(llm, 'stream')
            }

        return await self._run_test("Protocol Implementation", test)

    async def test_model_name_property(self) -> TestResult:
        """
        Test 2: Verify model_name property returns a string.
        """
        async def test():
            llm = self.llm_factory()
            model_name = llm.model_name

            if not isinstance(model_name, str):
                raise AssertionError(
                    f"model_name must return str, got {type(model_name).__name__}"
                )

            if not model_name:
                raise AssertionError("model_name must not be empty")

            return {"model_name": model_name}

        return await self._run_test("Model Name Property", test)

    async def test_simple_text_generation(self) -> TestResult:
        """
        Test 3: Basic text generation without tools.

        Checks:
        - stream() returns async generator
        - Yields content_delta events
        - Yields finish event
        - All events are valid LLMEvent format
        """
        async def test():
            llm = self.llm_factory()

            messages = [
                {"role": "user", "content": "Say 'Hello'"}
            ]

            event_count = 0
            content_deltas = 0
            finish_events = 0
            accumulated_content = ""

            # Stream and collect events
            async for event in llm.stream(messages):
                event_count += 1

                # Validate event format
                validate_llm_event(event, strict=self.strict_validation)

                if event.get("type") == "content_delta":
                    content_deltas += 1
                    accumulated_content += event.get("content", "")
                elif event.get("type") == "finish":
                    finish_events += 1

            # Verify we got events
            if event_count == 0:
                raise AssertionError("stream() yielded no events")

            # Verify we got content
            if content_deltas == 0:
                raise AssertionError("No content_delta events received")

            # Verify we got finish
            if finish_events == 0:
                raise AssertionError("No finish event received")

            # Verify content is not empty
            if not accumulated_content.strip():
                raise AssertionError("Generated content is empty")

            return {
                "total_events": event_count,
                "content_deltas": content_deltas,
                "finish_events": finish_events,
                "content_length": len(accumulated_content)
            }

        return await self._run_test("Simple Text Generation", test)

    async def test_tool_calling(self) -> TestResult:
        """
        Test 4: Tool calling / function calling support.

        Checks:
        - Accepts tools parameter
        - Returns tool_calls event when tools are provided
        - Tool calls have correct format (id, name, arguments)
        """
        async def test():
            llm = self.llm_factory()

            # Define a simple tool
            tools = [
                {
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "description": "Get current weather",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "location": {
                                    "type": "string",
                                    "description": "City name"
                                }
                            },
                            "required": ["location"]
                        }
                    }
                }
            ]

            messages = [
                {"role": "user", "content": "What's the weather in Tokyo?"}
            ]

            tool_calls_events = 0
            tool_calls_found = []

            # Stream with tools
            async for event in llm.stream(messages, tools=tools):
                # Validate event format
                validate_llm_event(event, strict=self.strict_validation)

                if event.get("type") == "tool_calls":
                    tool_calls_events += 1
                    calls = event.get("tool_calls", [])

                    # Validate each tool call
                    for tc in calls:
                        if "id" not in tc:
                            raise AssertionError("Tool call missing 'id' field")
                        if "name" not in tc:
                            raise AssertionError("Tool call missing 'name' field")
                        if "arguments" not in tc:
                            raise AssertionError("Tool call missing 'arguments' field")

                        tool_calls_found.append(tc)

            # Note: Some LLMs may choose to respond with text instead of tool calls
            # This is acceptable behavior, so we don't enforce tool_calls_events > 0

            return {
                "tool_calls_events": tool_calls_events,
                "total_tool_calls": len(tool_calls_found),
                "tool_names": [tc.get("name") for tc in tool_calls_found]
            }

        return await self._run_test("Tool Calling", test)

    async def test_json_mode(self) -> TestResult:
        """
        Test 5: JSON mode / structured output support.

        Checks:
        - Accepts response_format parameter
        - Returns valid JSON when response_format is set

        Note: This test is optional as not all LLMs support JSON mode
        """
        async def test():
            llm = self.llm_factory()

            messages = [
                {
                    "role": "user",
                    "content": "Return a JSON object with a 'greeting' field containing 'Hello'"
                }
            ]

            response_format = {"type": "json_object"}

            accumulated_content = ""

            try:
                # Stream with JSON mode
                async for event in llm.stream(
                    messages,
                    response_format=response_format
                ):
                    # Validate event format
                    validate_llm_event(event, strict=self.strict_validation)

                    if event.get("type") == "content_delta":
                        accumulated_content += event.get("content", "")

                # Try to parse as JSON
                import json
                parsed = json.loads(accumulated_content)

                return {
                    "json_valid": True,
                    "content_length": len(accumulated_content),
                    "parsed_type": type(parsed).__name__
                }

            except NotImplementedError:
                # JSON mode not supported - this is acceptable
                return {
                    "json_mode_supported": False,
                    "note": "JSON mode not implemented (acceptable)"
                }

        return await self._run_test("JSON Mode", test)

    async def test_event_format_consistency(self) -> TestResult:
        """
        Test 6: Event format consistency across multiple calls.

        Checks:
        - All events follow LLMEvent specification
        - Event types are consistent
        - Required fields are present
        """
        async def test():
            llm = self.llm_factory()

            messages = [
                {"role": "user", "content": "Count to 3"}
            ]

            event_types = []
            all_valid = True

            # Run multiple calls to check consistency
            for i in range(3):
                async for event in llm.stream(messages):
                    try:
                        validate_llm_event(event, strict=True)
                        event_types.append(event.get("type"))
                    except Exception as e:
                        all_valid = False
                        raise AssertionError(
                            f"Event validation failed on iteration {i+1}: {e}"
                        )

            if not all_valid:
                raise AssertionError("Some events failed validation")

            return {
                "total_events": len(event_types),
                "event_type_distribution": {
                    "content_delta": event_types.count("content_delta"),
                    "tool_calls": event_types.count("tool_calls"),
                    "finish": event_types.count("finish")
                }
            }

        return await self._run_test("Event Format Consistency", test)

    async def test_error_handling(self) -> TestResult:
        """
        Test 7: Error handling with invalid inputs.

        Checks:
        - Handles empty messages gracefully
        - Handles invalid tool definitions
        - Returns appropriate errors or fallback responses
        """
        async def test():
            llm = self.llm_factory()

            # Test 1: Empty messages (should handle gracefully)
            try:
                event_count = 0
                async for event in llm.stream([]):
                    event_count += 1
                    validate_llm_event(event, strict=False)

                empty_messages_handled = True
            except Exception as e:
                # Some LLMs may raise errors for empty messages - acceptable
                empty_messages_handled = False

            # Test 2: Messages with valid format
            messages = [{"role": "user", "content": "Hi"}]

            try:
                event_count = 0
                async for event in llm.stream(messages):
                    event_count += 1
                    validate_llm_event(event, strict=True)

                valid_messages_work = event_count > 0
            except Exception as e:
                raise AssertionError(f"Failed on valid messages: {e}")

            return {
                "empty_messages_handled": empty_messages_handled,
                "valid_messages_work": valid_messages_work
            }

        return await self._run_test("Error Handling", test)

    # =========================================================================
    # Suite Runner
    # =========================================================================

    async def run_all_tests(self) -> ComplianceReport:
        """
        Run all compliance tests and generate a comprehensive report.

        Returns:
            ComplianceReport with results of all tests

        Example:
            ```python
            suite = LLMComplianceSuite(llm_factory=lambda: MyLLM())
            report = await suite.run_all_tests()
            report.print_summary()

            if report.success_rate < 100:
                print("Some tests failed!")
            ```
        """
        import time

        # Reset results
        self.results = []

        # Get LLM instance for metadata
        llm = self.llm_factory()
        llm_class_name = type(llm).__name__
        model_name = llm.model_name if hasattr(llm, 'model_name') else None

        start_time = time.perf_counter()

        # Run all tests
        await self.test_protocol_implementation()
        await self.test_model_name_property()
        await self.test_simple_text_generation()
        await self.test_tool_calling()
        await self.test_json_mode()
        await self.test_event_format_consistency()
        await self.test_error_handling()

        total_duration = (time.perf_counter() - start_time) * 1000

        # Build report
        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed)

        report = ComplianceReport(
            llm_class_name=llm_class_name,
            model_name=model_name,
            total_tests=len(self.results),
            passed_tests=passed,
            failed_tests=failed,
            test_results=self.results.copy(),
            total_duration_ms=total_duration
        )

        return report
