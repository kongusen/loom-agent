"""
State Reconstructor: Rebuild Execution State from Event Stream

This module implements the "rehydration" logic for event sourcing.
Given a stream of events, it reconstructs the ExecutionFrame state.

Key Advantage over LangGraph:
- LangGraph: Load static snapshot → Fixed state
- loom-agent: Replay events → Can apply NEW strategies during replay

Example: Context compression strategy evolved
    # Original execution (v1 compression)
    events = [Event1, Event2, Event3, ...]

    # System crash, restart with v2 compression
    reconstructor = StateReconstructor(compression_strategy="v2")
    frame = await reconstructor.reconstruct(events)

    # The reconstructed state uses v2 compression!
    # LangGraph can't do this - it's locked to v1 snapshot

Use Cases:
    1. Crash recovery - Resume execution after failure
    2. Time-travel debugging - Reconstruct state at any point
    3. Strategy upgrades - Apply new logic to old events
    4. Audit analysis - Understand historical decisions

Example:
    ```python
    # Crash occurred at iteration 5
    journal = EventJournal(path)
    events = await journal.replay(thread_id="user-123")

    # Reconstruct state
    reconstructor = StateReconstructor()
    frame = await reconstructor.reconstruct(events)

    # Continue execution from reconstructed state
    async for event in agent.execute(
        prompt=None,
        initial_frame=frame  # Resume from here!
    ):
        print(event)
    ```
"""

from __future__ import annotations

from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from .execution_frame import ExecutionFrame, ExecutionPhase
from .events import AgentEvent, AgentEventType


@dataclass
class ReconstructionMetadata:
    """
    Metadata about the reconstruction process.

    Useful for debugging and understanding what happened during replay.

    Attributes:
        total_events: Total events processed
        events_by_type: Count of each event type
        reconstruction_time_ms: Time taken to reconstruct
        warnings: Any warnings during reconstruction
        final_phase: Final phase of reconstructed frame
    """
    total_events: int
    events_by_type: Dict[str, int]
    reconstruction_time_ms: float
    warnings: List[str]
    final_phase: str


