"""
流式处理管道

实现端到端的流式处理管道，整合所有核心组件
"""

import asyncio
import time
import uuid
from typing import Dict, Any, List, Optional, AsyncIterator, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime

from ...types import AgentEvent, AgentEventType, ToolCall, ToolResult, ManagedContext
from ..agent.controller import AgentController, SessionContext
from ..orchestration.coordinator import AgentCoordinator, CoordinationRequest
from ..tools.scheduler import IntelligentToolScheduler
from .processor import StreamingProcessor, StreamChunk
from .optimizer import PerformanceOptimizer


@dataclass
class PipelineStage:
    """管道阶段"""
    stage_id: str
    name: str
    processor: Callable
    dependencies: List[str] = field(default_factory=list)
    parallel_execution: bool = True
    timeout: float = 30.0
    retry_attempts: int = 3


@dataclass
class PipelineRequest:
    """管道请求"""
    request_id: str
    user_message: str
    session_context: Dict[str, Any] = field(default_factory=dict)
    processing_options: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    
    # 时间戳
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class PipelineResult:
    """管道结果"""
    request_id: str
    success: bool
    final_response: Any
    processing_time: float
    stages_completed: List[str] = field(default_factory=list)
    errors: List[Dict[str, Any]] = field(default_factory=list)
    performance_metrics: Dict[str, Any] = field(default_factory=dict)


