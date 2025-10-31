"""
Example: Phase 3 Message Passing Optimization

Demonstrates the enhanced message passing system including:
1. Tool result propagation
2. Automatic context compression
3. Recursion depth hints
"""

import asyncio
from typing import List, Dict, Any, AsyncGenerator
from pydantic import BaseModel

from loom.core.agent_executor import AgentExecutor
from loom.core.turn_state import TurnState
from loom.core.execution_context import ExecutionContext
from loom.core.events import AgentEvent, AgentEventType
from loom.core.types import Message
from loom.interfaces.llm import BaseLLM
from loom.interfaces.tool import BaseTool
from loom.interfaces.compressor import BaseCompressor
from loom.utils.token_counter import count_messages_tokens


# ===== Mock Components =====

class MultiStepLLM(BaseLLM):
    """LLM that performs multi-step tasks"""

    def __init__(self, steps_needed: int = 5):
        self.steps_needed = steps_needed
        self.step_count = 0

    @property
    def model_name(self) -> str:
        return "multi-step-llm"

    @property
    def supports_tools(self) -> bool:
        return True

    async def generate(self, messages: List[Dict]) -> str:
        return "Processing..."

    async def generate_with_tools(
        self, messages: List[Dict], tools: List[Dict]
    ) -> Dict[str, Any]:
        self.step_count += 1

        if self.step_count < self.steps_needed:
            return {
                "content": f"Step {self.step_count} completed",
                "tool_calls": [
                    {
                        "id": f"call_{self.step_count}",
                        "name": "analyze_step",
                        "arguments": {"step_num": self.step_count}
                    }
                ]
            }
        else:
            return {
                "content": f"✅ All {self.step_count} steps completed successfully!",
                "tool_calls": []
            }

    async def stream(self, messages: List[Dict]) -> AsyncGenerator[str, None]:
        yield "Working..."


class VerboseLLM(BaseLLM):
    """LLM that generates very long outputs"""

    def __init__(self, iterations: int = 3):
        self.iterations = iterations
        self.call_count = 0

    @property
    def model_name(self) -> str:
        return "verbose-llm"

    @property
    def supports_tools(self) -> bool:
        return True

    async def generate(self, messages: List[Dict]) -> str:
        return "x" * 1000

    async def generate_with_tools(
        self, messages: List[Dict], tools: List[Dict]
    ) -> Dict[str, Any]:
        self.call_count += 1

        if self.call_count < self.iterations:
            # Generate very long content
            long_content = f"Analysis {self.call_count}: " + ("x" * 2000)
            return {
                "content": long_content,
                "tool_calls": [
                    {
                        "id": f"call_{self.call_count}",
                        "name": "process_data",
                        "arguments": {}
                    }
                ]
            }
        else:
            return {
                "content": "Processing complete with compressed context!",
                "tool_calls": []
            }

    async def stream(self, messages: List[Dict]) -> AsyncGenerator[str, None]:
        yield "Processing..."


class AnalyzeToolArgs(BaseModel):
    """Arguments for analyze tool"""
    step_num: int = 0


class AnalyzeStepTool(BaseTool):
    """Tool that analyzes a step"""

    name: str = "analyze_step"
    description: str = "Analyze a processing step"
    args_schema: type[BaseModel] = AnalyzeToolArgs

    async def run(self, **kwargs) -> str:
        step_num = kwargs.get("step_num", 0)
        return f"📊 Analysis for step {step_num}: Data processed successfully"


class ProcessDataToolArgs(BaseModel):
    """Arguments for process data tool"""
    pass


class ProcessDataTool(BaseTool):
    """Tool that processes data"""

    name: str = "process_data"
    description: str = "Process data"
    args_schema: type[BaseModel] = ProcessDataToolArgs

    async def run(self, **kwargs) -> str:
        # Return long data to trigger compression
        return "Processed: " + ("data_" * 500)


class DemoCompressor(BaseCompressor):
    """Demo compressor that keeps only recent messages"""

    def should_compress(self, current_tokens: int, max_tokens: int) -> bool:
        return current_tokens > max_tokens

    async def compress(self, messages: List[Message]):
        """Keep only system messages and last 3 messages"""
        from unittest.mock import MagicMock

        system_msgs = [m for m in messages if m.role == "system"]
        other_msgs = [m for m in messages if m.role != "system"]

        # Keep last 3 non-system messages
        compressed = system_msgs + other_msgs[-3:]

        metadata = MagicMock()
        metadata.original_tokens = count_messages_tokens(messages)
        metadata.compressed_tokens = count_messages_tokens(compressed)
        metadata.compression_ratio = len(compressed) / len(messages) if messages else 1.0
        metadata.original_message_count = len(messages)
        metadata.compressed_message_count = len(compressed)
        metadata.key_topics = ["demo"]

        return compressed, metadata


# ===== Examples =====

