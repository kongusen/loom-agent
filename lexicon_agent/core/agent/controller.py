"""
Agent控制器

六阶段流式生成循环，类似Claude Code的tt函数
Phase 1: 上下文检索与生成
Phase 2: 上下文处理与优化  
Phase 3: LLM流式响应处理
Phase 4: 工具调用编排与执行
Phase 5: 结果聚合与上下文更新
Phase 6: 递归循环控制
"""

import asyncio
import time
import uuid
from typing import Dict, Any, List, Optional, AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime

from ...types import (
    AgentEvent, AgentEventType, ToolCall, ToolResult, 
    ToolSafetyLevel, SessionState, ManagedContext
)
from ..context import ContextRetrievalEngine, ContextProcessor, ContextManager
from ..context.retrieval import TaskContext
from ..context.processing import ProcessingConstraints
from ..context.management import SessionConstraints


@dataclass
class SessionContext:
    """会话上下文"""
    session_state: SessionState
    task_context: TaskContext
    constraints: SessionConstraints
    available_tools: List[str] = field(default_factory=list)


@dataclass
class UserInput:
    """用户输入"""
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RecoveryAction:
    """恢复动作"""
    action_type: str
    data: Any = None
    
    @classmethod
    def RETRY_WITH_BACKOFF(cls, delay: float):
        return cls("retry_with_backoff", {"delay": delay})
    
    @classmethod
    def CONTEXT_RECOVERED(cls, context):
        return cls("context_recovered", {"context": context})
    
    @classmethod
    def LLM_ASSISTED_RECOVERY(cls, prompt):
        return cls("llm_assisted_recovery", {"prompt": prompt})


@dataclass
class AgentError(Exception):
    """Agent错误"""
    error_type: str
    message: str
    retry_count: int = 0
    context_id: Optional[str] = None


@dataclass
class ContextError(AgentError):
    """上下文错误"""
    corruption_type: str = "unknown"


@dataclass
class ErrorContext:
    """错误上下文"""
    tool_name: Optional[str] = None
    input_data: Optional[Any] = None
    session_state: Optional[Dict[str, Any]] = None
    retry_count: int = 0
    max_retries: int = 3


class StreamingGenerator:
    """流式生成器"""
    
    def __init__(self, llm_provider):
        self.llm_provider = llm_provider
    
    async def stream_response(self, user_message: str, context: ManagedContext,
                            available_tools: List[str]) -> AsyncIterator[Dict[str, Any]]:
        """流式生成LLM响应"""
        
        if not self.llm_provider:
            yield {"error": "No LLM provider configured"}
            return
        
        # 构建消息
        messages = self._build_messages(user_message, context)
        
        # 构建工具定义
        tools = self._format_tools(available_tools) if available_tools else None
        
        try:
            # 流式调用LLM
            async for chunk in self.llm_provider.generate_stream(
                messages=messages,
                tools=tools
            ):
                # 转换为框架标准格式
                yield {
                    "content": chunk.content,
                    "type": chunk.chunk_type,
                    "metadata": chunk.metadata or {},
                    "is_final": chunk.is_final,
                    "timestamp": chunk.timestamp.isoformat()
                }
                
        except Exception as e:
            yield {
                "error": str(e),
                "type": "error",
                "is_final": True,
                "timestamp": datetime.now().isoformat()
            }
    
    def _build_messages(self, user_message: str, context: ManagedContext) -> List[Dict[str, Any]]:
        """构建消息列表"""
        
        # 简化实现
        system_prompt = self._build_system_prompt(context)
        
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
    
    def _build_system_prompt(self, context: ManagedContext) -> str:
        """构建系统提示"""
        
        # 从管理的上下文中提取相关信息
        active_context = context.active_context.content
        
        base_prompt = """你是一个智能助理，能够使用各种工具来帮助用户完成任务。

当前上下文信息：
{}

请根据用户的请求，智能地选择和使用适当的工具。如果需要调用工具，请按照指定的格式进行。
""".format(str(active_context)[:2000])  # 限制长度
        
        return base_prompt
    
    def _format_tools(self, available_tools: List[str]) -> List[Dict[str, Any]]:
        """格式化工具定义"""
        
        # 简化实现 - 在实际使用中需要从工具注册表获取
        tool_definitions = []
        
        for tool_name in available_tools:
            if tool_name == "file_system":
                tool_definitions.append({
                    "name": "file_system",
                    "description": "文件系统操作工具",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "action": {"type": "string", "enum": ["read", "write", "list"]},
                            "path": {"type": "string"}
                        },
                        "required": ["action", "path"]
                    }
                })
            elif tool_name == "knowledge_base":
                tool_definitions.append({
                    "name": "knowledge_base", 
                    "description": "知识库操作工具",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "action": {"type": "string", "enum": ["search", "add", "create"]},
                            "kb_name": {"type": "string"},
                            "query": {"type": "string"},
                            "text": {"type": "string"}
                        },
                        "required": ["action", "kb_name"]
                    }
                })
        
        return tool_definitions


class ConversationState:
    """对话状态管理"""
    
    def __init__(self):
        self.turns: List[Dict[str, Any]] = []
        self.context_history: List[ManagedContext] = []
        self.performance_metrics: Dict[str, Any] = {
            "total_turns": 0,
            "average_response_time": 0.0,
            "tool_usage_count": 0,
            "error_count": 0
        }
    
    async def update(self, turn_id: str, user_message: str, 
                    assistant_response: str, tool_results: List[Any],
                    context_usage: Dict[str, Any]):
        """更新对话状态"""
        
        turn_data = {
            "turn_id": turn_id,
            "timestamp": datetime.now(),
            "user_message": user_message,
            "assistant_response": assistant_response,
            "tool_results": tool_results,
            "context_usage": context_usage
        }
        
        self.turns.append(turn_data)
        self.performance_metrics["total_turns"] += 1
        self.performance_metrics["tool_usage_count"] += len(tool_results)
    
    def get_recent_context(self, max_turns: int = 5) -> List[Dict[str, Any]]:
        """获取最近的对话上下文"""
        return self.turns[-max_turns:] if self.turns else []


class AgentController:
    """
    六阶段流式生成器，类似Claude Code的tt函数
    """
    
    def __init__(self, 
                 context_engine: ContextRetrievalEngine,
                 context_processor: ContextProcessor,
                 context_manager: ContextManager,
                 orchestration_engine=None,  # 后续实现
                 streaming_generator: Optional[StreamingGenerator] = None):
        
        self.context_engine = context_engine
        self.context_processor = context_processor
        self.context_manager = context_manager
        self.orchestration_engine = orchestration_engine
        self.streaming_generator = streaming_generator
        self.conversation_state = ConversationState()
        
        # 性能监控
        self.performance_tracker = {
            "phase_timings": {},
            "error_recovery_count": 0,
            "recursive_calls": 0
        }
    
    async def stream_run(self, user_message: str,
                        session_context: SessionContext) -> AsyncIterator[AgentEvent]:
        """
        六阶段流式主循环
        """
        turn_id = self._generate_turn_id()
        start_time = time.time()
        
        try:
            # Phase 1: 上下文检索与生成
            async for event in self._phase1_context_retrieval(user_message, session_context):
                yield event
            
            # Phase 2: 上下文处理与优化
            async for event in self._phase2_context_processing(session_context):
                yield event
            
            # Phase 3: LLM流式响应处理
            tool_calls = []
            accumulated_response = ""
            async for event in self._phase3_llm_streaming(user_message, session_context):
                if event.type == AgentEventType.TOOL_CALL_DETECTED:
                    tool_calls.extend(event.content)
                elif event.type == AgentEventType.RESPONSE_DELTA:
                    accumulated_response += event.content
                yield event
            
            # Phase 4: 工具调用编排与执行 (如果需要)
            if tool_calls:
                async for event in self._phase4_tool_orchestration(tool_calls, session_context):
                    yield event
            
            # Phase 5: 结果聚合与上下文更新
            async for event in self._phase5_result_aggregation(
                turn_id, user_message, accumulated_response, tool_calls, session_context
            ):
                yield event
            
            # Phase 6: 递归循环控制
            async for event in self._phase6_recursive_control(
                accumulated_response, tool_calls, session_context
            ):
                yield event
                
        except Exception as e:
            error_event = AgentEvent(
                type=AgentEventType.ERROR,
                content={"error": str(e), "turn_id": turn_id},
                metadata={"phase": "unknown", "recoverable": True}
            )
            yield error_event
            
            # 尝试错误恢复
            recovery_action = await self.recover_from_error(
                AgentError("execution_error", str(e)),
                ErrorContext(session_state=session_context.session_state.__dict__)
            )
            
            if recovery_action.action_type == "retry_with_backoff":
                await asyncio.sleep(recovery_action.data["delay"])
                # 可以选择重试，这里简化处理
        
        finally:
            # 记录性能指标
            total_time = time.time() - start_time
            self._update_performance_metrics(turn_id, total_time)
    
    async def _phase1_context_retrieval(self, user_message: str, 
                                      session_context: SessionContext) -> AsyncIterator[AgentEvent]:
        """Phase 1: 上下文检索与生成"""
        
        phase_start = time.time()
        
        yield AgentEvent(
            type=AgentEventType.THINKING,
            content='分析需求并检索相关上下文...',
            metadata={"phase": 1, "action": "context_retrieval"}
        )
        
        try:
            context_package = await self.context_engine.retrieve_context(
                query=user_message,
                session_state=session_context.session_state,
                task_context=session_context.task_context
            )
            
            # 将检索结果存储到会话上下文中
            session_context.session_state.context_memory.update({
                "current_context_package": context_package.dict()
            })
            
            yield AgentEvent(
                type=AgentEventType.CONTEXT_PROCESSING,
                content=f'检索到 {len(context_package.metadata.get("retrieval_strategies_used", []))} 种策略的上下文信息',
                metadata={
                    "phase": 1,
                    "strategies_used": context_package.metadata.get("retrieval_strategies_used", []),
                    "retrieval_time": context_package.metadata.get("retrieval_time", 0)
                }
            )
            
        except Exception as e:
            yield AgentEvent(
                type=AgentEventType.ERROR,
                content=f'上下文检索失败: {str(e)}',
                metadata={"phase": 1, "recoverable": True}
            )
        
        finally:
            phase_time = time.time() - phase_start
            self.performance_tracker["phase_timings"]["phase1"] = phase_time
    
    async def _phase2_context_processing(self, 
                                       session_context: SessionContext) -> AsyncIterator[AgentEvent]:
        """Phase 2: 上下文处理与优化"""
        
        phase_start = time.time()
        
        yield AgentEvent(
            type=AgentEventType.CONTEXT_PROCESSING,
            content='处理和优化上下文信息...',
            metadata={"phase": 2, "action": "context_processing"}
        )
        
        try:
            # 从会话状态获取上下文包
            context_package_data = session_context.session_state.context_memory.get("current_context_package")
            if not context_package_data:
                raise ValueError("No context package found")
            
            # 重建上下文包对象（简化实现）
            from ...types import ContextPackage
            context_package = ContextPackage(**context_package_data)
            
            # 定义处理约束
            processing_constraints = ProcessingConstraints(
                max_tokens=session_context.constraints.max_memory_mb * 1000,  # 简化映射
                preserve_structure=True,
                goals=["relevance", "completeness", "efficiency"]
            )
            
            # 处理上下文
            processed_context = await self.context_processor.process_context(
                context_package=context_package,
                processing_constraints=processing_constraints
            )
            
            # 管理上下文
            managed_context = await self.context_manager.manage_context(
                processed_context=processed_context,
                session_constraints=session_context.constraints
            )
            
            # 存储管理的上下文
            session_context.session_state.context_memory.update({
                "current_managed_context": {
                    "content": managed_context.active_context.content,
                    "metadata": managed_context.management_metadata
                }
            })
            
            yield AgentEvent(
                type=AgentEventType.CONTEXT_PROCESSING,
                content='上下文处理完成',
                metadata={
                    "phase": 2,
                    "compression_ratio": managed_context.active_context.processing_metadata.get("compression_ratio", 1.0),
                    "memory_tier": getattr(managed_context.memory_footprint.get("allocation", {}), "tier", "unknown")
                }
            )
            
        except Exception as e:
            yield AgentEvent(
                type=AgentEventType.ERROR,
                content=f'上下文处理失败: {str(e)}',
                metadata={"phase": 2, "recoverable": True}
            )
        
        finally:
            phase_time = time.time() - phase_start
            self.performance_tracker["phase_timings"]["phase2"] = phase_time
    
    async def _phase3_llm_streaming(self, user_message: str,
                                  session_context: SessionContext) -> AsyncIterator[AgentEvent]:
        """Phase 3: LLM流式响应处理"""
        
        phase_start = time.time()
        
        yield AgentEvent(
            type=AgentEventType.LLM_STREAMING,
            content='开始LLM流式响应...',
            metadata={"phase": 3, "action": "llm_streaming"}
        )
        
        try:
            if not self.streaming_generator:
                yield AgentEvent(
                    type=AgentEventType.ERROR,
                    content="No LLM streaming generator available",
                    metadata={"phase": 3, "error_type": "missing_component"}
                )
                return
            
            # 创建简化的管理上下文
            from ...types import ManagedContext, ProcessedContext
            
            default_context = ProcessedContext(
                content={"user_message": user_message, "timestamp": datetime.now().isoformat()},
                processing_metadata={"source": "agent_controller", "created": datetime.now().isoformat()}
            )
            
            managed_context = ManagedContext(
                active_context=default_context,
                management_metadata={"created": datetime.now().isoformat()}
            )
            
            # 流式生成
            tool_calls_buffer = []
            
            async for stream_event in self.streaming_generator.stream_response(
                user_message=user_message,
                context=managed_context,
                available_tools=session_context.available_tools
            ):
                
                # 检查是否有错误
                if stream_event.get("error"):
                    yield AgentEvent(
                        type=AgentEventType.ERROR,
                        content=f"LLM Error: {stream_event['error']}",
                        metadata={"phase": 3, "error_source": "llm_provider"}
                    )
                    continue
                
                # 处理不同类型的流式事件
                event_type = stream_event.get("type", "")
                content = stream_event.get("content", "")
                
                if event_type in ["text_delta", "delta", "text"]:
                    # 文本增量
                    yield AgentEvent(
                        type=AgentEventType.RESPONSE_DELTA,
                        content=content,
                        metadata={"phase": 3, "event_type": event_type}
                    )
                elif event_type == "response_complete" or event_type == "complete":
                    # 完整响应
                    yield AgentEvent(
                        type=AgentEventType.RESPONSE_COMPLETE,
                        content=content,
                        metadata={"phase": 3, "event_type": event_type}
                    )
                elif event_type == "tool_call":
                    # 工具调用
                    tool_call = ToolCall(
                        tool_name=stream_event.get("tool_name", "unknown"),
                        input_data=stream_event.get("input_data", {}),
                        safety_level=ToolSafetyLevel.CAUTIOUS
                    )
                    tool_calls_buffer.append(tool_call)
                elif content and isinstance(content, str) and len(content.strip()) > 0:
                    # 兜底：任何有内容的事件都当作响应处理
                    yield AgentEvent(
                        type=AgentEventType.RESPONSE_DELTA,
                        content=content,
                        metadata={"phase": 3, "event_type": event_type or "fallback"}
                    )
            
            # 如果有工具调用，发出事件
            if tool_calls_buffer:
                yield AgentEvent(
                    type=AgentEventType.TOOL_CALL_DETECTED,
                    content=tool_calls_buffer,
                    metadata={"phase": 3, "tool_count": len(tool_calls_buffer)}
                )
                
        except Exception as e:
            yield AgentEvent(
                type=AgentEventType.ERROR,
                content=f'LLM流式处理失败: {str(e)}',
                metadata={"phase": 3, "recoverable": True}
            )
        
        finally:
            phase_time = time.time() - phase_start
            self.performance_tracker["phase_timings"]["phase3"] = phase_time
    
    async def _phase4_tool_orchestration(self, tool_calls: List[ToolCall],
                                       session_context: SessionContext) -> AsyncIterator[AgentEvent]:
        """Phase 4: 工具调用编排与执行"""
        
        phase_start = time.time()
        
        yield AgentEvent(
            type=AgentEventType.TOOL_ORCHESTRATION,
            content=f'编排和执行 {len(tool_calls)} 个工具调用...',
            metadata={"phase": 4, "tool_count": len(tool_calls)}
        )
        
        try:
            # 简化实现：串行执行所有工具
            for tool_call in tool_calls:
                yield AgentEvent(
                    type=AgentEventType.TOOL_PROGRESS,
                    content=f'执行工具: {tool_call.tool_name}',
                    metadata={"phase": 4, "tool_name": tool_call.tool_name}
                )
                
                # 模拟工具执行
                await asyncio.sleep(0.1)  # 模拟执行时间
                
                # 模拟工具结果
                if tool_call.tool_name == "file_system":
                    result = {"files": ["file1.txt", "file2.py", "file3.md"]}
                elif tool_call.tool_name == "knowledge_base":
                    result = {"results": ["相关文档1", "相关文档2"]}
                else:
                    result = {"status": "completed"}
                
                tool_result = ToolResult(
                    tool_call=tool_call,
                    result=result,
                    execution_time=0.1
                )
                
                yield AgentEvent(
                    type=AgentEventType.TOOL_RESULT,
                    content=tool_result,
                    metadata={"phase": 4, "tool_name": tool_call.tool_name, "success": True}
                )
                
        except Exception as e:
            yield AgentEvent(
                type=AgentEventType.ERROR,
                content=f'工具编排失败: {str(e)}',
                metadata={"phase": 4, "recoverable": True}
            )
        
        finally:
            phase_time = time.time() - phase_start
            self.performance_tracker["phase_timings"]["phase4"] = phase_time
    
    async def _phase5_result_aggregation(self, turn_id: str, user_message: str,
                                       assistant_response: str, tool_calls: List[ToolCall],
                                       session_context: SessionContext) -> AsyncIterator[AgentEvent]:
        """Phase 5: 结果聚合与上下文更新"""
        
        phase_start = time.time()
        
        yield AgentEvent(
            type=AgentEventType.CONTEXT_UPDATE,
            content='更新对话上下文...',
            metadata={"phase": 5, "action": "context_update"}
        )
        
        try:
            # 收集工具结果
            tool_results = []
            for tool_call in tool_calls:
                # 这里应该从之前的执行结果中获取，简化实现
                tool_results.append(f"Tool {tool_call.tool_name} executed successfully")
            
            # 更新对话状态
            context_usage = session_context.session_state.context_memory.get("current_managed_context", {})
            
            await self.conversation_state.update(
                turn_id=turn_id,
                user_message=user_message,
                assistant_response=assistant_response,
                tool_results=tool_results,
                context_usage=context_usage
            )
            
            # 更新会话状态
            session_context.session_state.conversation_history.append({
                "turn_id": turn_id,
                "user_message": user_message,
                "assistant_response": assistant_response,
                "tool_results": tool_results,
                "timestamp": datetime.now().isoformat()
            })
            
            yield AgentEvent(
                type=AgentEventType.CONTEXT_UPDATE,
                content='上下文更新完成',
                metadata={
                    "phase": 5,
                    "turn_id": turn_id,
                    "context_items_updated": len(tool_results)
                }
            )
            
        except Exception as e:
            yield AgentEvent(
                type=AgentEventType.ERROR,
                content=f'结果聚合失败: {str(e)}',
                metadata={"phase": 5, "recoverable": True}
            )
        
        finally:
            phase_time = time.time() - phase_start
            self.performance_tracker["phase_timings"]["phase5"] = phase_time
    
    async def _phase6_recursive_control(self, accumulated_response: str, 
                                      tool_calls: List[ToolCall],
                                      session_context: SessionContext) -> AsyncIterator[AgentEvent]:
        """Phase 6: 递归循环控制"""
        
        phase_start = time.time()
        
        try:
            # 检查是否需要继续处理
            should_continue = self._should_continue_processing(accumulated_response, tool_calls)
            
            if should_continue and self.performance_tracker["recursive_calls"] < 3:  # 限制递归深度
                self.performance_tracker["recursive_calls"] += 1
                
                yield AgentEvent(
                    type=AgentEventType.THINKING,
                    content='检测到需要继续处理，开始递归循环...',
                    metadata={"phase": 6, "recursive_call": True}
                )
                
                # 递归调用以处理后续轮次
                async for recursive_event in self.stream_run(
                    user_message="继续处理上述任务",
                    session_context=session_context
                ):
                    # 标记为递归事件
                    recursive_event.metadata["recursive"] = True
                    yield recursive_event
            else:
                yield AgentEvent(
                    type=AgentEventType.TURN_COMPLETE,
                    content='本轮对话完成',
                    metadata={
                        "phase": 6,
                        "total_tools_used": len(tool_calls),
                        "response_length": len(accumulated_response),
                        "recursive_calls": self.performance_tracker["recursive_calls"]
                    }
                )
                
        except Exception as e:
            yield AgentEvent(
                type=AgentEventType.ERROR,
                content=f'递归控制失败: {str(e)}',
                metadata={"phase": 6, "recoverable": False}
            )
        
        finally:
            phase_time = time.time() - phase_start
            self.performance_tracker["phase_timings"]["phase6"] = phase_time
            
            # 重置递归计数器
            if self.performance_tracker["recursive_calls"] > 0:
                self.performance_tracker["recursive_calls"] = 0
    
    def _should_continue_processing(self, response: str, tool_calls: List[ToolCall]) -> bool:
        """检查是否需要继续处理"""
        
        # 简化的继续条件检查
        continue_indicators = [
            "需要进一步", "继续", "接下来", "然后", "还需要"
        ]
        
        # 如果响应中包含继续的指示词
        if any(indicator in response for indicator in continue_indicators):
            return True
        
        # 如果有工具调用但没有完成响应
        if tool_calls and len(response.strip()) < 50:
            return True
        
        return False
    
    async def handle_tool_calls(self, calls: List[ToolCall],
                               context: ManagedContext) -> AsyncIterator[ToolResult]:
        """智能工具调用处理，实现类似Claude Code的并行/串行策略"""
        
        # 工具分类 (受Claude Code启发)
        safe_tools = []  # 只读，无副作用
        cautious_tools = []  # 有限副作用，可并行
        exclusive_tools = []  # 需要独占执行
        
        for call in calls:
            tool_safety = self._classify_tool_safety(call.tool_name)
            if tool_safety == ToolSafetyLevel.SAFE:
                safe_tools.append(call)
            elif tool_safety == ToolSafetyLevel.CAUTIOUS:
                cautious_tools.append(call)
            else:
                exclusive_tools.append(call)
        
        # 并行执行安全工具
        if safe_tools:
            async for result in self._execute_parallel_tools(safe_tools, context):
                yield result
        
        # 谨慎执行中等风险工具
        if cautious_tools:
            async for result in self._execute_cautious_tools(cautious_tools, context):
                yield result
        
        # 串行执行独占工具
        for call in exclusive_tools:
            result = await self._execute_single_tool(call, context)
            yield result
    
    def _classify_tool_safety(self, tool_name: str) -> ToolSafetyLevel:
        """分类工具安全级别"""
        
        # 简化的工具安全分类
        safe_tools = ["file_system.read", "file_system.list", "knowledge_base.search"]
        exclusive_tools = ["file_system.write", "file_system.delete", "code_interpreter"]
        
        if any(safe_tool in tool_name for safe_tool in safe_tools):
            return ToolSafetyLevel.SAFE
        elif any(exclusive_tool in tool_name for exclusive_tool in exclusive_tools):
            return ToolSafetyLevel.EXCLUSIVE
        else:
            return ToolSafetyLevel.CAUTIOUS
    
    async def _execute_parallel_tools(self, tools: List[ToolCall], 
                                    context: ManagedContext) -> AsyncIterator[ToolResult]:
        """并行执行安全工具"""
        
        tasks = [self._execute_single_tool(tool, context) for tool in tools]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, Exception):
                # 创建错误结果
                yield ToolResult(
                    tool_call=tools[0],  # 简化处理
                    error=result
                )
            else:
                yield result
    
    async def _execute_cautious_tools(self, tools: List[ToolCall],
                                    context: ManagedContext) -> AsyncIterator[ToolResult]:
        """谨慎执行中等风险工具"""
        
        # 限制并发数
        semaphore = asyncio.Semaphore(2)  # 最多2个并发
        
        async def execute_with_semaphore(tool):
            async with semaphore:
                return await self._execute_single_tool(tool, context)
        
        tasks = [execute_with_semaphore(tool) for tool in tools]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, Exception):
                yield ToolResult(
                    tool_call=tools[0],  # 简化处理
                    error=result
                )
            else:
                yield result
    
    async def _execute_single_tool(self, tool_call: ToolCall, 
                                 context: ManagedContext) -> ToolResult:
        """执行单个工具"""
        
        start_time = time.time()
        
        try:
            # 模拟工具执行
            await asyncio.sleep(0.1)
            
            # 根据工具类型生成模拟结果
            if tool_call.tool_name == "file_system":
                if tool_call.input_data.get("action") == "list":
                    result = {"files": ["example1.txt", "example2.py"]}
                elif tool_call.input_data.get("action") == "read":
                    result = {"content": "File content here..."}
                else:
                    result = {"status": "success"}
            else:
                result = {"status": "completed", "tool": tool_call.tool_name}
            
            execution_time = time.time() - start_time
            
            return ToolResult(
                tool_call=tool_call,
                result=result,
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            return ToolResult(
                tool_call=tool_call,
                error=e,
                execution_time=execution_time
            )
    
    async def recover_from_error(self, error: AgentError,
                                context: ErrorContext) -> RecoveryAction:
        """多层错误恢复机制，集成上下文重建"""
        
        self.performance_tracker["error_recovery_count"] += 1
        
        # 1. 尝试上下文恢复
        if isinstance(error, ContextError):
            recovered_context = await self.context_manager.recover_context(
                error.context_id, error.corruption_type
            )
            if recovered_context:
                return RecoveryAction.CONTEXT_RECOVERED(recovered_context)
        
        # 2. 尝试自动重试
        if error.retry_count < 3 and self._is_retryable_error(error):
            return RecoveryAction.RETRY_WITH_BACKOFF(
                delay=2 ** error.retry_count
            )
        
        # 3. LLM辅助恢复
        recovery_prompt = await self._generate_recovery_prompt(error, context)
        return RecoveryAction.LLM_ASSISTED_RECOVERY(recovery_prompt)
    
    def _is_retryable_error(self, error: AgentError) -> bool:
        """检查错误是否可重试"""
        
        retryable_types = ["network_error", "timeout_error", "temporary_failure"]
        return error.error_type in retryable_types
    
    async def _generate_recovery_prompt(self, error: AgentError, 
                                      context: ErrorContext) -> str:
        """生成恢复提示"""
        
        return f"""
发生了错误，需要恢复处理：

错误类型: {error.error_type}
错误信息: {error.message}
重试次数: {error.retry_count}

上下文信息:
- 工具名称: {context.tool_name or "未知"}
- 输入数据: {context.input_data or "无"}
- 会话状态: {context.session_state or "无"}

请分析错误原因并提供恢复建议。
"""
    
    def _generate_turn_id(self) -> str:
        """生成轮次ID"""
        return f"turn_{uuid.uuid4().hex[:8]}_{int(time.time())}"
    
    def _update_performance_metrics(self, turn_id: str, total_time: float):
        """更新性能指标"""
        
        # 计算各阶段平均时间
        phase_times = self.performance_tracker["phase_timings"]
        
        # 简化的性能记录
        self.conversation_state.performance_metrics["average_response_time"] = (
            (self.conversation_state.performance_metrics["average_response_time"] * 
             (self.conversation_state.performance_metrics["total_turns"] - 1) + total_time) /
            self.conversation_state.performance_metrics["total_turns"]
        )
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        
        return {
            "conversation_state": self.conversation_state.performance_metrics,
            "phase_timings": self.performance_tracker["phase_timings"],
            "error_recovery_count": self.performance_tracker["error_recovery_count"],
            "recursive_calls": self.performance_tracker["recursive_calls"]
        }