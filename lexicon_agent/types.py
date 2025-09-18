"""
核心类型定义和数据结构
"""

from __future__ import annotations
from typing import (
    Any, Dict, List, Optional, Union, AsyncIterator, Callable, 
    TypeVar, Generic, Protocol, runtime_checkable
)
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
import uuid
import asyncio
from pydantic import BaseModel, Field


# ============================================================================
# 基础枚举类型
# ============================================================================

class AgentEventType(str, Enum):
    """Agent事件类型"""
    THINKING = "thinking"
    CONTEXT_PROCESSING = "context_processing"
    LLM_STREAMING = "llm_streaming"
    TOOL_CALL_DETECTED = "tool_call_detected"
    TOOL_ORCHESTRATION = "tool_orchestration" 
    TOOL_PROGRESS = "tool_progress"
    TOOL_RESULT = "tool_result"
    CONTEXT_UPDATE = "context_update"
    RESPONSE_DELTA = "response_delta"
    TURN_COMPLETE = "turn_complete"
    ERROR = "error"


class ToolSafetyLevel(str, Enum):
    """工具安全级别 (受Claude Code启发)"""
    SAFE = "safe"           # 只读，无副作用，可并行
    CAUTIOUS = "cautious"   # 有限副作用，谨慎并行
    EXCLUSIVE = "exclusive" # 需要独占执行


class CacheStrategy(str, Enum):
    """缓存策略"""
    HOT_CACHE = "hot"       # 热缓存 - 频繁访问
    WARM_CACHE = "warm"     # 温缓存 - 中等频率  
    COLD_STORAGE = "cold"   # 冷存储 - 低频率


class OrchestrationStrategy(str, Enum):
    """编排策略"""
    PRIOR = "prior"                 # 先验编排
    POSTERIOR = "posterior"         # 后验编排
    FUNCTIONAL = "functional"       # 功能型编排
    COMPONENT = "component"         # 组件型编排
    PUPPETEER = "puppeteer"        # 木偶师编排


class CoordinationEventType(str, Enum):
    """协调事件类型"""
    AGENT_JOIN = "agent_join"
    AGENT_LEAVE = "agent_leave"
    CONTEXT_SHARE = "context_share"
    TASK_HANDOFF = "task_handoff"


# ============================================================================
# 基础数据结构
# ============================================================================

@dataclass
class AgentEvent:
    """Agent事件"""
    type: AgentEventType
    content: Any
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass  
class ToolCall:
    """工具调用"""
    tool_name: str
    input_data: Dict[str, Any]
    call_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    safety_level: ToolSafetyLevel = ToolSafetyLevel.CAUTIOUS
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolResult:
    """工具执行结果"""
    tool_call: ToolCall
    result: Optional[Any] = None
    error: Optional[Exception] = None
    execution_time: float = 0.0
    from_cache: bool = False
    cache_strategy: Optional[CacheStrategy] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def success(self) -> bool:
        return self.error is None


@dataclass
class SessionState:
    """会话状态"""
    session_id: str
    user_id: Optional[str] = None
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)
    context_memory: Dict[str, Any] = field(default_factory=dict)
    environment_state: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)


# ============================================================================
# 上下文工程相关类型
# ============================================================================

class ContextRequirements(BaseModel):
    """上下文需求"""
    strategies: List[str] = Field(default=["semantic_search", "temporal_context"])
    max_tokens: int = Field(default=100000)
    preserve_structure: bool = Field(default=True)
    goals: List[str] = Field(default_factory=list)
    target_size: Optional[int] = None
    priority_keywords: List[str] = Field(default_factory=list)


class ContextPackage(BaseModel):
    """上下文包"""
    primary_context: Dict[str, Any]
    metadata: Dict[str, Any] = Field(default_factory=dict)
    retrieval_metrics: Dict[str, Any] = Field(default_factory=dict)
    package_id: str = Field(default_factory=lambda: str(uuid.uuid4()))


class ProcessedContext(BaseModel):
    """处理后的上下文"""
    content: Dict[str, Any]
    processing_metadata: Dict[str, Any] = Field(default_factory=dict)
    optimization_trace: List[Dict[str, Any]] = Field(default_factory=list)
    processed_at: datetime = Field(default_factory=datetime.now)


class ManagedContext(BaseModel):
    """管理的上下文"""
    active_context: ProcessedContext
    memory_footprint: Dict[str, Any] = Field(default_factory=dict)
    cache_reference: Optional[str] = None
    management_metadata: Dict[str, Any] = Field(default_factory=dict)


# ============================================================================
# 编排相关类型
# ============================================================================

@dataclass
class Agent:
    """智能体定义"""
    agent_id: str
    name: str
    capabilities: List[str]
    specialization: str
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    status: str = "available"  # available, busy, offline
    metadata: Dict[str, Any] = field(default_factory=dict)
    configuration: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CoordinationEvent:
    """协调事件"""
    type: CoordinationEventType
    agent: Agent
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


class OrchestrationResult(BaseModel):
    """编排结果"""
    primary_result: Any
    participating_agents: List[Agent]
    context_usage: Dict[str, Any] = Field(default_factory=dict) 
    orchestration_metadata: Dict[str, Any] = Field(default_factory=dict)
    execution_time: float = 0.0


# ============================================================================
# 资源和执行相关类型
# ============================================================================

@dataclass
class ResourceRequirements:
    """资源需求"""
    cpu_intensive: bool = False
    memory_mb: int = 256
    timeout_seconds: int = 30
    disk_io: bool = False
    network_access: bool = False
    
    def conflicts_with(self, other: ResourceRequirements) -> bool:
        """检查资源冲突"""
        # 简单的冲突检测逻辑
        return (self.cpu_intensive and other.cpu_intensive and 
                self.memory_mb + other.memory_mb > 1024)


@dataclass  
class ExecutionContext:
    """执行上下文"""
    session_context: ManagedContext
    resource_constraints: Dict[str, Any] = field(default_factory=dict)
    available_tools: List[str] = field(default_factory=list)
    execution_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    

@dataclass
class ExecutionBatch:
    """执行批次"""
    calls: List[ToolCall] = field(default_factory=list)
    resource_usage: Dict[str, Any] = field(default_factory=dict)
    batch_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)
    
    def can_accommodate(self, requirements: ResourceRequirements, 
                       constraints: Dict[str, Any]) -> bool:
        """检查是否可以容纳新的工具调用"""
        # 简化的容量检查
        max_memory = constraints.get('max_memory_mb', 1024)
        current_memory = self.resource_usage.get('memory_mb', 0)
        return current_memory + requirements.memory_mb <= max_memory
    
    def add_call(self, call: ToolCall, requirements: ResourceRequirements):
        """添加工具调用"""
        self.calls.append(call)
        self.resource_usage['memory_mb'] = (
            self.resource_usage.get('memory_mb', 0) + requirements.memory_mb
        )
    
    def get_execution_time(self) -> float:
        """获取执行时间"""
        return (datetime.now() - self.created_at).total_seconds()


# ============================================================================
# 协议接口定义
# ============================================================================

@runtime_checkable
class Tool(Protocol):
    """工具协议接口"""
    name: str
    description: str
    safety_level: ToolSafetyLevel
    resource_requirements: ResourceRequirements
    
    async def execute(self, input_data: Dict[str, Any]) -> Any:
        """执行工具"""
        ...
    
    def can_run_parallel_with(self, other: Tool) -> bool:
        """检查是否可以与其他工具并行运行"""
        ...


@runtime_checkable  
class LLMProvider(Protocol):
    """LLM提供商协议"""
    
    async def stream_chat(self, messages: List[Dict[str, Any]], 
                         model: str, **kwargs) -> AsyncIterator[Dict[str, Any]]:
        """流式聊天"""
        ...
    
    async def complete(self, prompt: str, model: str, **kwargs) -> str:
        """完整响应"""
        ...


# ============================================================================
# 缓存相关类型
# ============================================================================

@dataclass
class CachedResult:
    """缓存结果"""
    result: Any
    timestamp: float
    ttl: int
    access_count: int = 0
    
    def is_expired(self) -> bool:
        """检查是否过期"""
        import time
        return time.time() - self.timestamp > self.ttl


# ============================================================================
# 工具类型
# ============================================================================

T = TypeVar('T')

class WeakValueDictionary(Generic[T]):
    """弱引用值字典 (简化实现)"""
    
    def __init__(self):
        self._data: Dict[str, Any] = {}
    
    def __setitem__(self, key: str, value: T):
        import weakref
        self._data[key] = weakref.ref(value) if hasattr(value, '__weakref__') else value
    
    def __getitem__(self, key: str) -> Optional[T]:
        ref = self._data.get(key)
        if ref is None:
            return None
        if hasattr(ref, '__call__'):  # 是弱引用
            value = ref()
            if value is None:
                del self._data[key]
            return value
        return ref
    
    def __contains__(self, key: str) -> bool:
        return key in self._data
    
    def __delitem__(self, key: str):
        del self._data[key]