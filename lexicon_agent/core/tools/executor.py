"""
工具执行器

负责实际的工具执行、监控和错误处理
"""

import asyncio
import time
import uuid
from typing import Dict, Any, List, Optional, AsyncIterator, Callable
from dataclasses import dataclass, field
from datetime import datetime
from contextlib import asynccontextmanager

from ...types import ToolCall, ToolResult, ToolSafetyLevel
from .registry import ToolRegistry, BaseTool
from .safety import ToolSafetyManager


@dataclass
class ExecutionSession:
    """执行会话"""
    session_id: str
    start_time: datetime
    tool_calls: List[ToolCall] = field(default_factory=list)
    results: List[ToolResult] = field(default_factory=list)
    active_tools: Dict[str, asyncio.Task] = field(default_factory=dict)
    session_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionMonitor:
    """执行监控器"""
    session_id: str
    start_time: float
    timeout: float = 30.0
    progress_callback: Optional[Callable] = None
    
    # 监控状态
    completed_tools: int = 0
    total_tools: int = 0
    current_stage: str = "initializing"
    errors: List[Dict[str, Any]] = field(default_factory=list)


class ToolExecutor:
    """工具执行器"""
    
    def __init__(self, tool_registry: ToolRegistry, 
                 safety_manager: Optional['ToolSafetyManager'] = None):
        self.tool_registry = tool_registry
        self.safety_manager = safety_manager or ToolSafetyManager()
        
        # 执行会话管理
        self.active_sessions: Dict[str, ExecutionSession] = {}
        self.execution_history: List[ExecutionSession] = []
        
        # 性能监控
        self.execution_stats = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "average_execution_time": 0.0,
            "tool_usage_distribution": {}
        }
        
        # 错误处理
        self.error_handlers: Dict[str, Callable] = {
            "timeout": self._handle_timeout_error,
            "validation": self._handle_validation_error,
            "execution": self._handle_execution_error,
            "safety": self._handle_safety_error
        }
    
    async def execute_single_tool(self, tool_call: ToolCall,
                                 session_id: Optional[str] = None,
                                 monitor: Optional[ExecutionMonitor] = None) -> ToolResult:
        """执行单个工具"""
        
        execution_start = time.time()
        
        # 创建或获取执行会话
        if session_id is None:
            session_id = self._generate_session_id()
        
        session = self._get_or_create_session(session_id)
        session.tool_calls.append(tool_call)
        
        try:
            # 1. 安全检查
            safety_result = await self.safety_manager.validate_tool_call(tool_call)
            if not safety_result["allowed"]:
                raise SecurityError(f"Tool call blocked by safety manager: {safety_result['reason']}")
            
            # 2. 获取工具实例
            tool = self.tool_registry.get_tool(tool_call.tool_name)
            if not tool:
                raise ValueError(f"Tool {tool_call.tool_name} not found in registry")
            
            # 3. 输入验证
            if not await tool.validate_input(tool_call.input_data):
                raise ValueError(f"Invalid input data for tool {tool_call.tool_name}")
            
            # 4. 创建执行任务
            execution_task = asyncio.create_task(
                self._execute_tool_with_monitoring(tool, tool_call, monitor)
            )
            
            # 注册活跃任务
            session.active_tools[tool_call.call_id] = execution_task
            
            # 5. 等待执行完成
            result = await execution_task
            
            # 6. 清理和记录
            del session.active_tools[tool_call.call_id]
            session.results.append(result)
            
            execution_time = time.time() - execution_start
            self._update_execution_stats(tool_call.tool_name, execution_time, True)
            
            return result
            
        except Exception as e:
            execution_time = time.time() - execution_start
            
            # 创建错误结果
            error_result = ToolResult(
                tool_call=tool_call,
                error=e,
                execution_time=execution_time
            )
            
            session.results.append(error_result)
            self._update_execution_stats(tool_call.tool_name, execution_time, False)
            
            # 错误处理
            await self._handle_execution_error(e, tool_call, session)
            
            return error_result
    
    async def execute_batch_tools(self, tool_calls: List[ToolCall],
                                 execution_strategy: str = "parallel",
                                 session_id: Optional[str] = None) -> AsyncIterator[ToolResult]:
        """批量执行工具"""
        
        if session_id is None:
            session_id = self._generate_session_id()
        
        session = self._get_or_create_session(session_id)
        
        # 创建执行监控器
        monitor = ExecutionMonitor(
            session_id=session_id,
            start_time=time.time(),
            total_tools=len(tool_calls)
        )
        
        try:
            if execution_strategy == "parallel":
                async for result in self._execute_parallel_batch(tool_calls, session, monitor):
                    yield result
            elif execution_strategy == "serial":
                async for result in self._execute_serial_batch(tool_calls, session, monitor):
                    yield result
            elif execution_strategy == "smart":
                async for result in self._execute_smart_batch(tool_calls, session, monitor):
                    yield result
            else:
                raise ValueError(f"Unknown execution strategy: {execution_strategy}")
                
        finally:
            # 清理会话
            self._cleanup_session(session_id)
    
    async def _execute_parallel_batch(self, tool_calls: List[ToolCall],
                                    session: ExecutionSession,
                                    monitor: ExecutionMonitor) -> AsyncIterator[ToolResult]:
        """并行执行批量工具"""
        
        monitor.current_stage = "parallel_execution"
        
        # 创建所有执行任务
        tasks = []
        for tool_call in tool_calls:
            task = asyncio.create_task(
                self.execute_single_tool(tool_call, session.session_id, monitor)
            )
            tasks.append((tool_call, task))
        
        # 等待所有任务完成并收集结果
        for tool_call, task in tasks:
            try:
                result = await task
                monitor.completed_tools += 1
                yield result
            except Exception as e:
                # 创建错误结果
                error_result = ToolResult(
                    tool_call=tool_call,
                    error=e,
                    execution_time=0.0
                )
                monitor.errors.append({
                    "tool_call_id": tool_call.call_id,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })
                yield error_result
    
    async def _execute_serial_batch(self, tool_calls: List[ToolCall],
                                  session: ExecutionSession,
                                  monitor: ExecutionMonitor) -> AsyncIterator[ToolResult]:
        """串行执行批量工具"""
        
        monitor.current_stage = "serial_execution"
        
        for tool_call in tool_calls:
            try:
                result = await self.execute_single_tool(tool_call, session.session_id, monitor)
                monitor.completed_tools += 1
                yield result
            except Exception as e:
                error_result = ToolResult(
                    tool_call=tool_call,
                    error=e,
                    execution_time=0.0
                )
                monitor.errors.append({
                    "tool_call_id": tool_call.call_id,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })
                yield error_result
    
    async def _execute_smart_batch(self, tool_calls: List[ToolCall],
                                 session: ExecutionSession,
                                 monitor: ExecutionMonitor) -> AsyncIterator[ToolResult]:
        """智能执行批量工具（根据安全级别分组）"""
        
        monitor.current_stage = "smart_execution"
        
        # 按安全级别分组
        safe_tools = []
        cautious_tools = []
        exclusive_tools = []
        
        for tool_call in tool_calls:
            if tool_call.safety_level == ToolSafetyLevel.SAFE:
                safe_tools.append(tool_call)
            elif tool_call.safety_level == ToolSafetyLevel.CAUTIOUS:
                cautious_tools.append(tool_call)
            else:
                exclusive_tools.append(tool_call)
        
        # 1. 并行执行安全工具
        if safe_tools:
            async for result in self._execute_parallel_batch(safe_tools, session, monitor):
                yield result
        
        # 2. 限制并发执行谨慎工具
        if cautious_tools:
            semaphore = asyncio.Semaphore(2)  # 最多2个并发
            
            async def execute_with_semaphore(tool_call):
                async with semaphore:
                    return await self.execute_single_tool(tool_call, session.session_id, monitor)
            
            tasks = [execute_with_semaphore(tool_call) for tool_call in cautious_tools]
            
            for task in asyncio.as_completed(tasks):
                try:
                    result = await task
                    monitor.completed_tools += 1
                    yield result
                except Exception as e:
                    # 处理错误
                    pass
        
        # 3. 串行执行独占工具
        if exclusive_tools:
            async for result in self._execute_serial_batch(exclusive_tools, session, monitor):
                yield result
    
    async def _execute_tool_with_monitoring(self, tool: BaseTool,
                                          tool_call: ToolCall,
                                          monitor: Optional[ExecutionMonitor]) -> ToolResult:
        """带监控的工具执行"""
        
        start_time = time.time()
        
        try:
            # 设置超时
            timeout = tool_call.input_data.get("timeout", 30.0)
            
            # 执行工具
            result_data = await asyncio.wait_for(
                tool.execute(tool_call.input_data),
                timeout=timeout
            )
            
            execution_time = time.time() - start_time
            
            # 更新监控
            if monitor and monitor.progress_callback:
                monitor.progress_callback({
                    "tool_name": tool_call.tool_name,
                    "status": "completed",
                    "execution_time": execution_time
                })
            
            # 更新工具指标
            tool.update_metrics(execution_time, True)
            
            return ToolResult(
                tool_call=tool_call,
                result=result_data,
                execution_time=execution_time
            )
            
        except asyncio.TimeoutError:
            execution_time = time.time() - start_time
            tool.update_metrics(execution_time, False, "timeout")
            
            raise TimeoutError(f"Tool {tool_call.tool_name} execution timed out after {timeout}s")
        
        except Exception as e:
            execution_time = time.time() - start_time
            tool.update_metrics(execution_time, False, str(type(e).__name__))
            
            raise e
    
    @asynccontextmanager
    async def execution_context(self, session_id: Optional[str] = None):
        """执行上下文管理器"""
        
        if session_id is None:
            session_id = self._generate_session_id()
        
        session = self._get_or_create_session(session_id)
        
        try:
            yield session
        finally:
            # 清理所有活跃任务
            for task in session.active_tools.values():
                if not task.done():
                    task.cancel()
            
            # 等待所有任务结束
            if session.active_tools:
                await asyncio.gather(
                    *session.active_tools.values(),
                    return_exceptions=True
                )
            
            self._cleanup_session(session_id)
    
    async def cancel_execution(self, session_id: str, tool_call_id: Optional[str] = None):
        """取消执行"""
        
        session = self.active_sessions.get(session_id)
        if not session:
            return False
        
        if tool_call_id:
            # 取消特定工具
            task = session.active_tools.get(tool_call_id)
            if task and not task.done():
                task.cancel()
                del session.active_tools[tool_call_id]
                return True
        else:
            # 取消所有工具
            for task in session.active_tools.values():
                if not task.done():
                    task.cancel()
            session.active_tools.clear()
            return True
        
        return False
    
    def _get_or_create_session(self, session_id: str) -> ExecutionSession:
        """获取或创建执行会话"""
        
        if session_id not in self.active_sessions:
            self.active_sessions[session_id] = ExecutionSession(
                session_id=session_id,
                start_time=datetime.now()
            )
        
        return self.active_sessions[session_id]
    
    def _cleanup_session(self, session_id: str):
        """清理执行会话"""
        
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            
            # 移动到历史记录
            self.execution_history.append(session)
            
            # 限制历史记录大小
            if len(self.execution_history) > 100:
                self.execution_history = self.execution_history[-100:]
            
            # 从活跃会话中移除
            del self.active_sessions[session_id]
    
    def _generate_session_id(self) -> str:
        """生成会话ID"""
        return f"exec_{uuid.uuid4().hex[:8]}_{int(time.time())}"
    
    def _update_execution_stats(self, tool_name: str, execution_time: float, success: bool):
        """更新执行统计"""
        
        self.execution_stats["total_executions"] += 1
        
        if success:
            self.execution_stats["successful_executions"] += 1
        else:
            self.execution_stats["failed_executions"] += 1
        
        # 更新平均执行时间
        total_count = self.execution_stats["total_executions"]
        current_avg = self.execution_stats["average_execution_time"]
        
        self.execution_stats["average_execution_time"] = (
            (current_avg * (total_count - 1) + execution_time) / total_count
        )
        
        # 更新工具使用分布
        if tool_name not in self.execution_stats["tool_usage_distribution"]:
            self.execution_stats["tool_usage_distribution"][tool_name] = 0
        self.execution_stats["tool_usage_distribution"][tool_name] += 1
    
    async def _handle_timeout_error(self, error: Exception, tool_call: ToolCall, 
                                  session: ExecutionSession):
        """处理超时错误"""
        print(f"Tool {tool_call.tool_name} timed out: {error}")
    
    async def _handle_validation_error(self, error: Exception, tool_call: ToolCall,
                                     session: ExecutionSession):
        """处理验证错误"""
        print(f"Validation failed for tool {tool_call.tool_name}: {error}")
    
    async def _handle_execution_error(self, error: Exception, tool_call: ToolCall,
                                    session: ExecutionSession):
        """处理执行错误"""
        print(f"Execution failed for tool {tool_call.tool_name}: {error}")
    
    async def _handle_safety_error(self, error: Exception, tool_call: ToolCall,
                                 session: ExecutionSession):
        """处理安全错误"""
        print(f"Safety violation for tool {tool_call.tool_name}: {error}")
    
    def get_execution_statistics(self) -> Dict[str, Any]:
        """获取执行统计信息"""
        
        success_rate = (
            self.execution_stats["successful_executions"] / 
            self.execution_stats["total_executions"]
        ) if self.execution_stats["total_executions"] > 0 else 0
        
        return {
            "execution_stats": self.execution_stats,
            "success_rate": success_rate,
            "active_sessions": len(self.active_sessions),
            "active_tools": sum(len(session.active_tools) for session in self.active_sessions.values()),
            "session_history_size": len(self.execution_history)
        }
    
    def get_session_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话状态"""
        
        session = self.active_sessions.get(session_id)
        if not session:
            return None
        
        return {
            "session_id": session_id,
            "start_time": session.start_time.isoformat(),
            "total_tool_calls": len(session.tool_calls),
            "completed_results": len(session.results),
            "active_tools": list(session.active_tools.keys()),
            "session_metadata": session.session_metadata
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        
        try:
            # 检查基本状态
            active_sessions_count = len(self.active_sessions)
            total_active_tools = sum(
                len(session.active_tools) for session in self.active_sessions.values()
            )
            
            # 检查工具注册表
            registry_health = self.tool_registry.get_registry_statistics()
            
            # 计算健康分数
            health_score = 1.0
            
            # 活跃会话过多会降低健康分数
            if active_sessions_count > 10:
                health_score -= 0.2
            
            # 活跃工具过多会降低健康分数
            if total_active_tools > 20:
                health_score -= 0.3
            
            # 成功率低会降低健康分数
            success_rate = (
                self.execution_stats["successful_executions"] / 
                self.execution_stats["total_executions"]
            ) if self.execution_stats["total_executions"] > 0 else 1.0
            
            if success_rate < 0.8:
                health_score -= 0.3
            
            health_score = max(0.0, health_score)
            
            return {
                "status": "healthy" if health_score > 0.8 else "degraded" if health_score > 0.5 else "unhealthy",
                "health_score": health_score,
                "active_sessions": active_sessions_count,
                "active_tools": total_active_tools,
                "execution_stats": self.execution_stats,
                "registry_health": registry_health,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "health_score": 0.0,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }


class SecurityError(Exception):
    """安全错误"""
    pass