class StreamingPipeline:
    """流式处理管道主类"""
    
    def __init__(self,
                 agent_controller: Optional[AgentController] = None,
                 agent_coordinator: Optional[AgentCoordinator] = None,
                 tool_scheduler: Optional[IntelligentToolScheduler] = None,
                 streaming_processor: Optional[StreamingProcessor] = None,
                 performance_optimizer: Optional[PerformanceOptimizer] = None):
        
        # 核心组件
        self.agent_controller = agent_controller
        self.agent_coordinator = agent_coordinator
        self.tool_scheduler = tool_scheduler
        self.streaming_processor = streaming_processor or StreamingProcessor()
        self.performance_optimizer = performance_optimizer or PerformanceOptimizer()
        
        # 管道配置
        self.pipeline_stages: List[PipelineStage] = []
        self.active_requests: Dict[str, PipelineRequest] = {}
        self.request_history: List[PipelineResult] = []
        
        # 性能配置
        self.max_concurrent_requests = 10
        self.default_timeout = 60.0
        self.enable_performance_monitoring = True
        
        # 统计信息
        self.pipeline_stats = {
            "total_requests": 0,
            "completed_requests": 0,
            "failed_requests": 0,
            "average_processing_time": 0.0,
            "throughput_per_minute": 0.0
        }
        
        # 初始化默认管道
        self._setup_default_pipeline()
    
    def _setup_default_pipeline(self):
        """设置默认处理管道"""
        
        # 阶段1: 请求预处理
        self.add_pipeline_stage(PipelineStage(
            stage_id="preprocessing",
            name="Request Preprocessing",
            processor=self._preprocess_request,
            dependencies=[],
            parallel_execution=False
        ))
        
        # 阶段2: 智能体协调
        self.add_pipeline_stage(PipelineStage(
            stage_id="agent_coordination",
            name="Agent Coordination",
            processor=self._coordinate_agents,
            dependencies=["preprocessing"],
            parallel_execution=False
        ))
        
        # 阶段3: 上下文处理
        self.add_pipeline_stage(PipelineStage(
            stage_id="context_processing",
            name="Context Processing",
            processor=self._process_context,
            dependencies=["agent_coordination"],
            parallel_execution=True
        ))
        
        # 阶段4: 核心处理
        self.add_pipeline_stage(PipelineStage(
            stage_id="core_processing",
            name="Core Agent Processing",
            processor=self._core_processing,
            dependencies=["context_processing"],
            parallel_execution=False
        ))
        
        # 阶段5: 工具调度
        self.add_pipeline_stage(PipelineStage(
            stage_id="tool_scheduling",
            name="Tool Scheduling",
            processor=self._schedule_tools,
            dependencies=["core_processing"],
            parallel_execution=True
        ))
        
        # 阶段6: 流式响应
        self.add_pipeline_stage(PipelineStage(
            stage_id="streaming_response",
            name="Streaming Response",
            processor=self._generate_streaming_response,
            dependencies=["tool_scheduling"],
            parallel_execution=False
        ))
        
        # 阶段7: 后处理
        self.add_pipeline_stage(PipelineStage(
            stage_id="postprocessing",
            name="Response Postprocessing",
            processor=self._postprocess_response,
            dependencies=["streaming_response"],
            parallel_execution=True
        ))
    
    def add_pipeline_stage(self, stage: PipelineStage):
        """添加管道阶段"""
        
        # 检查依赖是否存在
        existing_stage_ids = {s.stage_id for s in self.pipeline_stages}
        for dep in stage.dependencies:
            if dep not in existing_stage_ids:
                raise ValueError(f"Dependency {dep} not found for stage {stage.stage_id}")
        
        self.pipeline_stages.append(stage)
    
    def remove_pipeline_stage(self, stage_id: str) -> bool:
        """移除管道阶段"""
        
        # 检查是否有其他阶段依赖此阶段
        for stage in self.pipeline_stages:
            if stage_id in stage.dependencies:
                raise ValueError(f"Cannot remove stage {stage_id}: it's a dependency for {stage.stage_id}")
        
        self.pipeline_stages = [s for s in self.pipeline_stages if s.stage_id != stage_id]
        return True
    
    async def process_request(self, user_message: str,
                            session_context: Optional[Dict[str, Any]] = None,
                            processing_options: Optional[Dict[str, Any]] = None) -> AsyncIterator[StreamChunk]:
        """处理用户请求的主入口"""
        
        # 创建管道请求
        request = PipelineRequest(
            request_id=self._generate_request_id(),
            user_message=user_message,
            session_context=session_context or {},
            processing_options=processing_options or {}
        )
        
        self.active_requests[request.request_id] = request
        self.pipeline_stats["total_requests"] += 1
        
        try:
            # 执行管道处理
            async for chunk in self._execute_pipeline(request):
                yield chunk
                
        except Exception as e:
            error_chunk = StreamChunk(
                chunk_id=f"{request.request_id}_error",
                data={"error": str(e), "stage": "pipeline_execution"},
                chunk_type="error",
                metadata={"request_id": request.request_id},
                is_final=True
            )
            yield error_chunk
            
        finally:
            # 清理
            if request.request_id in self.active_requests:
                del self.active_requests[request.request_id]
    
    async def _execute_pipeline(self, request: PipelineRequest) -> AsyncIterator[StreamChunk]:
        """执行管道处理"""
        
        request.started_at = datetime.now()
        pipeline_context = {"request": request, "stage_results": {}}
        
        try:
            # 按依赖顺序执行阶段
            execution_order = self._calculate_execution_order()
            
            for stage_id in execution_order:
                stage = next(s for s in self.pipeline_stages if s.stage_id == stage_id)
                
                # 发送阶段开始事件
                yield StreamChunk(
                    chunk_id=f"{request.request_id}_{stage_id}_start",
                    data={"stage": stage_id, "status": "starting"},
                    chunk_type="stage_event",
                    metadata={"request_id": request.request_id, "stage_name": stage.name}
                )
                
                # 执行阶段
                stage_start = time.time()
                try:
                    print(f"DEBUG: Executing stage {stage_id}")
                    stage_result = await self._execute_stage(stage, pipeline_context)
                    print(f"DEBUG: Stage {stage_id} completed with result: {type(stage_result)}")
                    pipeline_context["stage_results"][stage_id] = stage_result
                    
                    stage_duration = time.time() - stage_start
                    
                    # 发送阶段完成事件
                    yield StreamChunk(
                        chunk_id=f"{request.request_id}_{stage_id}_complete",
                        data={
                            "stage": stage_id,
                            "status": "completed",
                            "duration": stage_duration,
                            "result": stage_result
                        },
                        chunk_type="stage_result",
                        metadata={"request_id": request.request_id, "stage_name": stage.name}
                    )
                    
                    # 如果是流式响应阶段，直接传递流数据
                    if stage_id == "streaming_response" and hasattr(stage_result, '__aiter__'):
                        async for response_chunk in stage_result:
                            yield response_chunk
                    
                except Exception as e:
                    stage_duration = time.time() - stage_start
                    
                    # 发送阶段错误事件
                    error_chunk = StreamChunk(
                        chunk_id=f"{request.request_id}_{stage_id}_error",
                        data={
                            "stage": stage_id,
                            "status": "failed",
                            "error": str(e),
                            "duration": stage_duration
                        },
                        chunk_type="stage_error",
                        metadata={"request_id": request.request_id, "stage_name": stage.name}
                    )
                    yield error_chunk
                    
                    # 根据阶段配置决定是否继续
                    if stage.stage_id in ["preprocessing", "agent_coordination"]:
                        raise e  # 关键阶段失败，终止流程
            
            # 发送完成事件
            request.completed_at = datetime.now()
            processing_time = (request.completed_at - request.started_at).total_seconds()
            
            yield StreamChunk(
                chunk_id=f"{request.request_id}_complete",
                data={
                    "status": "completed",
                    "processing_time": processing_time,
                    "stages_completed": list(pipeline_context["stage_results"].keys())
                },
                chunk_type="pipeline_complete",
                metadata={"request_id": request.request_id},
                is_final=True
            )
            
            # 更新统计
            self.pipeline_stats["completed_requests"] += 1
            self._update_performance_stats(processing_time)
            
        except Exception as e:
            self.pipeline_stats["failed_requests"] += 1
            raise e
    
    def _calculate_execution_order(self) -> List[str]:
        """计算执行顺序（拓扑排序）"""
        
        # 简化的拓扑排序实现
        in_degree = {stage.stage_id: 0 for stage in self.pipeline_stages}
        
        # 计算入度
        for stage in self.pipeline_stages:
            for dep in stage.dependencies:
                in_degree[stage.stage_id] += 1
        
        # 拓扑排序
        queue = [stage_id for stage_id, degree in in_degree.items() if degree == 0]
        result = []
        
        while queue:
            current = queue.pop(0)
            result.append(current)
            
            # 更新依赖此节点的其他节点
            for stage in self.pipeline_stages:
                if current in stage.dependencies:
                    in_degree[stage.stage_id] -= 1
                    if in_degree[stage.stage_id] == 0:
                        queue.append(stage.stage_id)
        
        return result
    
    async def _execute_stage(self, stage: PipelineStage, context: Dict[str, Any]) -> Any:
        """执行单个管道阶段"""
        
        try:
            # 检查是否是streaming_response阶段，需要特殊处理AsyncIterator
            if stage.stage_id == "streaming_response":
                print(f"DEBUG: Executing streaming response stage: {stage.stage_id}")
                # 直接调用处理器并返回AsyncIterator
                result = stage.processor(context)
                print(f"DEBUG: Streaming response stage returned: {type(result)}")
                return result
            else:
                # 普通阶段的处理
                result = await asyncio.wait_for(
                    stage.processor(context),
                    timeout=stage.timeout
                )
                return result
            
        except asyncio.TimeoutError:
            raise TimeoutError(f"Stage {stage.stage_id} timed out after {stage.timeout}s")
        except Exception as e:
            # 重试逻辑
            for attempt in range(stage.retry_attempts):
                try:
                    await asyncio.sleep(0.5 * (attempt + 1))  # 指数退避
                    if stage.stage_id == "streaming_response":
                        result = stage.processor(context)
                        return result
                    else:
                        result = await asyncio.wait_for(
                            stage.processor(context),
                            timeout=stage.timeout
                        )
                        return result
                except Exception:
                    if attempt == stage.retry_attempts - 1:
                        raise e
                    continue
    
    # 管道阶段实现
    
    async def _preprocess_request(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """预处理请求"""
        
        request = context["request"]
        
        # 输入验证
        if not request.user_message.strip():
            raise ValueError("Empty user message")
        
        # 意图分析（简化实现）
        intent = self._analyze_intent(request.user_message)
        
        # 上下文增强
        enhanced_context = {
            "original_message": request.user_message,
            "analyzed_intent": intent,
            "session_info": request.session_context,
            "processing_options": request.processing_options,
            "timestamp": datetime.now().isoformat()
        }
        
        return {
            "preprocessed_input": enhanced_context,
            "intent": intent,
            "validation_passed": True
        }
    
    async def _coordinate_agents(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """协调智能体"""
        
        if not self.agent_coordinator:
            return {"coordination_result": "no_coordinator", "agents": []}
        
        request = context["request"]
        preprocessing_result = context["stage_results"]["preprocessing"]
        
        # 创建协调请求
        coordination_request = CoordinationRequest(
            user_message=request.user_message,
            available_agents=[],  # 这里应该从注册表获取可用智能体
            session_constraints=request.session_context,
            metadata=preprocessing_result["preprocessed_input"]
        )
        
        # 执行协调
        coordination_result = await self.agent_coordinator.coordinate(coordination_request)
        
        return {
            "coordination_result": coordination_result,
            "selected_agents": coordination_result.participating_agents,
            "strategy_used": coordination_result.strategy_used
        }
    
    async def _process_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """处理上下文"""
        
        request = context["request"]
        
        # 构建管理上下文
        from ...types import ProcessedContext
        
        # 创建基本的处理上下文
        processed_context = ProcessedContext(
            content={"user_message": request.user_message, "timestamp": datetime.now().isoformat()},
            processing_metadata={"processor": "pipeline", "stage": "context_processing"},
            optimization_trace=[]
        )
        
        managed_context = ManagedContext(
            active_context=processed_context,
            management_metadata={"processed_at": datetime.now().isoformat()}
        )
        
        return {
            "managed_context": managed_context,
            "context_size": len(request.user_message),
            "processing_metadata": {"method": "default"}
        }
    
    async def _core_processing(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """核心处理"""
        
        if not self.agent_controller:
            return {"core_result": "no_controller", "events": []}
        
        request = context["request"]
        
        # 获取上下文处理的结果
        context_processing_result = context.get("stage_results", {}).get("context_processing", {})
        managed_context = context_processing_result.get("managed_context")
        
        # 创建基本的会话上下文
        from ..context.retrieval import TaskContext
        from ..context.management import SessionConstraints
        from ...types import SessionState
        
        # 创建基本的会话状态
        session_state = SessionState(
            session_id=f"session_{request.request_id}",
            user_id="default_user",
            conversation_history=[],
            context_memory={},
            environment_state={}
        )
        
        # 创建任务上下文
        task_context = TaskContext(
            task_type="chat",
            complexity_level=1,
            domain="general",
            metadata={"task_id": f"task_{request.request_id}"}
        )
        
        # 创建会话约束
        constraints = SessionConstraints(
            max_memory_mb=512,
            max_context_items=1000,
            cache_policy="adaptive",
            compression_level=1
        )
        
        session_context = SessionContext(
            session_state=session_state,
            task_context=task_context,
            constraints=constraints,
            available_tools=["file_system", "knowledge_base"]
        )
        
        # 如果有managed_context，将其存储到session_state中
        if managed_context:
            session_context.session_state.context_memory["current_managed_context"] = {
                "content": managed_context.active_context.content,
                "metadata": managed_context.management_metadata
            }
        
        # 收集处理事件
        events = []
        async for event in self.agent_controller.stream_run(
            user_message=request.user_message,
            session_context=session_context
        ):
            events.append(event)
        
        return {
            "core_result": "completed",
            "events": events,
            "event_count": len(events)
        }
    
    async def _schedule_tools(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """调度工具"""
        
        if not self.tool_scheduler:
            return {"tool_result": "no_scheduler", "tool_calls": []}
        
        # 从核心处理结果中提取工具调用
        core_result = context["stage_results"]["core_processing"]
        events = core_result.get("events", [])
        
        tool_calls = []
        for event in events:
            if event.type == AgentEventType.TOOL_CALL_DETECTED:
                tool_calls.extend(event.content)
        
        if not tool_calls:
            return {"tool_result": "no_tools_needed", "tool_calls": []}
        
        # 执行工具调度（简化实现）
        return {
            "tool_result": "scheduled",
            "tool_calls": tool_calls,
            "scheduled_count": len(tool_calls)
        }
    
    async def _generate_streaming_response(self, context: Dict[str, Any]) -> AsyncIterator[StreamChunk]:
        """生成流式响应"""
        
        print("DEBUG: _generate_streaming_response method started")
        request = context["request"]
        
        # 收集所有阶段的结果
        all_results = context["stage_results"]
        
        # 构建最终响应
        response_data = {
            "user_message": request.user_message,
            "processing_summary": {
                stage: result for stage, result in all_results.items()
            },
            "timestamp": datetime.now().isoformat()
        }
        
        # 发送真实的LLM响应
        core_result = all_results.get("core_processing", {})
        events = core_result.get("events", [])
        
        print(f"DEBUG: core_result = {core_result}")
        print(f"DEBUG: events count = {len(events)}")
        
        if events:
            # 从AgentController事件中提取响应文本
            response_parts = []
            complete_response = ""
            
            for i, event in enumerate(events):
                print(f"DEBUG: Event {i} = {event} (type: {type(event)})")
                # 更灵活的事件类型检查
                event_type = None
                if hasattr(event, 'type'):
                    if hasattr(event.type, 'value'):
                        event_type = event.type.value
                    else:
                        event_type = str(event.type)
                
                # 收集响应内容
                if event_type == "response_delta" and hasattr(event, 'content'):
                    if isinstance(event.content, str):
                        response_parts.append(event.content)
                elif event_type == "response_complete" and hasattr(event, 'content'):
                    if isinstance(event.content, str):
                        complete_response = event.content
                        break  # 完整响应已获得
                elif hasattr(event, 'content') and isinstance(event.content, str):
                    # 兜底：任何包含字符串内容的事件
                    if len(event.content) > 0 and not event.content.startswith('开始') and not event.content.startswith('分析'):
                        response_parts.append(event.content)
            
            # 优先使用完整响应，否则合并片段
            if complete_response:
                yield StreamChunk(
                    chunk_id=f"{request.request_id}_response_complete",
                    data=complete_response,
                    chunk_type="response_text",
                    metadata={"request_id": request.request_id, "complete": True},
                    is_final=True
                )
            elif response_parts:
                # 流式发送响应片段
                accumulated_text = ""
                for i, part in enumerate(response_parts):
                    accumulated_text += part
                    yield StreamChunk(
                        chunk_id=f"{request.request_id}_response_{i}",
                        data=part,
                        chunk_type="response_text",
                        metadata={"request_id": request.request_id, "part_index": i},
                        is_final=(i == len(response_parts) - 1)
                    )
                    await asyncio.sleep(0.001)  # 减少延迟
            else:
                # 备用响应
                fallback_text = f"已处理您的消息：'{request.user_message}'"
                yield StreamChunk(
                    chunk_id=f"{request.request_id}_response_fallback",
                    data=fallback_text,
                    chunk_type="response_text",
                    metadata={"request_id": request.request_id, "fallback": True},
                    is_final=True
                )
        else:
            # 如果没有事件，发送基本响应
            basic_response = f"收到您的消息：'{request.user_message}'"
            yield StreamChunk(
                chunk_id=f"{request.request_id}_response_basic",
                data=basic_response,
                chunk_type="response_text",
                metadata={"request_id": request.request_id, "basic": True},
                is_final=True
            )
        
        # 发送最终数据
        yield StreamChunk(
            chunk_id=f"{request.request_id}_response_data",
            data=response_data,
            chunk_type="response_data",
            metadata={"request_id": request.request_id},
            is_final=True
        )
    
    async def _postprocess_response(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """后处理响应"""
        
        # 性能记录
        if self.enable_performance_monitoring:
            request = context["request"]
            processing_time = (datetime.now() - request.started_at).total_seconds()
            self.performance_optimizer.record_response_time(processing_time * 1000)
            self.performance_optimizer.record_request(success=True)
        
        return {
            "postprocessing_result": "completed",
            "performance_recorded": self.enable_performance_monitoring
        }
    
    # 辅助方法
    
    def _analyze_intent(self, message: str) -> Dict[str, Any]:
        """分析用户意图（简化实现）"""
        
        message_lower = message.lower()
        
        intent_keywords = {
            "question": ["what", "how", "why", "when", "where", "?", "什么", "如何", "为什么"],
            "request": ["please", "can you", "could you", "请", "能否", "可以"],
            "command": ["create", "make", "build", "delete", "remove", "创建", "制作", "删除"],
            "analysis": ["analyze", "check", "review", "examine", "分析", "检查", "审查"]
        }
        
        detected_intents = {}
        for intent_type, keywords in intent_keywords.items():
            score = sum(1 for keyword in keywords if keyword in message_lower)
            if score > 0:
                detected_intents[intent_type] = score
        
        primary_intent = max(detected_intents.items(), key=lambda x: x[1])[0] if detected_intents else "general"
        
        return {
            "primary_intent": primary_intent,
            "all_intents": detected_intents,
            "confidence": detected_intents.get(primary_intent, 0) / 3,
            "message_length": len(message),
            "word_count": len(message.split())
        }
    
    def _generate_request_id(self) -> str:
        """生成请求ID"""
        return f"pipeline_{uuid.uuid4().hex[:8]}_{int(time.time())}"
    
    def _update_performance_stats(self, processing_time: float):
        """更新性能统计"""
        
        total_completed = self.pipeline_stats["completed_requests"]
        current_avg = self.pipeline_stats["average_processing_time"]
        
        self.pipeline_stats["average_processing_time"] = (
            (current_avg * (total_completed - 1) + processing_time) / total_completed
        )
        
        # 计算吞吐量（简化）
        if total_completed > 0:
            self.pipeline_stats["throughput_per_minute"] = 60.0 / self.pipeline_stats["average_processing_time"]
    
    # 管理方法
    
    def get_pipeline_status(self) -> Dict[str, Any]:
        """获取管道状态"""
        
        return {
            "pipeline_stages": [
                {
                    "stage_id": stage.stage_id,
                    "name": stage.name,
                    "dependencies": stage.dependencies,
                    "parallel_execution": stage.parallel_execution,
                    "timeout": stage.timeout
                }
                for stage in self.pipeline_stages
            ],
            "active_requests": len(self.active_requests),
            "pipeline_stats": self.pipeline_stats,
            "components_status": {
                "agent_controller": self.agent_controller is not None,
                "agent_coordinator": self.agent_coordinator is not None,
                "tool_scheduler": self.tool_scheduler is not None,
                "streaming_processor": self.streaming_processor is not None,
                "performance_optimizer": self.performance_optimizer is not None
            }
        }
    
    def get_request_status(self, request_id: str) -> Optional[Dict[str, Any]]:
        """获取请求状态"""
        
        request = self.active_requests.get(request_id)
        if not request:
            return None
        
        return {
            "request_id": request_id,
            "user_message": request.user_message[:100] + "..." if len(request.user_message) > 100 else request.user_message,
            "created_at": request.created_at.isoformat(),
            "started_at": request.started_at.isoformat() if request.started_at else None,
            "status": "processing",
            "priority": request.priority
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        
        try:
            # 检查组件状态
            component_health = {}
            
            if self.performance_optimizer:
                optimizer_health = await self.performance_optimizer.health_check()
                component_health["performance_optimizer"] = optimizer_health["status"]
            
            if self.streaming_processor:
                processor_health = await self.streaming_processor.health_check()
                component_health["streaming_processor"] = processor_health["status"]
            
            # 检查管道负载
            active_requests = len(self.active_requests)
            load_factor = active_requests / self.max_concurrent_requests
            
            # 计算健康分数
            health_score = 1.0
            
            if load_factor > 0.8:
                health_score -= 0.3
            elif load_factor > 0.6:
                health_score -= 0.1
            
            # 检查错误率
            total_requests = self.pipeline_stats["total_requests"]
            if total_requests > 0:
                error_rate = self.pipeline_stats["failed_requests"] / total_requests
                if error_rate > 0.1:
                    health_score -= 0.4
                elif error_rate > 0.05:
                    health_score -= 0.2
            
            health_score = max(0.0, health_score)
            
            return {
                "status": "healthy" if health_score > 0.8 else "degraded" if health_score > 0.5 else "unhealthy",
                "health_score": health_score,
                "active_requests": active_requests,
                "load_factor": load_factor,
                "component_health": component_health,
                "pipeline_stats": self.pipeline_stats,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "health_score": 0.0,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }