"""
Example: Recursion Control in Action

This example demonstrates how the Phase 2 recursion control system
prevents infinite loops and improves agent stability.
"""

import asyncio
from typing import Dict, Any, List, AsyncGenerator
from pydantic import BaseModel

from loom.core.agent_executor import AgentExecutor
from loom.core.recursion_control import RecursionMonitor, TerminationReason
from loom.core.turn_state import TurnState
from loom.core.execution_context import ExecutionContext
from loom.core.events import AgentEvent, AgentEventType
from loom.core.types import Message
from loom.interfaces.llm import BaseLLM
from loom.interfaces.tool import BaseTool


# ===== Mock LLM that simulates looping behavior =====

class LoopingLLM(BaseLLM):
    """Simulates an LLM that gets stuck calling the same tool repeatedly"""

    def __init__(self):
        self.call_count = 0

    @property
    def model_name(self) -> str:
        return "mock-looping-llm"

    @property
    def supports_tools(self) -> bool:
        return True

    async def generate(self, messages: List[Dict]) -> str:
        return "I'm searching for information..."

    async def generate_with_tools(
        self, messages: List[Dict], tools: List[Dict]
    ) -> Dict[str, Any]:
        self.call_count += 1

        # Simulate getting stuck: keep calling "search" tool
        if self.call_count < 15:
            return {
                "content": "",
                "tool_calls": [
                    {
                        "id": f"call_{self.call_count}",
                        "name": "search",
                        "arguments": {"query": f"attempt {self.call_count}"}
                    }
                ]
            }
        else:
            # Eventually give up
            return {
                "content": "I couldn't find the information after multiple attempts.",
                "tool_calls": []
            }

    async def stream(self, messages: List[Dict]) -> AsyncGenerator[str, None]:
        yield "Searching..."


# ===== Mock Tool =====

class SearchArgs(BaseModel):
    """Search tool arguments"""
    query: str = "default"


class SearchTool(BaseTool):
    """Mock search tool"""

    name: str = "search"
    description: str = "Search for information"
    args_schema: type[BaseModel] = SearchArgs

    async def run(self, **kwargs) -> str:
        query = kwargs.get("query", "default")
        return f"Search results for: {query} (no results found)"


# ===== Examples =====

async def example_1_default_recursion_control():
    """
    Example 1: Default recursion control prevents infinite loops
    """
    print("\n" + "="*70)
    print("Example 1: Default Recursion Control")
    print("="*70)

    llm = LoopingLLM()
    tools = {"search": SearchTool()}

    # Default recursion control (enabled by default)
    executor = AgentExecutor(
        llm=llm,
        tools=tools,
        enable_recursion_control=True  # This is the default
    )

    turn_state = TurnState.initial(max_iterations=50)
    context = ExecutionContext.create()
    messages = [Message(role="user", content="Find information about AI")]

    print("\n🚀 Starting execution with default recursion control...")
    print("   (Will detect duplicate tool calls and terminate)\n")

    iteration_count = 0
    termination_detected = False

    async for event in executor.tt(messages, turn_state, context):
        if event.type == AgentEventType.ITERATION_START:
            iteration_count += 1
            print(f"   Iteration {iteration_count}")

        elif event.type == AgentEventType.RECURSION_TERMINATED:
            termination_detected = True
            reason = event.metadata.get("reason", "unknown")
            print(f"\n⚠️  Recursion control triggered!")
            print(f"   Reason: {reason}")
            print(f"   Iteration: {event.metadata.get('iteration', 'unknown')}")
            print(f"   Tool history: {event.metadata.get('tool_call_history', [])[-5:]}")

        elif event.type == AgentEventType.AGENT_FINISH:
            print(f"\n✅ Agent finished: {event.content}\n")

    if termination_detected:
        print("✨ Recursion control successfully prevented an infinite loop!")
    else:
        print("⏭  Execution completed normally")


