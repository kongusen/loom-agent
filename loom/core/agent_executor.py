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
from typing import AsyncGenerator, Dict, List, Optional, Any
from uuid import uuid4

from loom.callbacks.base import BaseCallback
from loom.callbacks.metrics import MetricsCollector
from loom.core.context_assembly import ComponentPriority, ContextAssembler
from loom.core.events import AgentEvent, AgentEventType, ToolResult
from loom.core.execution_context import ExecutionContext
from loom.core.permissions import PermissionManager
from loom.core.recursion_control import RecursionMonitor, RecursionState
from loom.core.steering_control import SteeringControl
from loom.core.tool_orchestrator import ToolOrchestrator
from loom.core.tool_pipeline import ToolExecutionPipeline
from loom.core.turn_state import TurnState
from loom.core.types import Message, ToolCall
from loom.interfaces.compressor import BaseCompressor
from loom.interfaces.llm import BaseLLM
from loom.utils.stream_accumulator import safe_string_concat
from loom.interfaces.memory import BaseMemory
from loom.interfaces.tool import BaseTool
from loom.utils.token_counter import count_messages_tokens

# 🆕 New Architecture Imports
from loom.core.execution_frame import ExecutionFrame, ExecutionPhase
from loom.core.event_journal import EventJournal
from loom.core.context_debugger import ContextDebugger
from loom.core.state_reconstructor import StateReconstructor
from loom.core.lifecycle_hooks import (
    LifecycleHook,
    HookManager,
    InterruptException,
    SkipToolException
)

# RAG support
try:
    from loom.core.context_retriever import ContextRetriever
except ImportError:
    ContextRetriever = None  # type: ignore

# Unified coordination support
try:
    from loom.core.unified_coordination import UnifiedExecutionContext, IntelligentCoordinator
except ImportError:
    UnifiedExecutionContext = None  # type: ignore
    IntelligentCoordinator = None  # type: ignore


class TaskHandler:
    """
    任务处理器基类
    
    开发者可以继承此类来实现自定义的任务处理逻辑
    """
    
    def can_handle(self, task: str) -> bool:
        """
        判断是否能处理给定的任务
        
        Args:
            task: 任务描述
            
        Returns:
            bool: 是否能处理此任务
        """
        raise NotImplementedError
    
    def generate_guidance(
        self,
        original_task: str,
        result_analysis: Dict[str, Any],
        recursion_depth: int
    ) -> str:
        """
        生成递归指导消息
        
        Args:
            original_task: 原始任务
            result_analysis: 工具结果分析
            recursion_depth: 递归深度
            
        Returns:
            str: 生成的指导消息
        """
        raise NotImplementedError


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
        task_handlers: Optional[List[TaskHandler]] = None,
        unified_context: Optional["UnifiedExecutionContext"] = None,
        enable_unified_coordination: bool = True,
        # Phase 2: Recursion Control
        enable_recursion_control: bool = True,
        recursion_monitor: Optional[RecursionMonitor] = None,
        # 🆕 New Architecture Parameters
        hooks: Optional[List[LifecycleHook]] = None,
        event_journal: Optional[EventJournal] = None,
        context_debugger: Optional[ContextDebugger] = None,
        thread_id: Optional[str] = None,
        # 🎯 LLM Event Validation (开发/测试环境)
        debug: bool = False,
        validate_events: bool = False,
    ) -> None:
        # Validate LLM implements Protocol
        from loom.interfaces.llm import validate_llm
        validate_llm(llm, name="llm")

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
        self.task_handlers = task_handlers or []

        # Debug and validation
        self.debug = debug
        self.validate_events = validate_events or debug  # debug模式自动启用验证

        # Unified coordination
        self.unified_context = unified_context
        self.enable_unified_coordination = enable_unified_coordination

        # Phase 2: Recursion control
        self.enable_recursion_control = enable_recursion_control
        self.recursion_monitor = recursion_monitor or RecursionMonitor(
            max_iterations=max_iterations
        )

        # 🆕 New Architecture Components
        self.hooks = hooks or []
        self.hook_manager = HookManager(self.hooks) if self.hooks else None
        self.event_journal = event_journal
        self.context_debugger = context_debugger
        self.thread_id = thread_id or str(uuid4())

        # Initialize unified coordination if enabled
        if self.enable_unified_coordination and UnifiedExecutionContext and IntelligentCoordinator:
            self._setup_unified_coordination()

        # Tool execution (legacy pipeline for backward compatibility)
        self.tool_pipeline = ToolExecutionPipeline(
            self.tools,
            permission_manager=self.permission_manager,
            metrics=self.metrics,
        )

    def _setup_unified_coordination(self):
        """设置统一协调机制"""
        if not self.unified_context:
            # 创建默认的统一执行上下文
            from loom.core.unified_coordination import CoordinationConfig
            self.unified_context = UnifiedExecutionContext(
                execution_id=f"exec_{int(time.time())}",
                config=CoordinationConfig()  # 使用默认配置
            )
        
        # 集成四大核心能力
        self._integrate_core_capabilities()
        
        # 创建智能协调器
        self.coordinator = IntelligentCoordinator(self.unified_context)
        
        # 设置跨组件引用
        self._setup_cross_component_references()

    def _integrate_core_capabilities(self):
        """集成四大核心能力到统一上下文"""

        config = self.unified_context.config

        # 1. 集成 ContextAssembler
        if not self.unified_context.context_assembler:
            from loom.core.context_assembly import ContextAssembler, ComponentPriority
            import json

            self.unified_context.context_assembler = ContextAssembler(
                max_tokens=self.max_context_tokens,
                enable_caching=True,
                cache_size=config.context_cache_size
            )

            # 【关键修复】添加 system_instructions 作为基础组件
            if self.system_instructions:
                self.unified_context.context_assembler.add_component(
                    name="base_instructions",
                    content=self.system_instructions,
                    priority=ComponentPriority.CRITICAL,
                    truncatable=False,
                )

            # 添加工具定义
            if self.tools:
                tools_spec = self._serialize_tools()
                tools_prompt = f"Available tools:\n{json.dumps(tools_spec, indent=2)}"
                self.unified_context.context_assembler.add_component(
                    name="tool_definitions",
                    content=tools_prompt,
                    priority=ComponentPriority.MEDIUM,
                    truncatable=False,
                )

        # 2. 集成 TaskTool
        if "task" in self.tools and not self.unified_context.task_tool:
            task_tool = self.tools["task"]
            # 使用配置更新 TaskTool
            task_tool.pool_size = config.subagent_pool_size
            task_tool.enable_pooling = True
            self.unified_context.task_tool = task_tool

        # 3. 集成 EventProcessor
        if not self.unified_context.event_processor:
            from loom.core.events import EventFilter, EventProcessor, AgentEventType

            # 创建智能事件过滤器，使用配置值
            llm_filter = EventFilter(
                allowed_types=[
                    AgentEventType.LLM_DELTA,
                    AgentEventType.TOOL_RESULT,
                    AgentEventType.AGENT_FINISH
                ],
                enable_batching=True,
                batch_size=config.event_batch_size,
                batch_timeout=config.event_batch_timeout
            )

            self.unified_context.event_processor = EventProcessor(
                filters=[llm_filter],
                enable_stats=True
            )

        # 4. 集成 TaskHandlers
        if not self.unified_context.task_handlers:
            self.unified_context.task_handlers = self.task_handlers or []

    def _setup_cross_component_references(self):
        """
        设置跨组件引用（已简化）

        移除了魔法属性注入，改为通过协调器处理所有跨组件通信
        """
        pass  # 跨组件通信现在通过 IntelligentCoordinator 处理

        # Tool orchestration (Loom 2.0 - intelligent parallel/sequential execution)
        self.tool_orchestrator = ToolOrchestrator(
            tools=self.tools,
            permission_manager=self.permission_manager,
            max_parallel=5,
        )

    # ==========================================
    # CORE METHOD: tt (Tail-Recursive Control Loop)
    # ==========================================

    async def _record_event(self, event: AgentEvent):
        """Record event to journal if available."""
        if self.event_journal:
            await self.event_journal.append(event, thread_id=self.thread_id)

    async def tt(
        self,
        messages: List[Message],
        turn_state: TurnState,  # Note: Still using TurnState for backward compatibility initially
        context: ExecutionContext,
        frame: Optional[ExecutionFrame] = None,  # 🆕 New parameter for ExecutionFrame
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

        # 🆕 Create or update ExecutionFrame
        if frame is None:
            # Create initial frame from messages
            frame = ExecutionFrame(
                frame_id=turn_state.turn_id,
                parent_frame_id=turn_state.parent_turn_id,
                depth=turn_state.turn_counter,
                phase=ExecutionPhase.INITIAL,
                messages=[{"role": m.role, "content": m.content} for m in messages],
                max_iterations=turn_state.max_iterations,
                tool_call_history=turn_state.tool_call_history,
                error_count=turn_state.error_count,
                last_outputs=turn_state.last_outputs
            )

        # 🆕 Hook: before_iteration_start
        if self.hook_manager:
            frame = await self.hook_manager.before_iteration_start(frame)

        event = AgentEvent(
            type=AgentEventType.ITERATION_START,
            iteration=turn_state.turn_counter,
            turn_id=turn_state.turn_id,
            metadata={"parent_turn_id": turn_state.parent_turn_id},
        )
        await self._record_event(event)
        yield event

        # Phase 2: Advanced recursion control (optional)
        if self.enable_recursion_control:
            # Build recursion state from turn state
            recursion_state = RecursionState(
                iteration=turn_state.turn_counter,
                tool_call_history=turn_state.tool_call_history,
                error_count=turn_state.error_count,
                last_outputs=turn_state.last_outputs
            )

            # Check for termination conditions
            termination_reason = self.recursion_monitor.check_termination(
                recursion_state
            )

            if termination_reason:
                # Emit termination event
                yield AgentEvent(
                    type=AgentEventType.RECURSION_TERMINATED,
                    metadata={
                        "reason": termination_reason.value,
                        "iteration": turn_state.turn_counter,
                        "tool_call_history": turn_state.tool_call_history[-5:],
                        "error_count": turn_state.error_count
                    }
                )

                # Add termination message to prompt LLM to finish
                termination_msg = self.recursion_monitor.build_termination_message(
                    termination_reason
                )

                # Add termination guidance as system message
                messages = messages + [
                    Message(role="system", content=termination_msg)
                ]

                # Note: We continue execution but with termination guidance
                # The LLM will receive the termination message and should wrap up

            # Check for early warnings (not terminating yet, just warning)
            elif warning_msg := self.recursion_monitor.should_add_warning(
                recursion_state,
                warning_threshold=0.8
            ):
                # Add warning as system message
                messages = messages + [
                    Message(role="system", content=warning_msg)
                ]

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
            # 🆕 Hook: after_iteration_end
            if self.hook_manager:
                frame = await self.hook_manager.after_iteration_end(frame)
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
            # 🆕 Hook: after_iteration_end
            if self.hook_manager:
                frame = await self.hook_manager.after_iteration_end(frame)
            return

        # ==========================================
        # Phase 1: Context Assembly
        # ==========================================
        event = AgentEvent.phase_start("context_assembly")
        await self._record_event(event)
        yield event

        # 🆕 Hook: before_context_assembly
        if self.hook_manager:
            frame = await self.hook_manager.before_context_assembly(frame)

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

        # 使用统一协调的智能上下文组装
        if self.enable_unified_coordination and hasattr(self, 'coordinator'):
            # 使用智能协调器进行上下文组装
            execution_plan = self.coordinator.coordinate_tt_recursion(
                messages, turn_state, context
            )
            final_system_prompt = execution_plan.get("context", "")
            # 使用统一协调器的 assembler
            assembler = self.unified_context.context_assembler
        else:
            # 传统方式组装系统提示
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

        # 🆕 Update frame with context
        frame = frame.with_context(
            context_snapshot={"system_prompt": final_system_prompt},
            context_metadata=summary
        )

        # 🆕 Hook: after_context_assembly
        context_snapshot = frame.context_snapshot
        context_metadata = frame.context_metadata
        if self.hook_manager:
            result = await self.hook_manager.after_context_assembly(
                frame, context_snapshot, context_metadata
            )
            if result:
                context_snapshot, context_metadata = result
                frame = frame.with_context(context_snapshot, context_metadata)

        # 🆕 Record to ContextDebugger
        if self.context_debugger:
            self.context_debugger.record_from_frame(frame)

        event = AgentEvent.phase_end(
            "context_assembly",
            tokens_used=summary["total_tokens"],
            metadata={
                "components": len(summary["components"]),
                "utilization": summary["utilization"],
            },
        )
        await self._record_event(event)
        yield event

        # ==========================================
        # Phase 2: LLM Call
        # ==========================================
        event = AgentEvent(type=AgentEventType.LLM_START)
        await self._record_event(event)
        yield event

        # 🆕 Hook: before_llm_call
        api_messages = [self._message_to_api_format(m) for m in history]
        if self.hook_manager:
            result = await self.hook_manager.before_llm_call(frame, api_messages)
            if result:
                api_messages = result

        try:
            # ==========================================
            # Unified LLM Call using stream()
            # ==========================================
            # Use stream() for ALL LLM calls (with or without tools)
            # This provides consistent streaming behavior and supports JSON mode
            #
            # Protocol Design:
            # - llm.stream() yields LLMEvent dictionaries
            # - Supports text, tools, and JSON mode in one interface
            # - No branching logic needed

            tools_spec = self._serialize_tools() if self.tools else None
            content_parts = []
            tool_calls = []
            finish_reason = None

            async for llm_event in self.llm.stream(
                messages=api_messages,
                tools=tools_spec,
                response_format=None  # Future: support JSON mode parameter
            ):
                # 🎯 Validate event format in debug/test mode
                if self.validate_events:
                    from loom.interfaces.llm import validate_llm_event
                    validate_llm_event(llm_event, strict=self.debug)

                # Handle content deltas
                if llm_event.get("type") == "content_delta":
                    delta_content = llm_event["content"]
                    content_parts.append(delta_content)

                    # Emit AgentEvent for real-time streaming
                    agent_event = AgentEvent(
                        type=AgentEventType.LLM_DELTA,
                        content=delta_content
                    )
                    await self._record_event(agent_event)
                    yield agent_event

                # Handle tool calls (emitted at end of stream)
                elif llm_event.get("type") == "tool_calls":
                    tool_calls = llm_event["tool_calls"]

                # Handle finish event
                elif llm_event.get("type") == "finish":
                    finish_reason = llm_event.get("finish_reason", "stop")
                    # Track finish_reason for metrics/debugging

            # Reconstruct full content from accumulated parts
            content = safe_string_concat(content_parts)

            # Emit completion event
            event = AgentEvent(type=AgentEventType.LLM_COMPLETE)
            await self._record_event(event)
            yield event

            # 🆕 Update frame with LLM response
            frame = frame.with_llm_response(content, tool_calls)

            # 🆕 Hook: after_llm_response
            if self.hook_manager:
                result = await self.hook_manager.after_llm_response(frame, content, tool_calls)
                if result:
                    content, tool_calls = result
                    frame = frame.with_llm_response(content, tool_calls)

        except Exception as e:
            self.metrics.metrics.total_errors += 1
            yield AgentEvent.error(e, llm_failed=True)
            await self._emit("error", {"stage": "llm_call", "message": str(e)})
            # 🆕 Hook: after_iteration_end
            if self.hook_manager:
                frame = await self.hook_manager.after_iteration_end(frame)
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

            # 🆕 Hook: after_iteration_end
            if self.hook_manager:
                frame = await self.hook_manager.after_iteration_end(frame)
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

        # Save assistant message with tool_calls to memory first
        # This is critical: assistant message must come before tool messages
        assistant_msg = Message(
            role="assistant",
            content=content or "",
            metadata={"tool_calls": tool_calls}  # Store tool_calls in metadata for API conversion
        )
        if self.memory:
            await self.memory.add_message(assistant_msg)

        try:
            # 🆕 Execute with hook support
            if self.hook_manager:
                # Execute tools one by one to support hooks
                for tc_model in tc_models:
                    # 🆕 Hook: before_tool_execution (HITL critical point!)
                    tool_call_dict = {
                        "id": tc_model.id,
                        "name": tc_model.name,
                        "arguments": tc_model.arguments
                    }

                    try:
                        result = await self.hook_manager.before_tool_execution(
                            frame, tool_call_dict
                        )
                        if result:
                            # Hook modified the tool call
                            tc_model = self._to_tool_call(result)

                    except InterruptException as interrupt:
                        # 🔥 HITL: Execution interrupted!
                        event = AgentEvent(
                            type=AgentEventType.EXECUTION_CANCELLED,
                            metadata={
                                "reason": interrupt.reason,
                                "requires_user_input": interrupt.requires_user_input,
                                "frame_id": frame.frame_id,
                                "tool_call": tool_call_dict,
                                "interrupt": True
                            }
                        )
                        await self._record_event(event)
                        yield event

                        # Save checkpoint for resumption
                        checkpoint_event = AgentEvent(
                            type=AgentEventType.PHASE_START,
                            phase="checkpoint",
                            metadata={
                                "checkpoint": frame.to_checkpoint(),
                                "pending_tool_calls": [
                                    {"id": tc.id, "name": tc.name, "arguments": tc.arguments}
                                    for tc in tc_models
                                ]
                            }
                        )
                        await self._record_event(checkpoint_event)

                        # 🆕 Hook: after_iteration_end
                        if self.hook_manager:
                            frame = await self.hook_manager.after_iteration_end(frame)

                        return  # Exit execution, waiting for resumption

                    except SkipToolException:
                        # Skip this tool
                        continue

                    # Execute single tool
                    async for event in self.tool_orchestrator.execute_batch([tc_model]):
                        await self._record_event(event)
                        yield event

                        if event.type == AgentEventType.TOOL_RESULT:
                            tool_results.append(event.tool_result)

                            # 🆕 Hook: after_tool_execution
                            tool_result_dict = {
                                "tool_call_id": event.tool_result.tool_call_id,
                                "tool_name": event.tool_result.tool_name,
                                "content": event.tool_result.content,
                                "is_error": event.tool_result.is_error,
                                "execution_time_ms": event.tool_result.execution_time_ms,
                                "metadata": event.tool_result.metadata
                            }

                            result = await self.hook_manager.after_tool_execution(
                                frame, tool_result_dict
                            )
                            if result:
                                # Hook modified the result - update the tool_result
                                event.tool_result.content = result.get("content", event.tool_result.content)

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

            else:
                # No hooks - use batch execution (original behavior)
                async for event in self.tool_orchestrator.execute_batch(tc_models):
                    await self._record_event(event)
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
            # 🆕 Hook: after_iteration_end
            if self.hook_manager:
                frame = await self.hook_manager.after_iteration_end(frame)
            return

        yield AgentEvent(
            type=AgentEventType.TOOL_CALLS_COMPLETE,
            metadata={"results_count": len(tool_results)},
        )

        self.metrics.metrics.total_iterations += 1

        # ==========================================
        # Phase 5: Recursive Call (Tail Recursion)
        # ==========================================

        # Phase 2: Track tool calls and errors for recursion control
        tool_names_called = [tc.name for tc in tc_models]
        had_tool_errors = any(r.is_error for r in tool_results)

        # Extract output for loop detection (use first tool result or content)
        output_sample = None
        if tool_results:
            output_sample = tool_results[0].content[:200]  # First 200 chars
        elif content:
            output_sample = content[:200]

        # 🆕 Update frame with tool results
        frame = frame.with_tool_results(
            tool_results=[{
                "tool_call_id": r.tool_call_id,
                "tool_name": r.tool_name,
                "content": r.content,
                "is_error": r.is_error,
                "execution_time_ms": r.execution_time_ms,
                "metadata": r.metadata or {}
            } for r in tool_results],
            had_error=had_tool_errors
        )

        # Prepare next turn state with recursion tracking
        next_state = turn_state.next_turn(
            compacted=compacted_this_turn,
            tool_calls=tool_names_called,
            had_error=had_tool_errors,
            output=output_sample
        )

        # Phase 3: Prepare next turn messages with intelligent context guidance
        # This now includes tool results, compression, and recursion hints
        # Pass assistant message and tool_calls for proper message formatting
        next_messages = await self._prepare_recursive_messages(
            messages, tool_results, tool_calls, content, turn_state, context
        )

        # Check if compression was applied and emit event
        if "last_compression" in context.metadata:
            comp_info = context.metadata.pop("last_compression")
            yield AgentEvent(
                type=AgentEventType.COMPRESSION_APPLIED,
                metadata=comp_info
            )

        # 🆕 Create next frame for recursion
        next_frame = frame.next_frame(new_messages=next_messages)

        # 🆕 Hook: before_recursion
        if self.hook_manager:
            result = await self.hook_manager.before_recursion(frame, next_frame)
            if result:
                next_frame = result

        # Emit recursion event
        yield AgentEvent(
            type=AgentEventType.RECURSION,
            metadata={
                "from_turn": turn_state.turn_id,
                "to_turn": next_state.turn_id,
                "depth": next_state.turn_counter,
                "tools_called": tool_names_called,
                "message_count": len(next_messages),
                "from_frame_id": frame.frame_id,
                "to_frame_id": next_frame.frame_id,
            },
        )

        # 🔥 Tail-recursive call with frame
        async for event in self.tt(next_messages, next_state, context, frame=next_frame):
            yield event

    # ==========================================
    # Intelligent Recursion Methods
    # ==========================================

    async def _prepare_recursive_messages(
        self,
        messages: List[Message],
        tool_results: List[ToolResult],
        tool_calls: List[Dict],
        assistant_content: str,
        turn_state: TurnState,
        context: ExecutionContext,
    ) -> List[Message]:
        """
        Phase 3: 智能准备递归调用的消息

        确保工具结果正确传递到下一轮，并进行必要的上下文优化
        关键：必须符合 OpenAI API 的消息格式要求：
        - assistant 消息（包含 tool_calls）必须紧跟在之前的消息之后
        - tool 消息必须紧跟在对应的 assistant 消息之后
        - 不能在 tool 消息前插入新的 user 消息

        Args:
            messages: 当前轮次的消息
            tool_results: 工具执行结果
            tool_calls: 工具调用列表（用于创建 assistant 消息）
            assistant_content: Assistant 消息的内容
            turn_state: 当前轮次状态
            context: 执行上下文

        Returns:
            准备好的下一轮消息列表
        """
        # 1. 首先添加 assistant 消息（包含 tool_calls）
        # 这是关键：assistant 消息必须在 tool 消息之前
        assistant_msg = Message(
            role="assistant",
            content=assistant_content or "",
            metadata={"tool_calls": tool_calls}  # Store tool_calls in metadata
        )
        next_messages = [assistant_msg]

        # 2. 添加工具结果消息（必须紧跟在 assistant 消息之后）
        for result in tool_results:
            next_messages.append(Message(
                role="tool",
                content=result.content,
                tool_call_id=result.tool_call_id,
                metadata=result.metadata or {}
            ))
        
        # 3. 如果需要指导信息，在 tool 消息之后添加（作为系统消息）
        # 这样可以避免违反 API 的消息格式要求
        result_analysis = self._analyze_tool_results(tool_results)
        original_task = self._extract_original_task(messages)
        
        guidance_message = self._generate_recursion_guidance(
            original_task, result_analysis, turn_state.turn_counter
        )
        
        # 只有在有指导信息时才添加
        if guidance_message and guidance_message.strip():
            # 将指导信息作为系统消息添加到 tool 消息之后
            next_messages.append(Message(role="system", content=guidance_message))

        # 5. Phase 3: 检查上下文长度
        estimated_tokens = self._estimate_tokens(next_messages)
        compression_applied = False

        if estimated_tokens > self.max_context_tokens:
            # 触发压缩（如果有 compressor）
            if self.compressor:
                tokens_before = estimated_tokens
                next_messages = await self._compress_messages(next_messages)
                tokens_after = self._estimate_tokens(next_messages)
                compression_applied = True

                # Store compression info for later emission
                context.metadata["last_compression"] = {
                    "tokens_before": tokens_before,
                    "tokens_after": tokens_after,
                    "trigger": "recursive_message_preparation"
                }

        # 6. Phase 3: 添加递归深度提示（深度递归时）
        if turn_state.turn_counter > 3:
            hint_content = self._build_recursion_hint(
                turn_state.turn_counter,
                turn_state.max_iterations
            )

            hint = Message(
                role="system",
                content=hint_content
            )
            next_messages.append(hint)

        return next_messages

    def _estimate_tokens(self, messages: List[Message]) -> int:
        """
        估算消息列表的 token 数量

        使用简单的启发式方法：字符数 / 4
        生产环境中应使用具体模型的 tokenizer
        """
        return count_messages_tokens(messages)

    async def _compress_messages(
        self,
        messages: List[Message]
    ) -> List[Message]:
        """
        压缩消息列表（如果有 compressor）

        这个方法会调用配置的 compressor 来减少上下文长度
        """
        if not self.compressor:
            return messages

        try:
            compressed, metadata = await self.compressor.compress(messages)

            # Update compression metrics
            self.metrics.metrics.compressions = (
                getattr(self.metrics.metrics, "compressions", 0) + 1
            )

            return compressed
        except Exception as e:
            # If compression fails, return original messages
            self.metrics.metrics.total_errors += 1
            await self._emit(
                "error",
                {"stage": "message_compression", "message": str(e)}
            )
            return messages

    def _build_recursion_hint(self, current_depth: int, max_depth: int) -> str:
        """
        构建递归深度提示消息

        在深度递归时提醒 LLM 注意进度和避免重复
        """
        remaining = max_depth - current_depth
        progress = (current_depth / max_depth) * 100

        hint = f"""🔄 Recursion Status:
- Depth: {current_depth}/{max_depth} ({progress:.0f}% of maximum)
- Remaining iterations: {remaining}

Please review the tool results above and make meaningful progress towards completing the task.
Avoid calling the same tool repeatedly with the same arguments unless necessary.
If you have enough information, please provide your final answer."""

        return hint

    def _analyze_tool_results(self, tool_results: List[ToolResult]) -> Dict[str, Any]:
        """分析工具结果类型和质量"""
        analysis = {
            "has_data": False,
            "has_errors": False,
            "suggests_completion": False,
            "result_types": [],
            "completeness_score": 0.0
        }
        
        for result in tool_results:
            content = result.content.lower()
            
            # 检查数据类型
            if any(keyword in content for keyword in ["data", "found", "retrieved", "table", "schema", "获取到", "表结构", "结构"]):
                analysis["has_data"] = True
                analysis["result_types"].append("data")
                analysis["completeness_score"] += 0.3
            
            # 检查错误
            if any(keyword in content for keyword in ["error", "failed", "exception", "not found"]):
                analysis["has_errors"] = True
                analysis["result_types"].append("error")
            
            # 检查完成建议
            if any(keyword in content for keyword in ["complete", "finished", "done", "ready"]):
                analysis["suggests_completion"] = True
                analysis["result_types"].append("completion")
                analysis["completeness_score"] += 0.5
            
            # 检查分析结果
            if any(keyword in content for keyword in ["analysis", "summary", "conclusion", "insights"]):
                analysis["result_types"].append("analysis")
                analysis["completeness_score"] += 0.4
        
        analysis["completeness_score"] = min(analysis["completeness_score"], 1.0)
        return analysis

    def _extract_original_task(self, messages: List[Message]) -> str:
        """从消息历史中提取原始任务"""
        # 查找第一个用户消息作为原始任务
        for message in messages:
            if message.role == "user" and message.content:
                # 过滤掉系统生成的递归消息
                if not any(keyword in message.content.lower() for keyword in [
                    "工具调用已完成", "请基于工具返回的结果", "不要继续调用工具"
                ]):
                    return message.content
        return "处理用户请求"

    def _generate_recursion_guidance(
        self,
        original_task: str,
        result_analysis: Dict[str, Any],
        recursion_depth: int
    ) -> str:
        """生成递归指导消息"""
        
        # 使用可扩展的任务处理器
        if hasattr(self, 'task_handlers') and self.task_handlers:
            for handler in self.task_handlers:
                if handler.can_handle(original_task):
                    return handler.generate_guidance(original_task, result_analysis, recursion_depth)
        
        # 默认处理
        return self._generate_default_guidance(original_task, result_analysis, recursion_depth)


    def _generate_default_guidance(
        self,
        original_task: str,
        result_analysis: Dict[str, Any],
        recursion_depth: int
    ) -> str:
        """生成默认的递归指导"""
        
        if result_analysis["suggests_completion"] or recursion_depth >= 6:
            return f"""工具调用已完成。请基于返回的结果完成任务：{original_task}

请提供完整、准确的最终答案。"""
        
        elif result_analysis["has_errors"]:
            return f"""工具执行遇到问题。请重新尝试完成任务：{original_task}

建议：
- 检查工具参数是否正确
- 尝试使用不同的工具或方法
- 如果问题持续，请说明具体错误"""
        
        else:
            return f"""继续处理任务：{original_task}

当前进度：{result_analysis['completeness_score']:.0%}
建议：使用更多工具收集信息或分析已获得的结果"""

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

    def _message_to_api_format(self, message: Message) -> Dict:
        """
        Convert Message object to OpenAI API format.

        Handles special case: assistant messages with tool_calls in metadata
        must be converted to API format with tool_calls field.

        According to OpenAI API spec:
        - When assistant message has tool_calls, content should be null
        - tool_calls must be at top level, not in metadata

        Args:
            message: Message object to convert

        Returns:
            Dict in OpenAI API message format
        """
        api_msg = {
            "role": message.role,
            "content": message.content or None,
        }

        # Handle tool messages
        if message.role == "tool" and message.tool_call_id:
            api_msg["tool_call_id"] = message.tool_call_id

        # Handle assistant messages with tool_calls
        # Check if metadata contains tool_calls (metadata is always a dict per Message dataclass)
        if message.role == "assistant" and "tool_calls" in message.metadata:
            tool_calls = message.metadata["tool_calls"]
            if isinstance(tool_calls, list) and tool_calls:  # Validate it's a non-empty list
                # According to OpenAI API spec, when tool_calls exist, content should be null
                api_msg["content"] = None

                # Convert tool_calls to OpenAI API format
                api_tool_calls = []
                for tc in tool_calls:
                    if not isinstance(tc, dict):
                        continue  # Skip invalid tool call entries

                    # Handle arguments: validate and serialize properly
                    arguments = tc.get("arguments", {})
                    if isinstance(arguments, str):
                        # Validate it's valid JSON string, use as-is if valid
                        try:
                            json.loads(arguments)  # Validate JSON
                            arguments_str = arguments
                        except (json.JSONDecodeError, ValueError):
                            # Invalid JSON, treat as empty dict
                            arguments_str = "{}"
                    elif isinstance(arguments, dict):
                        # Serialize dict to JSON string
                        try:
                            arguments_str = json.dumps(arguments)
                        except (TypeError, ValueError):
                            # Fallback to empty dict if serialization fails
                            arguments_str = "{}"
                    else:
                        # Fallback: convert to empty dict
                        arguments_str = "{}"

                    # Validate required fields exist
                    tool_id = tc.get("id", "")
                    tool_name = tc.get("name", "")

                    if tool_id and tool_name:  # Only add valid tool calls
                        api_tool_calls.append({
                            "id": tool_id,
                            "type": "function",
                            "function": {
                                "name": tool_name,
                                "arguments": arguments_str
                            }
                        })

                if api_tool_calls:  # Only add if we have valid tool calls
                    api_msg["tool_calls"] = api_tool_calls

        return api_msg

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

    async def resume(
        self,
        thread_id: str,
        journal: Optional[EventJournal] = None,
        cancel_token: Optional[asyncio.Event] = None,
        correlation_id: Optional[str] = None,
    ) -> AsyncGenerator[AgentEvent, None]:
        """
        Resume execution from a crash or interruption.

        This method reconstructs the execution state from the event journal
        and continues from the last checkpoint.

        Args:
            thread_id: Thread ID to resume
            journal: Optional EventJournal instance (uses self.event_journal if not provided)
            cancel_token: Optional cancellation event
            correlation_id: Optional correlation ID for tracing

        Yields:
            AgentEvent: Events from resumed execution

        Example:
            ```python
            # After a crash, resume execution
            executor = AgentExecutor(
                llm=llm,
                tools=tools,
                event_journal=journal
            )

            async for event in executor.resume(thread_id="user-123"):
                if event.type == AgentEventType.AGENT_FINISH:
                    print(f"Resumed and completed: {event.content}")
            ```
        """
        # Use provided journal or fall back to instance journal
        journal_to_use = journal or self.event_journal

        if not journal_to_use:
            raise ValueError(
                "No EventJournal available. Please provide a journal parameter "
                "or initialize AgentExecutor with event_journal."
            )

        # 1. Replay events from journal
        yield AgentEvent(
            type=AgentEventType.PHASE_START,
            phase="resume",
            metadata={"thread_id": thread_id, "status": "replaying_events"}
        )

        events = await journal_to_use.replay(thread_id=thread_id)

        if not events:
            raise ValueError(f"No events found for thread_id: {thread_id}")

        # 2. Reconstruct state from events
        reconstructor = StateReconstructor()
        frame, metadata = await reconstructor.reconstruct(events)

        yield AgentEvent(
            type=AgentEventType.PHASE_END,
            phase="resume",
            metadata={
                "thread_id": thread_id,
                "status": "state_reconstructed",
                "total_events": metadata.total_events,
                "final_phase": metadata.final_phase.value if hasattr(metadata.final_phase, 'value') else str(metadata.final_phase) if metadata.final_phase else None,
                "warnings": metadata.warnings,
                "reconstruction_time_ms": metadata.reconstruction_time_ms,
            }
        )

        # 3. Rebuild TurnState from ExecutionFrame (backward compatibility)
        turn_state = TurnState(
            turn_counter=frame.depth,
            turn_id=frame.frame_id,
            max_iterations=frame.max_iterations,
            parent_turn_id=frame.parent_frame_id,
            tool_call_history=frame.tool_call_history,
            error_count=frame.error_count,
            last_outputs=frame.last_outputs
        )

        # 4. Rebuild messages from frame
        messages = [Message(role=m["role"], content=m["content"]) for m in frame.messages]

        # 5. Create execution context
        context = ExecutionContext.create(
            correlation_id=correlation_id or thread_id,
            cancel_token=cancel_token,
        )

        # 6. Continue execution from checkpoint
        yield AgentEvent(
            type=AgentEventType.PHASE_START,
            phase="resume_execution",
            metadata={
                "thread_id": thread_id,
                "from_depth": frame.depth,
                "from_phase": frame.phase.value,
            }
        )

        # Resume from the reconstructed frame
        async for event in self.tt(messages, turn_state, context, frame=frame):
            yield event
