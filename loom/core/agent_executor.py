"""
Agent Executor with tt (Tail-Recursive) Control Loop

Core execution engine implementing recursive conversation management,
inspired by Claude Code's tt function design.
"""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import AsyncGenerator, Dict, List, Optional
from uuid import uuid4

from loom.callbacks.base import BaseCallback
from loom.callbacks.metrics import MetricsCollector
from loom.core.context_assembly import ComponentPriority, ContextAssembler
from loom.core.events import AgentEvent, AgentEventType, ToolResult
from loom.core.execution_context import ExecutionContext
from loom.core.permissions import PermissionManager
from loom.core.steering_control import SteeringControl
from loom.core.tool_orchestrator import ToolOrchestrator
from loom.core.tool_pipeline import ToolExecutionPipeline
from loom.core.turn_state import TurnState
from loom.core.types import Message, ToolCall
from loom.interfaces.compressor import BaseCompressor
from loom.interfaces.llm import BaseLLM
from loom.interfaces.memory import BaseMemory
from loom.interfaces.tool import BaseTool
from loom.utils.token_counter import count_messages_tokens

# RAG support
try:
    from loom.core.context_retriever import ContextRetriever
except ImportError:
    ContextRetriever = None  # type: ignore


class AgentExecutor:
    """
    Agent Executor with tt Recursive Control Loop.

    Core Design:
    - tt() is the only execution method (tail-recursive)
    - All other methods are thin wrappers around tt()
    - No iteration loops - only recursion
    - Immutable state (TurnState)

    Example:
        ```python
        executor = AgentExecutor(llm=llm, tools=tools)

        # Initialize state
        turn_state = TurnState.initial(max_iterations=10)
        context = ExecutionContext.create()
        messages = [Message(role="user", content="Hello")]

        # Execute with tt recursion
        async for event in executor.tt(messages, turn_state, context):
            print(event)
        ```
    """

    def __init__(
        self,
        llm: BaseLLM,
        tools: Dict[str, BaseTool] | None = None,
        memory: BaseMemory | None = None,
        compressor: BaseCompressor | None = None,
        context_retriever: Optional["ContextRetriever"] = None,
        steering_control: SteeringControl | None = None,
        max_iterations: int = 50,
        max_context_tokens: int = 16000,
        permission_manager: PermissionManager | None = None,
        metrics: MetricsCollector | None = None,
        system_instructions: Optional[str] = None,
        callbacks: Optional[List[BaseCallback]] = None,
        enable_steering: bool = False,
    ) -> None:
        self.llm = llm
        self.tools = tools or {}
        self.memory = memory
        self.compressor = compressor
        self.context_retriever = context_retriever
        self.steering_control = steering_control or SteeringControl()
        self.max_iterations = max_iterations
        self.max_context_tokens = max_context_tokens
        self.metrics = metrics or MetricsCollector()
        self.permission_manager = permission_manager or PermissionManager(
            policy={"default": "allow"}
        )
        self.system_instructions = system_instructions
        self.callbacks = callbacks or []
        self.enable_steering = enable_steering

        # Tool execution (legacy pipeline for backward compatibility)
        self.tool_pipeline = ToolExecutionPipeline(
            self.tools,
            permission_manager=self.permission_manager,
            metrics=self.metrics,
        )

        # Tool orchestration (Loom 2.0 - intelligent parallel/sequential execution)
        self.tool_orchestrator = ToolOrchestrator(
            tools=self.tools,
            permission_manager=self.permission_manager,
            max_parallel=5,
        )

    # ==========================================
    # CORE METHOD: tt (Tail-Recursive Control Loop)
    # ==========================================

    async def tt(
        self,
        messages: List[Message],
        turn_state: TurnState,
        context: ExecutionContext,
    ) -> AsyncGenerator[AgentEvent, None]:
        """
        Tail-recursive control loop (inspired by Claude Code).

        This is the ONLY core execution method. It processes one turn of the
        conversation, then recursively calls itself if tools were used.

        Recursion Flow:
            tt(messages, state_0, ctx)
              → LLM generates tool calls
              → Execute tools
              → tt(messages + tool_results, state_1, ctx)  # Recursive call
                  → LLM generates final answer
                  → return (base case)

        Base Cases (recursion terminates):
        1. LLM returns final answer (no tools)
        2. Maximum recursion depth reached
        3. Execution cancelled
        4. Error occurred

        Args:
            messages: New messages for this turn (not full history)
            turn_state: Immutable turn state
            context: Shared execution context

        Yields:
            AgentEvent: Events representing execution progress

        Example:
            ```python
            # Initial turn
            state = TurnState.initial(max_iterations=10)
            context = ExecutionContext.create()
            messages = [Message(role="user", content="Search files")]

            async for event in executor.tt(messages, state, context):
                if event.type == AgentEventType.AGENT_FINISH:
                    print(f"Done: {event.content}")
            ```
        """
        # ==========================================
        # Phase 0: Recursion Control
        # ==========================================
        yield AgentEvent(
            type=AgentEventType.ITERATION_START,
            iteration=turn_state.turn_counter,
            turn_id=turn_state.turn_id,
            metadata={"parent_turn_id": turn_state.parent_turn_id},
        )

        # Base case 1: Maximum recursion depth reached
        if turn_state.is_final:
            yield AgentEvent(
                type=AgentEventType.MAX_ITERATIONS_REACHED,
                metadata={
                    "turn_counter": turn_state.turn_counter,
                    "max_iterations": turn_state.max_iterations,
                },
            )
            await self._emit(
                "max_iterations_reached",
                {
                    "turn_counter": turn_state.turn_counter,
                    "max_iterations": turn_state.max_iterations,
                },
            )
            return

        # Base case 2: Execution cancelled
        if context.is_cancelled():
            yield AgentEvent(
                type=AgentEventType.EXECUTION_CANCELLED,
                metadata={"correlation_id": context.correlation_id},
            )
            await self._emit(
                "execution_cancelled",
                {"correlation_id": context.correlation_id},
            )
            return

        # ==========================================
        # Phase 1: Context Assembly
        # ==========================================
        yield AgentEvent.phase_start("context_assembly")

        # Load conversation history from memory
        history = await self._load_history()

        # RAG retrieval (if configured)
        rag_context = None
        if self.context_retriever:
            yield AgentEvent(type=AgentEventType.RETRIEVAL_START)

            try:
                # Extract user query from last message
                user_query = ""
                for msg in reversed(messages):
                    if msg.role == "user":
                        user_query = msg.content
                        break

                if user_query:
                    retrieved_docs = await self.context_retriever.retrieve_for_query(
                        user_query
                    )

                    if retrieved_docs:
                        rag_context = self.context_retriever.format_documents(
                            retrieved_docs
                        )

                        # Emit retrieval progress
                        for doc in retrieved_docs:
                            yield AgentEvent(
                                type=AgentEventType.RETRIEVAL_PROGRESS,
                                metadata={
                                    "doc_title": doc.metadata.get("title", "Unknown"),
                                    "relevance_score": doc.metadata.get("score", 0.0),
                                },
                            )

                    yield AgentEvent(
                        type=AgentEventType.RETRIEVAL_COMPLETE,
                        metadata={"doc_count": len(retrieved_docs)},
                    )
                    self.metrics.metrics.retrievals = (
                        getattr(self.metrics.metrics, "retrievals", 0) + 1
                    )

            except Exception as e:
                yield AgentEvent.error(e, retrieval_failed=True)

        # Add new messages to history
        history.extend(messages)

        # Compression check
        old_len = len(history)
        history_compacted = await self._maybe_compress(history)
        compacted_this_turn = len(history_compacted) < old_len

        if compacted_this_turn:
            history = history_compacted
            yield AgentEvent(
                type=AgentEventType.COMPRESSION_APPLIED,
                metadata={
                    "messages_before": old_len,
                    "messages_after": len(history),
                },
            )

        # Assemble system prompt using ContextAssembler
        assembler = ContextAssembler(max_tokens=self.max_context_tokens)

        # Add base instructions (critical priority)
        if self.system_instructions:
            assembler.add_component(
                name="base_instructions",
                content=self.system_instructions,
                priority=ComponentPriority.CRITICAL,
                truncatable=False,
            )

        # Add RAG context (high priority)
        if rag_context:
            assembler.add_component(
                name="retrieved_context",
                content=rag_context,
                priority=ComponentPriority.HIGH,
                truncatable=True,
            )

        # Add tool definitions (medium priority)
        if self.tools:
            tools_spec = self._serialize_tools()
            tools_prompt = f"Available tools:\n{json.dumps(tools_spec, indent=2)}"
            assembler.add_component(
                name="tool_definitions",
                content=tools_prompt,
                priority=ComponentPriority.MEDIUM,
                truncatable=False,
            )

        # Assemble final system prompt
        final_system_prompt = assembler.assemble()

        # Inject system prompt into history
        if history and history[0].role == "system":
            history[0] = Message(role="system", content=final_system_prompt)
        else:
            history.insert(0, Message(role="system", content=final_system_prompt))

        # Emit context assembly summary
        summary = assembler.get_summary()
        yield AgentEvent.phase_end(
            "context_assembly",
            tokens_used=summary["total_tokens"],
            metadata={
                "components": len(summary["components"]),
                "utilization": summary["utilization"],
            },
        )

        # ==========================================
        # Phase 2: LLM Call
        # ==========================================
        yield AgentEvent(type=AgentEventType.LLM_START)

        try:
            if self.llm.supports_tools and self.tools:
                # LLM with tool support
                tools_spec = self._serialize_tools()
                response = await self.llm.generate_with_tools(
                    [m.__dict__ for m in history], tools_spec
                )

                content = response.get("content", "")
                tool_calls = response.get("tool_calls", [])

                # Emit LLM content if available
                if content:
                    yield AgentEvent(type=AgentEventType.LLM_DELTA, content=content)

            else:
                # Simple LLM generation (streaming)
                content_parts = []
                async for delta in self.llm.stream([m.__dict__ for m in history]):
                    content_parts.append(delta)
                    yield AgentEvent(type=AgentEventType.LLM_DELTA, content=delta)

                content = "".join(content_parts)
                tool_calls = []

            yield AgentEvent(type=AgentEventType.LLM_COMPLETE)

        except Exception as e:
            self.metrics.metrics.total_errors += 1
            yield AgentEvent.error(e, llm_failed=True)
            await self._emit("error", {"stage": "llm_call", "message": str(e)})
            return

        self.metrics.metrics.llm_calls += 1

        # ==========================================
        # Phase 3: Decision Point (Base Case or Recurse)
        # ==========================================

        if not tool_calls:
            # Base case: No tools → Conversation complete
            yield AgentEvent(
                type=AgentEventType.AGENT_FINISH,
                content=content,
                metadata={
                    "turn_counter": turn_state.turn_counter,
                    "total_llm_calls": self.metrics.metrics.llm_calls,
                },
            )

            # Save to memory
            if self.memory and content:
                await self.memory.add_message(
                    Message(role="assistant", content=content)
                )

            await self._emit("agent_finish", {"content": content})
            return

        # ==========================================
        # Phase 4: Tool Execution
        # ==========================================
        yield AgentEvent(
            type=AgentEventType.LLM_TOOL_CALLS,
            metadata={
                "tool_count": len(tool_calls),
                "tool_names": [tc.get("name") for tc in tool_calls],
            },
        )

        # Convert to ToolCall models
        tc_models = [self._to_tool_call(tc) for tc in tool_calls]

        # Execute tools using ToolOrchestrator
        tool_results: List[ToolResult] = []
        try:
            async for event in self.tool_orchestrator.execute_batch(tc_models):
                yield event  # Forward all tool events

                if event.type == AgentEventType.TOOL_RESULT:
                    tool_results.append(event.tool_result)

                    # Add to memory
                    tool_msg = Message(
                        role="tool",
                        content=event.tool_result.content,
                        tool_call_id=event.tool_result.tool_call_id,
                    )
                    if self.memory:
                        await self.memory.add_message(tool_msg)

                elif event.type == AgentEventType.TOOL_ERROR:
                    # Collect error results too
                    if event.tool_result:
                        tool_results.append(event.tool_result)

        except Exception as e:
            self.metrics.metrics.total_errors += 1
            yield AgentEvent.error(e, tool_execution_failed=True)
            await self._emit("error", {"stage": "tool_execution", "message": str(e)})
            return

        yield AgentEvent(
            type=AgentEventType.TOOL_CALLS_COMPLETE,
            metadata={"results_count": len(tool_results)},
        )

        self.metrics.metrics.total_iterations += 1

        # ==========================================
        # Phase 5: Recursive Call (Tail Recursion)
        # ==========================================

        # Prepare next turn state
        next_state = turn_state.next_turn(compacted=compacted_this_turn)

        # Prepare next turn messages (only new messages, not full history)
        next_messages = [
            Message(
                role="tool",
                content=r.content,
                tool_call_id=r.tool_call_id,
            )
            for r in tool_results
        ]

        # Emit recursion event
        yield AgentEvent(
            type=AgentEventType.RECURSION,
            metadata={
                "from_turn": turn_state.turn_id,
                "to_turn": next_state.turn_id,
                "depth": next_state.turn_counter,
            },
        )

        # 🔥 Tail-recursive call
        async for event in self.tt(next_messages, next_state, context):
            yield event

    # ==========================================
    # Helper Methods
    # ==========================================

    async def _load_history(self) -> List[Message]:
        """Load conversation history from memory."""
        if not self.memory:
            return []
        return await self.memory.get_messages()

    async def _maybe_compress(self, history: List[Message]) -> List[Message]:
        """Check if compression needed and apply if threshold reached."""
        if not self.compressor:
            return history

        tokens_before = count_messages_tokens(history)

        # Check if compression should be triggered (92% threshold)
        if self.compressor.should_compress(tokens_before, self.max_context_tokens):
            try:
                compressed_messages, metadata = await self.compressor.compress(history)

                # Update metrics
                self.metrics.metrics.compressions = (
                    getattr(self.metrics.metrics, "compressions", 0) + 1
                )
                if metadata.key_topics == ["fallback"]:
                    self.metrics.metrics.compression_fallbacks = (
                        getattr(self.metrics.metrics, "compression_fallbacks", 0) + 1
                    )

                # Emit compression event
                await self._emit(
                    "compression_applied",
                    {
                        "before_tokens": metadata.original_tokens,
                        "after_tokens": metadata.compressed_tokens,
                        "compression_ratio": metadata.compression_ratio,
                        "original_message_count": metadata.original_message_count,
                        "compressed_message_count": metadata.compressed_message_count,
                        "key_topics": metadata.key_topics,
                        "fallback_used": metadata.key_topics == ["fallback"],
                    },
                )

                return compressed_messages

            except Exception as e:
                self.metrics.metrics.total_errors += 1
                await self._emit(
                    "error",
                    {"stage": "compression", "message": str(e)},
                )
                return history

        return history

    def _serialize_tools(self) -> List[Dict]:
        """Serialize tools to LLM-compatible format."""
        tools_spec: List[Dict] = []
        for t in self.tools.values():
            schema = {}
            try:
                schema = t.args_schema.model_json_schema()  # type: ignore[attr-defined]
            except Exception:
                schema = {"type": "object", "properties": {}}

            tools_spec.append(
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": getattr(t, "description", ""),
                        "parameters": schema,
                    },
                }
            )
        return tools_spec

    def _to_tool_call(self, raw: Dict) -> ToolCall:
        """Convert raw dict to ToolCall model."""
        return ToolCall(
            id=str(raw.get("id", "call_0")),
            name=raw["name"],
            arguments=raw.get("arguments", {}),
        )

    async def _emit(self, event_type: str, payload: Dict) -> None:
        """Emit event to callbacks."""
        if not self.callbacks:
            return

        enriched = dict(payload)
        enriched.setdefault("ts", time.time())
        enriched.setdefault("type", event_type)

        for cb in self.callbacks:
            try:
                await cb.on_event(event_type, enriched)
            except Exception:
                # Best-effort; don't fail execution on callback errors
                pass

    # ==========================================
    # Backward Compatibility Wrappers
    # ==========================================

    async def execute(
        self,
        user_input: str,
        cancel_token: Optional[asyncio.Event] = None,
        correlation_id: Optional[str] = None,
    ) -> str:
        """
        Execute agent and return final response (backward compatible wrapper).

        This method wraps the new tt() recursive API and extracts the final
        response for backward compatibility with existing code.

        Args:
            user_input: User input text
            cancel_token: Optional cancellation event
            correlation_id: Optional correlation ID for tracing

        Returns:
            str: Final response text

        Example:
            ```python
            executor = AgentExecutor(llm=llm, tools=tools)
            response = await executor.execute("Hello")
            print(response)
            ```
        """
        # Initialize state and context
        turn_state = TurnState.initial(max_iterations=self.max_iterations)
        context = ExecutionContext.create(
            correlation_id=correlation_id,
            cancel_token=cancel_token,
        )
        messages = [Message(role="user", content=user_input)]

        # Execute with tt and collect result
        final_content = ""
        async for event in self.tt(messages, turn_state, context):
            # Accumulate LLM deltas
            if event.type == AgentEventType.LLM_DELTA:
                final_content += event.content or ""

            # Return on finish
            elif event.type == AgentEventType.AGENT_FINISH:
                return event.content or final_content

            # Handle cancellation
            elif event.type == AgentEventType.EXECUTION_CANCELLED:
                return "cancelled"

            # Handle max iterations
            elif event.type == AgentEventType.MAX_ITERATIONS_REACHED:
                return final_content or "Max iterations reached"

            # Raise on error
            elif event.type == AgentEventType.ERROR:
                if event.error:
                    raise event.error

        return final_content