async def example_2_custom_thresholds():
    """
    Example 2: Custom recursion monitor with strict thresholds
    """
    print("\n" + "="*70)
    print("Example 2: Custom Recursion Monitor (Strict)")
    print("="*70)

    llm = LoopingLLM()
    tools = {"search": SearchTool()}

    # Custom monitor with very strict thresholds
    strict_monitor = RecursionMonitor(
        max_iterations=20,         # Lower max iterations
        duplicate_threshold=2,     # Terminate after just 2 duplicates
        error_threshold=0.9        # High error threshold to avoid false positives
    )

    executor = AgentExecutor(
        llm=llm,
        tools=tools,
        enable_recursion_control=True,
        recursion_monitor=strict_monitor
    )

    turn_state = TurnState.initial(max_iterations=20)
    context = ExecutionContext.create()
    messages = [Message(role="user", content="Search for quantum computing")]

    print("\n🚀 Starting with strict recursion control...")
    print("   (duplicate_threshold=2 - very sensitive)\n")

    termination_count = 0
    async for event in executor.tt(messages, turn_state, context):
        if event.type == AgentEventType.RECURSION_TERMINATED:
            termination_count += 1
            reason = TerminationReason(event.metadata["reason"])
            print(f"⚠️  Termination #{termination_count}: {reason.value}")

        elif event.type == AgentEventType.AGENT_FINISH:
            print(f"✅ Finished: {event.content}\n")

    print(f"Total terminations detected: {termination_count}")


async def example_3_disabled_recursion_control():
    """
    Example 3: Disabled recursion control (for comparison)
    """
    print("\n" + "="*70)
    print("Example 3: Recursion Control Disabled (Comparison)")
    print("="*70)

    llm = LoopingLLM()
    tools = {"search": SearchTool()}

    # Disable recursion control
    executor = AgentExecutor(
        llm=llm,
        tools=tools,
        max_iterations=8,  # Use a low max to prevent actual infinite loop
        enable_recursion_control=False  # DISABLED
    )

    turn_state = TurnState.initial(max_iterations=8)
    context = ExecutionContext.create()
    messages = [Message(role="user", content="Find research papers")]

    print("\n🚀 Starting WITHOUT recursion control...")
    print("   (Will run until max_iterations=8)\n")

    iteration_count = 0
    async for event in executor.tt(messages, turn_state, context):
        if event.type == AgentEventType.ITERATION_START:
            iteration_count += 1

        elif event.type == AgentEventType.RECURSION_TERMINATED:
            print("   ⚠️  Recursion terminated (shouldn't happen - disabled)")

        elif event.type == AgentEventType.MAX_ITERATIONS_REACHED:
            print(f"   ⛔ Hit max iterations: {iteration_count}")

        elif event.type == AgentEventType.AGENT_FINISH:
            print(f"   ✅ Finished: {event.content}\n")

    print(f"Note: Without recursion control, ran all {iteration_count} iterations")
    print("      before hitting max_iterations limit.")


async def example_4_event_monitoring():
    """
    Example 4: Monitoring recursion control events
    """
    print("\n" + "="*70)
    print("Example 4: Event Monitoring")
    print("="*70)

    llm = LoopingLLM()
    tools = {"search": SearchTool()}

    monitor = RecursionMonitor(duplicate_threshold=3, error_threshold=0.9)
    executor = AgentExecutor(
        llm=llm,
        tools=tools,
        recursion_monitor=monitor
    )

    turn_state = TurnState.initial(max_iterations=50)
    context = ExecutionContext.create()
    messages = [Message(role="user", content="Research AI safety")]

    print("\n📊 Monitoring all recursion-related events...\n")

    events_summary = {
        "iterations": 0,
        "tool_calls": 0,
        "terminations": [],
        "warnings": 0
    }

    async for event in executor.tt(messages, turn_state, context):
        if event.type == AgentEventType.ITERATION_START:
            events_summary["iterations"] += 1

        elif event.type == AgentEventType.LLM_TOOL_CALLS:
            tool_count = event.metadata.get("tool_count", 0)
            events_summary["tool_calls"] += tool_count

        elif event.type == AgentEventType.RECURSION_TERMINATED:
            reason = event.metadata.get("reason", "unknown")
            events_summary["terminations"].append(reason)
            print(f"   🚨 Termination: {reason}")

        elif event.type == AgentEventType.AGENT_FINISH:
            print(f"\n✅ Final result: {event.content}\n")

    # Print summary
    print("📊 Execution Summary:")
    print(f"   Total iterations: {events_summary['iterations']}")
    print(f"   Total tool calls: {events_summary['tool_calls']}")
    print(f"   Terminations: {len(events_summary['terminations'])}")
    if events_summary['terminations']:
        print(f"   Termination reasons: {events_summary['terminations']}")


async def main():
    """Run all examples"""
    print("\n" + "="*70)
    print(" Phase 2: Recursion Control Examples")
    print("="*70)

    # Run all examples
    await example_1_default_recursion_control()
    await example_2_custom_thresholds()
    await example_3_disabled_recursion_control()
    await example_4_event_monitoring()

    print("\n" + "="*70)
    print(" All examples completed!")
    print("="*70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