class StateReconstructor:
    """
    Reconstructs ExecutionFrame from event stream.

    This is the "rehydration" component of event sourcing.
    It processes events in chronological order and builds up state.

    Features:
    - Idempotent reconstruction (same events → same state)
    - Partial reconstruction (reconstruct up to specific event)
    - Strategy injection (apply new compression/context strategies)
    - Validation (detect inconsistencies)
    """

    def __init__(
        self,
        context_assembler=None,
        compression_manager=None,
        validate: bool = True
    ):
        """
        Initialize state reconstructor.

        Args:
            context_assembler: Optional ContextAssembler (use new strategy)
            compression_manager: Optional CompressionManager (use new strategy)
            validate: Whether to validate reconstructed state
        """
        self.context_assembler = context_assembler
        self.compression_manager = compression_manager
        self.validate = validate

    async def reconstruct(
        self,
        events: List[AgentEvent],
        up_to_sequence: Optional[int] = None
    ) -> tuple[ExecutionFrame, ReconstructionMetadata]:
        """
        Reconstruct ExecutionFrame from event stream.

        Args:
            events: Chronological list of events
            up_to_sequence: Optional - only reconstruct up to this event

        Returns:
            Tuple of (ExecutionFrame, ReconstructionMetadata)

        Process:
            1. Initialize empty frame
            2. Process each event in order
            3. Apply event to update frame state
            4. Return final reconstructed frame

        Example:
            ```python
            events = await journal.replay(thread_id="user-123")

            reconstructor = StateReconstructor()
            frame, metadata = await reconstructor.reconstruct(events)

            print(f"Reconstructed {metadata.total_events} events")
            print(f"Final depth: {frame.depth}")
            print(frame.summary())
            ```
        """
        import time
        start_time = time.time()

        # Tracking
        events_by_type: Dict[str, int] = {}
        warnings: List[str] = []

        # Initialize with minimal frame
        frame: Optional[ExecutionFrame] = None
        messages: List[Dict[str, Any]] = []
        context_snapshot: Dict[str, Any] = {}
        context_metadata: Dict[str, Any] = {}
        llm_response_parts: List[str] = []
        llm_tool_calls: List[Dict[str, Any]] = []
        tool_results: List[Dict[str, Any]] = []
        current_depth = 0
        max_iterations = 50  # Default
        tool_call_history: List[str] = []
        error_count = 0
        last_outputs: List[str] = []

        # Process events
        for i, event in enumerate(events):
            # Check sequence limit
            if up_to_sequence is not None and i >= up_to_sequence:
                break

            # Track event types
            event_type_str = event.type.value
            events_by_type[event_type_str] = events_by_type.get(event_type_str, 0) + 1

            # === Phase Events ===
            if event.type == AgentEventType.ITERATION_START:
                # New iteration starting
                current_depth = event.iteration or 0

                # If we have accumulated data, create frame
                if frame is None and messages:
                    frame = ExecutionFrame(
                        frame_id=event.turn_id or "reconstructed",
                        depth=current_depth,
                        phase=ExecutionPhase.INITIAL,
                        messages=messages.copy(),
                        max_iterations=max_iterations
                    )

            # === Context Events ===
            elif event.type == AgentEventType.CONTEXT_ASSEMBLY_COMPLETE:
                # Context was assembled
                if event.metadata:
                    context_metadata = event.metadata.copy()

            elif event.type == AgentEventType.COMPRESSION_APPLIED:
                # Compression was applied
                if event.metadata:
                    compressed_data = event.metadata.get("compressed_context", {})
                    context_snapshot.update(compressed_data)

            # === LLM Events ===
            elif event.type == AgentEventType.LLM_START:
                # LLM call started - reset response accumulator
                llm_response_parts = []
                llm_tool_calls = []

            elif event.type == AgentEventType.LLM_DELTA:
                # Accumulate streaming response
                if event.content:
                    llm_response_parts.append(event.content)

            elif event.type == AgentEventType.LLM_COMPLETE:
                # LLM call completed
                pass

            elif event.type == AgentEventType.LLM_TOOL_CALLS:
                # LLM requested tool calls
                if event.metadata and "tool_calls" in event.metadata:
                    llm_tool_calls = event.metadata["tool_calls"]

            # === Tool Events ===
            elif event.type == AgentEventType.TOOL_RESULT:
                # Tool execution completed
                if event.tool_result:
                    tool_results.append({
                        "tool_call_id": event.tool_result.tool_call_id,
                        "tool_name": event.tool_result.tool_name,
                        "content": event.tool_result.content,
                        "is_error": event.tool_result.is_error,
                        "execution_time_ms": event.tool_result.execution_time_ms,
                        "metadata": event.tool_result.metadata
                    })

                    # Track tool call history
                    tool_call_history.append(event.tool_result.tool_name)
                    tool_call_history = tool_call_history[-20:]  # Keep last 20

                    # Track errors
                    if event.tool_result.is_error:
                        error_count += 1

            elif event.type == AgentEventType.TOOL_ERROR:
                # Tool execution failed
                error_count += 1
                if event.tool_result:
                    tool_results.append({
                        "tool_call_id": event.tool_result.tool_call_id,
                        "tool_name": event.tool_result.tool_name,
                        "content": event.tool_result.content,
                        "is_error": True,
                        "metadata": event.tool_result.metadata
                    })

            # === Agent Events ===
            elif event.type == AgentEventType.RECURSION:
                # Recursion is happening
                # Create frame if we don't have one yet
                if frame is None:
                    frame = ExecutionFrame(
                        frame_id=event.turn_id or "reconstructed",
                        depth=current_depth,
                        phase=ExecutionPhase.RECURSION,
                        messages=messages.copy(),
                        context_snapshot=context_snapshot.copy(),
                        context_metadata=context_metadata.copy(),
                        llm_response="".join(llm_response_parts) if llm_response_parts else None,
                        llm_tool_calls=llm_tool_calls.copy(),
                        tool_results=tool_results.copy(),
                        max_iterations=max_iterations,
                        tool_call_history=tool_call_history.copy(),
                        error_count=error_count,
                        last_outputs=last_outputs.copy()
                    )

            elif event.type == AgentEventType.AGENT_FINISH:
                # Agent finished - this is the final state
                pass

            elif event.type == AgentEventType.MAX_ITERATIONS_REACHED:
                # Hit iteration limit
                warnings.append("Max iterations reached during original execution")

            elif event.type == AgentEventType.RECURSION_TERMINATED:
                # Recursion was terminated
                if event.metadata:
                    reason = event.metadata.get("reason", "unknown")
                    warnings.append(f"Recursion terminated: {reason}")

        # === Build Final Frame ===

        # Construct final LLM response
        final_llm_response = "".join(llm_response_parts) if llm_response_parts else None

        # Track last output for loop detection
        if final_llm_response:
            last_outputs.append(final_llm_response[:200])
            last_outputs = last_outputs[-10:]

        # Build messages list (reconstruct conversation)
        # Note: This is simplified - in practice you'd reconstruct from events more carefully
        if not messages and final_llm_response:
            messages = [{"role": "assistant", "content": final_llm_response}]

        # Create or update frame
        if frame is None:
            # No ITERATION_START event found - create initial frame
            frame = ExecutionFrame(
                frame_id="reconstructed-root",
                depth=current_depth,
                phase=ExecutionPhase.INITIAL,
                messages=messages,
                max_iterations=max_iterations
            )

        # Apply accumulated state
        frame = ExecutionFrame(
            frame_id=frame.frame_id,
            parent_frame_id=frame.parent_frame_id,
            depth=current_depth,
            phase=ExecutionPhase.COMPLETED,  # Assume completed since we're reconstructing
            created_at=frame.created_at,
            messages=messages if messages else frame.messages,
            context_snapshot=context_snapshot,
            context_metadata=context_metadata,
            llm_response=final_llm_response,
            llm_tool_calls=llm_tool_calls,
            tool_results=tool_results,
            max_iterations=max_iterations,
            tool_call_history=tool_call_history,
            error_count=error_count,
            last_outputs=last_outputs,
            metadata=frame.metadata
        )

        # === Validation ===
        if self.validate:
            validation_warnings = self._validate_frame(frame, events)
            warnings.extend(validation_warnings)

        # === Build Metadata ===
        reconstruction_time = (time.time() - start_time) * 1000  # ms

        metadata = ReconstructionMetadata(
            total_events=len(events) if up_to_sequence is None else up_to_sequence,
            events_by_type=events_by_type,
            reconstruction_time_ms=reconstruction_time,
            warnings=warnings,
            final_phase=frame.phase.value
        )

        return frame, metadata

    def _validate_frame(self, frame: ExecutionFrame, events: List[AgentEvent]) -> List[str]:
        """
        Validate reconstructed frame for consistency.

        Args:
            frame: Reconstructed frame
            events: Original events

        Returns:
            List[str]: Validation warnings
        """
        warnings = []

        # Check tool calls match tool results
        tool_call_count = len(frame.llm_tool_calls)
        tool_result_count = len(frame.tool_results)

        if tool_call_count > 0 and tool_result_count == 0:
            warnings.append(
                f"Frame has {tool_call_count} tool calls but no results - "
                f"execution may have been interrupted"
            )

        # Check error count consistency
        error_events = sum(1 for e in events if e.type == AgentEventType.TOOL_ERROR)
        if frame.error_count != error_events:
            warnings.append(
                f"Frame error_count ({frame.error_count}) doesn't match "
                f"TOOL_ERROR events ({error_events})"
            )

        # Check depth consistency
        iteration_events = [e for e in events if e.type == AgentEventType.ITERATION_START]
        if iteration_events:
            max_depth = max((e.iteration or 0) for e in iteration_events)
            if frame.depth != max_depth:
                warnings.append(
                    f"Frame depth ({frame.depth}) doesn't match "
                    f"max iteration depth ({max_depth})"
                )

        return warnings

    async def reconstruct_at_iteration(
        self,
        events: List[AgentEvent],
        target_iteration: int
    ) -> tuple[ExecutionFrame, ReconstructionMetadata]:
        """
        Reconstruct state at a specific iteration (time-travel).

        Args:
            events: Complete event stream
            target_iteration: Target iteration to reconstruct

        Returns:
            Tuple of (ExecutionFrame, ReconstructionMetadata)

        Example:
            ```python
            # "Go back in time" to iteration 3
            frame, metadata = await reconstructor.reconstruct_at_iteration(
                events, target_iteration=3
            )

            # Now you can inspect what the state was at iteration 3!
            print(frame.summary())
            ```
        """
        # Find events up to target iteration
        filtered_events = []
        for event in events:
            if event.type == AgentEventType.ITERATION_START:
                if (event.iteration or 0) > target_iteration:
                    break
            filtered_events.append(event)

        return await self.reconstruct(filtered_events)

    async def reconstruct_with_new_strategy(
        self,
        events: List[AgentEvent],
        context_strategy: Optional[Any] = None,
        compression_strategy: Optional[Any] = None
    ) -> tuple[ExecutionFrame, ReconstructionMetadata]:
        """
        Reconstruct state while applying NEW strategies.

        This is the killer feature of event sourcing!
        You can replay old events with new logic.

        Args:
            events: Original event stream
            context_strategy: New context assembly strategy
            compression_strategy: New compression strategy

        Returns:
            Tuple of (ExecutionFrame, ReconstructionMetadata)

        Example:
            ```python
            # Original execution used compression v1
            # Now we have compression v2 (better algorithm)

            frame, metadata = await reconstructor.reconstruct_with_new_strategy(
                events,
                compression_strategy=CompressionManagerV2()
            )

            # The reconstructed state uses v2 compression!
            # This is impossible with LangGraph's static snapshots
            ```
        """
        # Temporarily inject new strategies
        old_assembler = self.context_assembler
        old_compression = self.compression_manager

        if context_strategy:
            self.context_assembler = context_strategy
        if compression_strategy:
            self.compression_manager = compression_strategy

        try:
            result = await self.reconstruct(events)
        finally:
            # Restore original strategies
            self.context_assembler = old_assembler
            self.compression_manager = old_compression

        return result
