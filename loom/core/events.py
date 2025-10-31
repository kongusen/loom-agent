"""
Agent Event System for Loom 2.0

This module defines the unified event model for streaming agent execution.
Inspired by Claude Code's event-driven architecture.

新特性 (Loom 0.0.3):
- 事件过滤和批量处理
- 智能事件聚合
- 性能优化的事件流
- 事件优先级管理

Example:
    ```python
    agent = Agent(llm=llm, tools=tools)

    async for event in agent.execute("Search for TODO comments"):
        if event.type == AgentEventType.LLM_DELTA:
            print(event.content, end="", flush=True)
        elif event.type == AgentEventType.TOOL_PROGRESS:
            print(f"\\nTool: {event.metadata['tool_name']}")
        elif event.type == AgentEventType.AGENT_FINISH:
            print(f"\\n✓ {event.content}")
    ```
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any, List
import time
import uuid


class AgentEventType(Enum):
    """
    Agent event types for different execution phases.

    Event Categories:
    - Phase Events: Lifecycle events for execution phases
    - Context Events: Context assembly and management
    - RAG Events: Retrieval-augmented generation events
    - LLM Events: Language model interaction events
    - Tool Events: Tool execution and progress
    - Agent Events: High-level agent state changes
    - Error Events: Error handling and recovery
    """

    # ===== Phase Events =====
    PHASE_START = "phase_start"
    """A new execution phase has started"""

    PHASE_END = "phase_end"
    """An execution phase has completed"""

    # ===== Context Events =====
    CONTEXT_ASSEMBLY_START = "context_assembly_start"
    """Starting to assemble system context"""

    CONTEXT_ASSEMBLY_COMPLETE = "context_assembly_complete"
    """System context assembly completed"""

    COMPRESSION_APPLIED = "compression_applied"
    """Conversation history was compressed"""

    # ===== RAG Events =====
    RETRIEVAL_START = "retrieval_start"
    """Starting document retrieval"""

    RETRIEVAL_PROGRESS = "retrieval_progress"
    """Progress update during retrieval (documents found)"""

    RETRIEVAL_COMPLETE = "retrieval_complete"
    """Document retrieval completed"""

    # ===== LLM Events =====
    LLM_START = "llm_start"
    """LLM call initiated"""

    LLM_DELTA = "llm_delta"
    """Streaming text chunk from LLM"""

    LLM_COMPLETE = "llm_complete"
    """LLM call completed"""

    LLM_TOOL_CALLS = "llm_tool_calls"
    """LLM requested tool calls"""

    # ===== Tool Events =====
    TOOL_CALLS_START = "tool_calls_start"
    """Starting to execute tool calls"""

    TOOL_EXECUTION_START = "tool_execution_start"
    """Individual tool execution started"""

    TOOL_PROGRESS = "tool_progress"
    """Progress update from tool execution"""

    TOOL_RESULT = "tool_result"
    """Tool execution completed with result"""

    TOOL_ERROR = "tool_error"
    """Tool execution failed"""

    TOOL_CALLS_COMPLETE = "tool_calls_complete"
    """All tool calls completed (batch execution finished)"""

    # ===== Agent Events =====
    ITERATION_START = "iteration_start"
    """New agent iteration started (for recursive loops)"""

    ITERATION_END = "iteration_end"
    """Agent iteration completed"""

    RECURSION = "recursion"
    """Recursive call initiated (tt mode)"""

    RECURSION_TERMINATED = "recursion_terminated"
    """Recursion terminated due to loop detection or limits (Phase 2 optimization)"""

    AGENT_FINISH = "agent_finish"
    """Agent execution finished successfully"""

    MAX_ITERATIONS_REACHED = "max_iterations_reached"
    """Maximum iteration limit reached"""

    EXECUTION_CANCELLED = "execution_cancelled"
    """Execution was cancelled via cancel_token"""

    # ===== Error Events =====
    ERROR = "error"
    """Error occurred during execution"""

    RECOVERY_ATTEMPT = "recovery_attempt"
    """Attempting to recover from error"""

    RECOVERY_SUCCESS = "recovery_success"
    """Error recovery succeeded"""

    RECOVERY_FAILED = "recovery_failed"
    """Error recovery failed"""


@dataclass
class ToolCall:
    """Represents a tool invocation request from the LLM"""

    id: str
    """Unique identifier for this tool call"""

    name: str
    """Name of the tool to execute"""

    arguments: Dict[str, Any]
    """Arguments to pass to the tool"""

    def __post_init__(self):
        if not self.id:
            self.id = f"call_{uuid.uuid4().hex[:8]}"


@dataclass
class ToolResult:
    """Represents the result of a tool execution"""

    tool_call_id: str
    """ID of the tool call this result corresponds to"""

    tool_name: str
    """Name of the tool that was executed"""

    content: str
    """Result content (or error message)"""

    is_error: bool = False
    """Whether this result represents an error"""

    execution_time_ms: Optional[float] = None
    """Time taken to execute the tool in milliseconds"""

    metadata: Dict[str, Any] = field(default_factory=dict)
    """Additional metadata about the execution"""


@dataclass
class AgentEvent:
    """
    Unified event model for agent execution streaming.

    All components in Loom 2.0 produce AgentEvent instances to communicate
    their state and progress. This enables:
    - Real-time progress updates to users
    - Fine-grained control over execution flow
    - Debugging and observability
    - Flexible consumption patterns

    Attributes:
        type: The type of event (see AgentEventType)
        timestamp: Unix timestamp when event was created
        phase: Optional execution phase name (e.g., "context", "retrieval", "llm")
        content: Optional text content (for LLM deltas, final responses)
        tool_call: Optional tool call request
        tool_result: Optional tool execution result
        error: Optional exception that occurred
        metadata: Additional event-specific data
        iteration: Current iteration number (for recursive loops)
        turn_id: Unique ID for this conversation turn
    """

    type: AgentEventType
    """The type of this event"""

    timestamp: float = field(default_factory=time.time)
    """Unix timestamp when this event was created"""

    # ===== Optional Fields (based on event type) =====

    phase: Optional[str] = None
    """Execution phase name (e.g., 'context_assembly', 'tool_execution')"""

    content: Optional[str] = None
    """Text content (for LLM_DELTA, AGENT_FINISH, etc.)"""

    tool_call: Optional[ToolCall] = None
    """Tool call request (for LLM_TOOL_CALLS, TOOL_EXECUTION_START)"""

    tool_result: Optional[ToolResult] = None
    """Tool execution result (for TOOL_RESULT, TOOL_ERROR)"""

    error: Optional[Exception] = None
    """Exception that occurred (for ERROR events)"""

    metadata: Dict[str, Any] = field(default_factory=dict)
    """Additional event-specific data"""

    # ===== Tracking Fields =====

    iteration: Optional[int] = None
    """Current iteration number (for recursive agent loops)"""

    turn_id: Optional[str] = None
    """Unique identifier for this conversation turn"""

    def __post_init__(self):
        """Generate turn_id if not provided"""
        if self.turn_id is None:
            self.turn_id = f"turn_{uuid.uuid4().hex[:12]}"

    # ===== Convenience Constructors =====

    @classmethod
    def phase_start(cls, phase: str, **metadata) -> "AgentEvent":
        """Create a PHASE_START event"""
        return cls(
            type=AgentEventType.PHASE_START,
            phase=phase,
            metadata=metadata
        )

    @classmethod
    def phase_end(cls, phase: str, **metadata) -> "AgentEvent":
        """Create a PHASE_END event"""
        return cls(
            type=AgentEventType.PHASE_END,
            phase=phase,
            metadata=metadata
        )

    @classmethod
    def llm_delta(cls, content: str, **metadata) -> "AgentEvent":
        """Create an LLM_DELTA event for streaming text"""
        return cls(
            type=AgentEventType.LLM_DELTA,
            content=content,
            metadata=metadata
        )

    @classmethod
    def tool_progress(
        cls,
        tool_name: str,
        status: str,
        **metadata
    ) -> "AgentEvent":
        """Create a TOOL_PROGRESS event"""
        return cls(
            type=AgentEventType.TOOL_PROGRESS,
            metadata={"tool_name": tool_name, "status": status, **metadata}
        )

    @classmethod
    def tool_result(
        cls,
        tool_result: ToolResult,
        **metadata
    ) -> "AgentEvent":
        """Create a TOOL_RESULT event"""
        return cls(
            type=AgentEventType.TOOL_RESULT,
            tool_result=tool_result,
            metadata=metadata
        )

    @classmethod
    def agent_finish(cls, content: str, **metadata) -> "AgentEvent":
        """Create an AGENT_FINISH event"""
        return cls(
            type=AgentEventType.AGENT_FINISH,
            content=content,
            metadata=metadata
        )

    @classmethod
    def error(cls, error: Exception, **metadata) -> "AgentEvent":
        """Create an ERROR event"""
        return cls(
            type=AgentEventType.ERROR,
            error=error,
            metadata=metadata
        )

    # ===== Utility Methods =====

    def is_terminal(self) -> bool:
        """Check if this event signals execution completion"""
        return self.type in {
            AgentEventType.AGENT_FINISH,
            AgentEventType.MAX_ITERATIONS_REACHED,
            AgentEventType.ERROR
        }

    def is_llm_content(self) -> bool:
        """Check if this event contains LLM-generated content"""
        return self.type in {
            AgentEventType.LLM_DELTA,
            AgentEventType.LLM_COMPLETE,
            AgentEventType.AGENT_FINISH
        }

    def is_tool_event(self) -> bool:
        """Check if this is a tool-related event"""
        return self.type.value.startswith("tool_")

    def __repr__(self) -> str:
        """Human-readable representation"""
        parts = [f"AgentEvent({self.type.value}"]

        if self.phase:
            parts.append(f"phase={self.phase}")

        if self.content:
            preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
            parts.append(f"content='{preview}'")

        if self.tool_call:
            parts.append(f"tool={self.tool_call.name}")

        # Access instance variable directly to avoid class method with same name
        tool_result_instance = self.__dict__.get('tool_result')
        if tool_result_instance and isinstance(tool_result_instance, ToolResult):
            parts.append(f"tool={tool_result_instance.tool_name}")

        if self.error:
            parts.append(f"error={type(self.error).__name__}")

        if self.iteration is not None:
            parts.append(f"iter={self.iteration}")

        return ", ".join(parts) + ")"


# ===== Event Consumer Helpers =====

class EventCollector:
    """
    Helper class to collect and filter events during agent execution.

    Example:
        ```python
        collector = EventCollector()

        async for event in agent.execute(prompt):
            collector.add(event)

        # Get all LLM content
        llm_text = collector.get_llm_content()

        # Get all tool results
        tool_results = collector.get_tool_results()
        ```
    """

    def __init__(self):
        self.events: List[AgentEvent] = []

    def add(self, event: AgentEvent):
        """Add an event to the collection"""
        self.events.append(event)

    def filter(self, event_type: AgentEventType) -> List[AgentEvent]:
        """Get all events of a specific type"""
        return [e for e in self.events if e.type == event_type]

    def get_llm_content(self) -> str:
        """Reconstruct full LLM output from LLM_DELTA events"""
        deltas = self.filter(AgentEventType.LLM_DELTA)
        return "".join(e.content or "" for e in deltas)

    def get_tool_results(self) -> List[ToolResult]:
        """Get all tool results"""
        result_events = self.filter(AgentEventType.TOOL_RESULT)
        return [e.tool_result for e in result_events if e.tool_result]

    def get_errors(self) -> List[Exception]:
        """Get all errors that occurred"""
        error_events = self.filter(AgentEventType.ERROR)
        return [e.error for e in error_events if e.error]

    def get_final_response(self) -> Optional[str]:
        """Get the final agent response"""
        finish_events = self.filter(AgentEventType.AGENT_FINISH)
        if finish_events:
            return finish_events[-1].content
        return None


class EventFilter:
    """
    事件过滤器 - 提供高级事件过滤和批量处理能力
    
    新特性 (Loom 0.0.3):
    - 智能事件过滤
    - 批量事件处理
    - 事件聚合和合并
    - 性能优化的事件流
    """
    
    def __init__(self, 
                 allowed_types: Optional[List[AgentEventType]] = None,
                 blocked_types: Optional[List[AgentEventType]] = None,
                 enable_batching: bool = True,
                 batch_size: int = 10,
                 batch_timeout: float = 0.1):
        """
        初始化事件过滤器
        
        Args:
            allowed_types: 允许的事件类型列表（None = 全部允许）
            blocked_types: 阻止的事件类型列表
            enable_batching: 启用批量处理
            batch_size: 批量大小
            batch_timeout: 批量超时时间（秒）
        """
        self.allowed_types = allowed_types
        self.blocked_types = blocked_types or []
        self.enable_batching = enable_batching
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        
        # 批量处理状态
        self._batch_buffer: List[AgentEvent] = []
        self._last_batch_time = time.time()
    
    def should_include(self, event: AgentEvent) -> bool:
        """判断事件是否应该被包含"""
        # 检查允许的类型
        if self.allowed_types and event.type not in self.allowed_types:
            return False
        
        # 检查阻止的类型
        if event.type in self.blocked_types:
            return False
        
        return True
    
    def process_event(self, event: AgentEvent) -> List[AgentEvent]:
        """
        处理单个事件，可能返回批量事件
        
        Returns:
            处理后的事件列表
        """
        if not self.should_include(event):
            return []
        
        if not self.enable_batching:
            return [event]
        
        # 添加到批量缓冲区
        self._batch_buffer.append(event)
        
        # 检查是否需要输出批量事件
        should_flush = (
            len(self._batch_buffer) >= self.batch_size or
            (time.time() - self._last_batch_time) >= self.batch_timeout
        )
        
        if should_flush:
            return self._flush_batch()
        
        return []
    
    def _flush_batch(self) -> List[AgentEvent]:
        """输出批量事件并清空缓冲区"""
        if not self._batch_buffer:
            return []
        
        # 智能聚合相同类型的事件
        aggregated_events = self._aggregate_events(self._batch_buffer)
        
        # 清空缓冲区
        self._batch_buffer.clear()
        self._last_batch_time = time.time()
        
        return aggregated_events
    
    def _aggregate_events(self, events: List[AgentEvent]) -> List[AgentEvent]:
        """智能聚合事件"""
        if not events:
            return []
        
        # 按类型分组
        events_by_type: Dict[AgentEventType, List[AgentEvent]] = {}
        for event in events:
            if event.type not in events_by_type:
                events_by_type[event.type] = []
            events_by_type[event.type].append(event)
        
        aggregated = []
        
        for event_type, type_events in events_by_type.items():
            if event_type == AgentEventType.LLM_DELTA:
                # 合并 LLM delta 事件
                merged_content = "".join(e.content or "" for e in type_events)
                if merged_content:
                    # 创建合并的事件
                    merged_event = AgentEvent(
                        type=AgentEventType.LLM_DELTA,
                        content=merged_content,
                        timestamp=type_events[0].timestamp,
                        metadata={
                            "batch_size": len(type_events),
                            "aggregated": True
                        }
                    )
                    aggregated.append(merged_event)
            else:
                # 其他类型的事件保持原样
                aggregated.extend(type_events)
        
        return aggregated
    
    def flush_remaining(self) -> List[AgentEvent]:
        """强制输出剩余的事件"""
        return self._flush_batch()


class EventProcessor:
    """
    事件处理器 - 提供高级事件处理能力
    
    新特性 (Loom 0.0.3):
    - 事件优先级管理
    - 智能事件路由
    - 事件统计和分析
    - 性能监控
    """
    
    def __init__(self, 
                 filters: Optional[List[EventFilter]] = None,
                 enable_stats: bool = True):
        """
        初始化事件处理器
        
        Args:
            filters: 事件过滤器列表
            enable_stats: 启用统计功能
        """
        self.filters = filters or []
        self.enable_stats = enable_stats
        
        # 统计信息
        self._stats = {
            "total_events": 0,
            "filtered_events": 0,
            "batched_events": 0,
            "events_by_type": {},
            "processing_times": []
        }
    
    def process_events(self, events: List[AgentEvent]) -> List[AgentEvent]:
        """
        批量处理事件
        
        Args:
            events: 输入事件列表
            
        Returns:
            处理后的事件列表
        """
        if not events:
            return []
        
        start_time = time.time()
        processed_events = []
        
        for event in events:
            # 更新统计
            if self.enable_stats:
                self._stats["total_events"] += 1
                event_type = event.type.value
                self._stats["events_by_type"][event_type] = \
                    self._stats["events_by_type"].get(event_type, 0) + 1
            
            # 应用过滤器
            for filter_obj in self.filters:
                filtered = filter_obj.process_event(event)
                processed_events.extend(filtered)
            
            # 如果没有过滤器，直接添加事件
            if not self.filters:
                processed_events.append(event)
        
        # 强制刷新所有过滤器的批量缓冲区
        for filter_obj in self.filters:
            remaining = filter_obj.flush_remaining()
            processed_events.extend(remaining)
        
        # 更新处理时间统计
        if self.enable_stats:
            processing_time = time.time() - start_time
            self._stats["processing_times"].append(processing_time)
            self._stats["filtered_events"] = len(processed_events)
        
        return processed_events
    
    def get_stats(self) -> Dict[str, Any]:
        """获取处理统计信息"""
        if not self.enable_stats:
            return {}
        
        avg_processing_time = (
            sum(self._stats["processing_times"]) / len(self._stats["processing_times"])
            if self._stats["processing_times"] else 0
        )
        
        return {
            **self._stats,
            "average_processing_time": avg_processing_time,
            "filter_efficiency": (
                self._stats["filtered_events"] / self._stats["total_events"]
                if self._stats["total_events"] > 0 else 0
            )
        }
    
    def reset_stats(self) -> None:
        """重置统计信息"""
        self._stats = {
            "total_events": 0,
            "filtered_events": 0,
            "batched_events": 0,
            "events_by_type": {},
            "processing_times": []
        }