async def example_1_tool_result_propagation():
    """
    Example 1: Tool results are automatically propagated to next iteration
    """
    print("\n" + "="*70)
    print("Example 1: Tool Result Propagation")
    print("="*70)

    llm = MultiStepLLM(steps_needed=5)
    tools = {"analyze_step": AnalyzeStepTool()}

    executor = AgentExecutor(llm=llm, tools=tools)

    turn_state = TurnState.initial(max_iterations=10)
    context = ExecutionContext.create()
    messages = [Message(role="user", content="Perform multi-step analysis")]

    print("\n🚀 Starting multi-step task...")
    print("   Each step's results will be passed to the next iteration\n")

    tool_results_seen = []
    async for event in executor.tt(messages, turn_state, context):
        if event.type == AgentEventType.TOOL_RESULT:
            result_content = event.tool_result.content if event.tool_result else ""
            tool_results_seen.append(result_content)
            print(f"   🔧 {result_content}")

        elif event.type == AgentEventType.RECURSION:
            depth = event.metadata.get("depth", 0)
            msg_count = event.metadata.get("message_count", 0)
            print(f"   📨 Recursion {depth}: {msg_count} messages prepared")

        elif event.type == AgentEventType.AGENT_FINISH:
            print(f"\n{event.content}")

    print(f"\n✨ Total steps: {len(tool_results_seen)}")
    print("   All tool results were successfully propagated!")


async def example_2_automatic_compression():
    """
    Example 2: Automatic compression when context gets too long
    """
    print("\n" + "="*70)
    print("Example 2: Automatic Context Compression")
    print("="*70)

    llm = VerboseLLM(iterations=4)
    tools = {"process_data": ProcessDataTool()}
    compressor = DemoCompressor()

    # Low token limit to trigger compression
    executor = AgentExecutor(
        llm=llm,
        tools=tools,
        compressor=compressor,
        max_context_tokens=500
    )

    turn_state = TurnState.initial(max_iterations=10)
    context = ExecutionContext.create()
    messages = [Message(role="user", content="Process large dataset")]

    print("\n🚀 Starting task with automatic compression...")
    print(f"   Max context: 500 tokens\n")

    compression_count = 0
    async for event in executor.tt(messages, turn_state, context):
        if event.type == AgentEventType.COMPRESSION_APPLIED:
            compression_count += 1
            before = event.metadata.get("tokens_before", 0)
            after = event.metadata.get("tokens_after", 0)
            reduction = before - after
            print(f"   📉 Compression #{compression_count}:")
            print(f"      Before: {before} tokens")
            print(f"      After:  {after} tokens")
            print(f"      Saved:  {reduction} tokens ({(reduction/before*100):.0f}%)\n")

        elif event.type == AgentEventType.AGENT_FINISH:
            print(f"✅ {event.content}")

    print(f"\n✨ Total compressions: {compression_count}")
    print("   Context was automatically managed!")


async def example_3_recursion_depth_hints():
    """
    Example 3: Recursion depth hints appear at deep recursions
    """
    print("\n" + "="*70)
    print("Example 3: Recursion Depth Hints")
    print("="*70)

    llm = MultiStepLLM(steps_needed=6)
    tools = {"analyze_step": AnalyzeStepTool()}

    executor = AgentExecutor(llm=llm, tools=tools)

    turn_state = TurnState.initial(max_iterations=10)
    context = ExecutionContext.create()
    messages = [Message(role="user", content="Deep analysis task")]

    print("\n🚀 Starting deep recursion task...")
    print("   Hints will appear at depth > 3\n")

    async for event in executor.tt(messages, turn_state, context):
        if event.type == AgentEventType.RECURSION:
            depth = event.metadata.get("depth", 0)
            msg_count = event.metadata.get("message_count", 0)

            if depth > 3:
                print(f"   ⚠️  Depth {depth}: {msg_count} messages (hint added)")
            else:
                print(f"   🔄 Depth {depth}: {msg_count} messages")

        elif event.type == AgentEventType.AGENT_FINISH:
            print(f"\n✅ {event.content}")


async def example_4_monitoring_message_counts():
    """
    Example 4: Monitor message counts to see optimization effect
    """
    print("\n" + "="*70)
    print("Example 4: Message Count Monitoring")
    print("="*70)

    llm = MultiStepLLM(steps_needed=5)
    tools = {"analyze_step": AnalyzeStepTool()}

    executor = AgentExecutor(llm=llm, tools=tools)

    turn_state = TurnState.initial(max_iterations=10)
    context = ExecutionContext.create()
    messages = [Message(role="user", content="Monitored task")]

    print("\n📊 Monitoring message counts at each recursion...\n")

    message_counts = []
    async for event in executor.tt(messages, turn_state, context):
        if event.type == AgentEventType.RECURSION:
            depth = event.metadata.get("depth", 0)
            msg_count = event.metadata.get("message_count", 0)
            message_counts.append(msg_count)

            # Show growth pattern
            if depth == 1:
                print(f"   Depth {depth}: {msg_count} messages (baseline)")
            else:
                growth = msg_count - message_counts[0]
                print(f"   Depth {depth}: {msg_count} messages (+{growth})")

        elif event.type == AgentEventType.AGENT_FINISH:
            print(f"\n✅ Completed")

    if message_counts:
        avg_count = sum(message_counts) / len(message_counts)
        print(f"\n📈 Average messages per recursion: {avg_count:.1f}")


async def main():
    """Run all examples"""
    print("\n" + "="*70)
    print(" Phase 3: Message Passing Optimization Examples")
    print("="*70)

    await example_1_tool_result_propagation()
    await example_2_automatic_compression()
    await example_3_recursion_depth_hints()
    await example_4_monitoring_message_counts()

    print("\n" + "="*70)
    print(" All examples completed!")
    print("="*70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
