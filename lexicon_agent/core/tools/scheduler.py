"""
智能工具调度器

实现智能工具选择、执行顺序优化和资源管理，
类似Claude Code的工具调度机制
"""

import asyncio
import time
from typing import Dict, Any, List, Optional, AsyncIterator, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from ...types import ToolCall, ToolResult, ToolSafetyLevel, ManagedContext
from .registry import ToolRegistry, BaseTool


class ExecutionStrategy(Enum):
    """执行策略"""
    SERIAL = "serial"  # 串行执行
    PARALLEL = "parallel"  # 并行执行
    SMART_PARALLEL = "smart_parallel"  # 智能并行
    PIPELINE = "pipeline"  # 流水线
    ADAPTIVE = "adaptive"  # 自适应


@dataclass
class ToolExecutionPlan:
    """工具执行计划"""
    tool_calls: List[ToolCall]
    execution_groups: List[List[ToolCall]] = field(default_factory=list)
    dependencies: Dict[str, List[str]] = field(default_factory=dict)
    estimated_duration: float = 0.0
    strategy: ExecutionStrategy = ExecutionStrategy.ADAPTIVE
    resource_requirements: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionContext:
    """执行上下文"""
    managed_context: ManagedContext
    session_constraints: Dict[str, Any] = field(default_factory=dict)
    available_resources: Dict[str, Any] = field(default_factory=dict)
    execution_history: List[ToolResult] = field(default_factory=list)


@dataclass
class ResourcePool:
    """资源池"""
    max_concurrent_tools: int = 5
    max_memory_mb: int = 1024
    max_cpu_percent: float = 80.0
    exclusive_lock: bool = False
    
    # 当前使用情况
    active_tools: Set[str] = field(default_factory=set)
    current_memory_mb: float = 0.0
    current_cpu_percent: float = 0.0


class DependencyAnalyzer:
    """依赖分析器"""
    
    def __init__(self):
        self.dependency_graph: Dict[str, Set[str]] = {}
        self.reverse_dependencies: Dict[str, Set[str]] = {}
    
    def analyze_dependencies(self, tool_calls: List[ToolCall], 
                           context: ExecutionContext) -> Dict[str, List[str]]:
        """分析工具调用之间的依赖关系"""
        
        dependencies = {}
        
        # 简化的依赖分析逻辑
        for i, call in enumerate(tool_calls):
            call_dependencies = []
            
            # 1. 数据依赖：后续工具可能需要前面工具的输出
            for j in range(i):
                prev_call = tool_calls[j]
                if self._has_data_dependency(prev_call, call):
                    call_dependencies.append(prev_call.call_id)
            
            # 2. 资源依赖：独占工具需要等待其他工具完成
            if call.safety_level == ToolSafetyLevel.EXCLUSIVE:
                for j in range(i):
                    prev_call = tool_calls[j]
                    if prev_call.call_id not in call_dependencies:
                        call_dependencies.append(prev_call.call_id)
            
            # 3. 安全依赖：某些工具组合不能并行执行
            for j in range(i):
                prev_call = tool_calls[j]
                if self._has_safety_conflict(prev_call, call):
                    if prev_call.call_id not in call_dependencies:
                        call_dependencies.append(prev_call.call_id)
            
            dependencies[call.call_id] = call_dependencies
        
        return dependencies
    
    def _has_data_dependency(self, producer: ToolCall, consumer: ToolCall) -> bool:
        """检查数据依赖"""
        
        # 简化的数据依赖检测
        data_flow_patterns = [
            ("file_system", "code_interpreter"),  # 文件 -> 代码执行
            ("web_search", "knowledge_base"),     # 搜索 -> 知识存储
            ("knowledge_base", "code_interpreter") # 知识检索 -> 代码生成
        ]
        
        return (producer.tool_name, consumer.tool_name) in data_flow_patterns
    
    def _has_safety_conflict(self, tool1: ToolCall, tool2: ToolCall) -> bool:
        """检查安全冲突"""
        
        # 独占工具与其他工具冲突
        if (tool1.safety_level == ToolSafetyLevel.EXCLUSIVE or 
            tool2.safety_level == ToolSafetyLevel.EXCLUSIVE):
            return True
        
        # 特定工具组合冲突
        conflict_pairs = [
            ("file_system", "file_system"),  # 文件操作可能冲突
        ]
        
        return (tool1.tool_name, tool2.tool_name) in conflict_pairs
    
    def topological_sort(self, dependencies: Dict[str, List[str]]) -> List[List[str]]:
        """拓扑排序，返回执行层次"""
        
        # 构建入度图
        in_degree = {call_id: 0 for call_id in dependencies.keys()}
        for call_id, deps in dependencies.items():
            in_degree[call_id] = len(deps)
        
        # 层次化拓扑排序
        execution_levels = []
        remaining_calls = set(dependencies.keys())
        
        while remaining_calls:
            # 找到入度为0的节点（当前可执行的工具）
            current_level = [
                call_id for call_id in remaining_calls 
                if in_degree[call_id] == 0
            ]
            
            if not current_level:
                # 检测到循环依赖
                break
            
            execution_levels.append(current_level)
            
            # 移除当前层次的节点并更新入度
            for call_id in current_level:
                remaining_calls.remove(call_id)
                
                # 更新依赖此节点的其他节点的入度
                for other_id, deps in dependencies.items():
                    if call_id in deps:
                        in_degree[other_id] -= 1
        
        return execution_levels


class PerformanceOptimizer:
    """性能优化器"""
    
    def __init__(self):
        self.execution_history: List[Dict[str, Any]] = []
        self.tool_performance_cache: Dict[str, Dict[str, float]] = {}
    
    def optimize_execution_order(self, tool_calls: List[ToolCall],
                                dependencies: Dict[str, List[str]]) -> List[ToolCall]:
        """优化执行顺序"""
        
        # 基于历史性能数据重新排序
        scored_calls = []
        
        for call in tool_calls:
            # 计算工具调用的优先级分数
            score = self._calculate_priority_score(call)
            scored_calls.append((call, score))
        
        # 在满足依赖关系的前提下，按分数排序
        optimized_calls = self._sort_with_dependencies(scored_calls, dependencies)
        
        return optimized_calls
    
    def _calculate_priority_score(self, tool_call: ToolCall) -> float:
        """计算工具调用优先级分数"""
        
        score = 0.0
        
        # 1. 基于历史执行时间（快的工具优先）
        performance = self.tool_performance_cache.get(tool_call.tool_name, {})
        avg_time = performance.get("average_execution_time", 1.0)
        time_score = 1.0 / (avg_time + 0.1)  # 避免除零
        score += time_score * 0.4
        
        # 2. 基于成功率（可靠的工具优先）
        success_rate = performance.get("success_rate", 0.5)
        score += success_rate * 0.3
        
        # 3. 基于安全级别（安全的工具可以早执行）
        if tool_call.safety_level == ToolSafetyLevel.SAFE:
            score += 0.3
        elif tool_call.safety_level == ToolSafetyLevel.CAUTIOUS:
            score += 0.2
        else:  # EXCLUSIVE
            score += 0.1
        
        return score
    
    def _sort_with_dependencies(self, scored_calls: List[Tuple[ToolCall, float]],
                               dependencies: Dict[str, List[str]]) -> List[ToolCall]:
        """在满足依赖的前提下排序"""
        
        # 简化实现：按依赖层次内部排序
        dependency_analyzer = DependencyAnalyzer()
        execution_levels = dependency_analyzer.topological_sort(dependencies)
        
        optimized_order = []
        call_by_id = {call.call_id: call for call, score in scored_calls}
        score_by_id = {call.call_id: score for call, score in scored_calls}
        
        for level in execution_levels:
            # 在每个层次内按分数排序
            level_calls = [(call_by_id[call_id], score_by_id[call_id]) for call_id in level]
            level_calls.sort(key=lambda x: x[1], reverse=True)
            
            optimized_order.extend([call for call, score in level_calls])
        
        return optimized_order
    
    def update_performance_data(self, tool_name: str, execution_time: float, 
                               success: bool):
        """更新性能数据"""
        
        if tool_name not in self.tool_performance_cache:
            self.tool_performance_cache[tool_name] = {
                "total_executions": 0,
                "total_time": 0.0,
                "successful_executions": 0
            }
        
        cache = self.tool_performance_cache[tool_name]
        cache["total_executions"] += 1
        cache["total_time"] += execution_time
        
        if success:
            cache["successful_executions"] += 1
        
        # 计算平均值
        cache["average_execution_time"] = cache["total_time"] / cache["total_executions"]
        cache["success_rate"] = cache["successful_executions"] / cache["total_executions"]


class IntelligentToolScheduler:
    """智能工具调度器"""
    
    def __init__(self, tool_registry: ToolRegistry):
        self.tool_registry = tool_registry
        self.dependency_analyzer = DependencyAnalyzer()
        self.performance_optimizer = PerformanceOptimizer()
        self.resource_pool = ResourcePool()
        
        # 调度统计
        self.scheduling_stats = {
            "total_executions": 0,
            "strategy_usage": {},
            "average_planning_time": 0.0,
            "optimization_success_rate": 0.0
        }
    
    async def schedule_tools(self, tool_calls: List[ToolCall],
                           context: ExecutionContext,
                           strategy: ExecutionStrategy = ExecutionStrategy.ADAPTIVE) -> ToolExecutionPlan:
        """调度工具执行"""
        
        start_time = time.time()
        
        try:
            # 1. 分析依赖关系
            dependencies = self.dependency_analyzer.analyze_dependencies(tool_calls, context)
            
            # 2. 性能优化
            optimized_calls = self.performance_optimizer.optimize_execution_order(
                tool_calls, dependencies
            )
            
            # 3. 确定执行策略
            final_strategy = self._determine_execution_strategy(
                optimized_calls, dependencies, strategy
            )
            
            # 4. 创建执行分组
            execution_groups = self._create_execution_groups(
                optimized_calls, dependencies, final_strategy
            )
            
            # 5. 估算执行时间
            estimated_duration = self._estimate_execution_duration(
                optimized_calls, final_strategy
            )
            
            # 6. 评估资源需求
            resource_requirements = self._assess_resource_requirements(optimized_calls)
            
            planning_time = time.time() - start_time
            self._update_scheduling_stats(final_strategy, planning_time, True)
            
            return ToolExecutionPlan(
                tool_calls=optimized_calls,
                execution_groups=execution_groups,
                dependencies=dependencies,
                estimated_duration=estimated_duration,
                strategy=final_strategy,
                resource_requirements=resource_requirements
            )
            
        except Exception as e:
            planning_time = time.time() - start_time
            self._update_scheduling_stats(strategy, planning_time, False)
            raise e
    
    def _determine_execution_strategy(self, tool_calls: List[ToolCall],
                                    dependencies: Dict[str, List[str]],
                                    preferred_strategy: ExecutionStrategy) -> ExecutionStrategy:
        """确定最佳执行策略"""
        
        if preferred_strategy != ExecutionStrategy.ADAPTIVE:
            return preferred_strategy
        
        # 自适应策略选择
        call_count = len(tool_calls)
        has_dependencies = any(deps for deps in dependencies.values())
        has_exclusive_tools = any(
            call.safety_level == ToolSafetyLevel.EXCLUSIVE for call in tool_calls
        )
        
        # 策略选择逻辑
        if has_exclusive_tools:
            return ExecutionStrategy.SERIAL
        elif has_dependencies and call_count > 3:
            return ExecutionStrategy.PIPELINE
        elif call_count > 2 and not has_dependencies:
            return ExecutionStrategy.PARALLEL
        elif call_count > 1:
            return ExecutionStrategy.SMART_PARALLEL
        else:
            return ExecutionStrategy.SERIAL
    
    def _create_execution_groups(self, tool_calls: List[ToolCall],
                               dependencies: Dict[str, List[str]],
                               strategy: ExecutionStrategy) -> List[List[ToolCall]]:
        """创建执行分组"""
        
        if strategy == ExecutionStrategy.SERIAL:
            # 串行执行：每个工具一组
            return [[call] for call in tool_calls]
        
        elif strategy == ExecutionStrategy.PARALLEL:
            # 并行执行：所有工具一组
            return [tool_calls]
        
        elif strategy in (ExecutionStrategy.SMART_PARALLEL, ExecutionStrategy.PIPELINE):
            # 智能并行/流水线：基于依赖关系分组
            execution_levels = self.dependency_analyzer.topological_sort(dependencies)
            
            groups = []
            call_by_id = {call.call_id: call for call in tool_calls}
            
            for level in execution_levels:
                level_calls = [call_by_id[call_id] for call_id in level if call_id in call_by_id]
                if level_calls:
                    groups.append(level_calls)
            
            return groups
        
        else:  # ADAPTIVE - fallback to smart parallel
            return self._create_execution_groups(
                tool_calls, dependencies, ExecutionStrategy.SMART_PARALLEL
            )
    
    def _estimate_execution_duration(self, tool_calls: List[ToolCall],
                                   strategy: ExecutionStrategy) -> float:
        """估算执行时间"""
        
        total_duration = 0.0
        
        for call in tool_calls:
            # 从注册表获取工具定义
            definition = self.tool_registry.get_tool_definition(call.tool_name)
            if definition:
                estimated_time = definition.average_execution_time or 1.0
            else:
                estimated_time = 1.0  # 默认估算
            
            if strategy == ExecutionStrategy.SERIAL:
                total_duration += estimated_time
            elif strategy == ExecutionStrategy.PARALLEL:
                total_duration = max(total_duration, estimated_time)
            else:
                # 智能并行等策略的复杂估算
                total_duration += estimated_time * 0.7  # 考虑部分并行
        
        return total_duration
    
    def _assess_resource_requirements(self, tool_calls: List[ToolCall]) -> Dict[str, Any]:
        """评估资源需求"""
        
        max_concurrent = 0
        total_memory = 0.0
        max_cpu = 0.0
        
        for call in tool_calls:
            # 简化的资源需求评估
            if call.tool_name == "code_interpreter":
                total_memory += 256  # MB
                max_cpu = max(max_cpu, 50.0)  # %
            elif call.tool_name == "file_system":
                total_memory += 64
                max_cpu = max(max_cpu, 20.0)
            else:
                total_memory += 32
                max_cpu = max(max_cpu, 10.0)
            
            max_concurrent += 1
        
        return {
            "max_concurrent_tools": max_concurrent,
            "estimated_memory_mb": total_memory,
            "estimated_cpu_percent": max_cpu,
            "requires_exclusive_access": any(
                call.safety_level == ToolSafetyLevel.EXCLUSIVE for call in tool_calls
            )
        }
    
    async def execute_plan(self, plan: ToolExecutionPlan,
                          context: ExecutionContext) -> AsyncIterator[ToolResult]:
        """执行工具调度计划"""
        
        execution_start = time.time()
        
        try:
            # 检查资源可用性
            if not self._check_resource_availability(plan.resource_requirements):
                raise RuntimeError("Insufficient resources for execution")
            
            # 按分组执行
            for group_index, execution_group in enumerate(plan.execution_groups):
                
                # 并行执行组内工具
                if len(execution_group) > 1:
                    async for result in self._execute_parallel_group(execution_group, context):
                        yield result
                else:
                    # 单工具执行
                    async for result in self._execute_single_tool(execution_group[0], context):
                        yield result
                
                # 组间同步点
                if group_index < len(plan.execution_groups) - 1:
                    await asyncio.sleep(0.01)  # 短暂等待，确保顺序
            
            execution_time = time.time() - execution_start
            self._record_execution_metrics(plan, execution_time, True)
            
        except Exception as e:
            execution_time = time.time() - execution_start
            self._record_execution_metrics(plan, execution_time, False)
            raise e
    
    async def _execute_parallel_group(self, tool_calls: List[ToolCall],
                                    context: ExecutionContext) -> AsyncIterator[ToolResult]:
        """并行执行工具组"""
        
        # 创建并行任务
        tasks = [
            self._execute_single_tool_task(call, context)
            for call in tool_calls
        ]
        
        # 等待所有任务完成
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 产出结果
        for result in results:
            if isinstance(result, Exception):
                # 创建错误结果
                yield ToolResult(
                    tool_call=tool_calls[0],  # 简化处理
                    error=result
                )
            else:
                yield result
    
    async def _execute_single_tool(self, tool_call: ToolCall,
                                 context: ExecutionContext) -> AsyncIterator[ToolResult]:
        """执行单个工具"""
        
        result = await self._execute_single_tool_task(tool_call, context)
        yield result
    
    async def _execute_single_tool_task(self, tool_call: ToolCall,
                                      context: ExecutionContext) -> ToolResult:
        """执行单个工具的任务"""
        
        start_time = time.time()
        
        try:
            # 获取工具实例
            tool = self.tool_registry.get_tool(tool_call.tool_name)
            if not tool:
                raise ValueError(f"Tool {tool_call.tool_name} not found")
            
            # 验证输入
            if not await tool.validate_input(tool_call.input_data):
                raise ValueError(f"Invalid input for tool {tool_call.tool_name}")
            
            # 执行工具
            result_data = await tool.execute(tool_call.input_data)
            
            execution_time = time.time() - start_time
            
            # 更新性能数据
            tool.update_metrics(execution_time, True)
            self.performance_optimizer.update_performance_data(
                tool_call.tool_name, execution_time, True
            )
            
            return ToolResult(
                tool_call=tool_call,
                result=result_data,
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            # 更新错误指标
            tool = self.tool_registry.get_tool(tool_call.tool_name)
            if tool:
                tool.update_metrics(execution_time, False, str(type(e).__name__))
            
            self.performance_optimizer.update_performance_data(
                tool_call.tool_name, execution_time, False
            )
            
            return ToolResult(
                tool_call=tool_call,
                error=e,
                execution_time=execution_time
            )
    
    def _check_resource_availability(self, requirements: Dict[str, Any]) -> bool:
        """检查资源可用性"""
        
        required_memory = requirements.get("estimated_memory_mb", 0)
        required_cpu = requirements.get("estimated_cpu_percent", 0)
        requires_exclusive = requirements.get("requires_exclusive_access", False)
        
        # 检查内存
        if (self.resource_pool.current_memory_mb + required_memory > 
            self.resource_pool.max_memory_mb):
            return False
        
        # 检查CPU
        if (self.resource_pool.current_cpu_percent + required_cpu > 
            self.resource_pool.max_cpu_percent):
            return False
        
        # 检查独占访问
        if requires_exclusive and self.resource_pool.active_tools:
            return False
        
        if self.resource_pool.exclusive_lock:
            return False
        
        return True
    
    def _update_scheduling_stats(self, strategy: ExecutionStrategy, 
                               planning_time: float, success: bool):
        """更新调度统计"""
        
        self.scheduling_stats["total_executions"] += 1
        
        # 更新策略使用统计
        strategy_name = strategy.value
        if strategy_name not in self.scheduling_stats["strategy_usage"]:
            self.scheduling_stats["strategy_usage"][strategy_name] = 0
        self.scheduling_stats["strategy_usage"][strategy_name] += 1
        
        # 更新平均规划时间
        total_count = self.scheduling_stats["total_executions"]
        current_avg = self.scheduling_stats["average_planning_time"]
        
        self.scheduling_stats["average_planning_time"] = (
            (current_avg * (total_count - 1) + planning_time) / total_count
        )
        
        # 更新优化成功率（简化）
        if success:
            current_rate = self.scheduling_stats["optimization_success_rate"]
            self.scheduling_stats["optimization_success_rate"] = (
                (current_rate * (total_count - 1) + 1.0) / total_count
            )
    
    def _record_execution_metrics(self, plan: ToolExecutionPlan, 
                                execution_time: float, success: bool):
        """记录执行指标"""
        
        # 简化的指标记录
        metrics = {
            "plan_strategy": plan.strategy.value,
            "estimated_duration": plan.estimated_duration,
            "actual_duration": execution_time,
            "tools_count": len(plan.tool_calls),
            "groups_count": len(plan.execution_groups),
            "success": success,
            "timestamp": datetime.now().isoformat()
        }
        
        # 可以将指标存储到数据库或日志系统
        print(f"Execution metrics: {metrics}")
    
    def get_scheduling_statistics(self) -> Dict[str, Any]:
        """获取调度统计信息"""
        
        return {
            "scheduling_stats": self.scheduling_stats,
            "performance_cache": self.performance_optimizer.tool_performance_cache,
            "resource_pool_status": {
                "max_concurrent_tools": self.resource_pool.max_concurrent_tools,
                "active_tools": list(self.resource_pool.active_tools),
                "current_memory_mb": self.resource_pool.current_memory_mb,
                "current_cpu_percent": self.resource_pool.current_cpu_percent,
                "exclusive_lock": self.resource_pool.exclusive_lock
            }
        }
    
    async def optimize_for_context(self, context: ExecutionContext) -> Dict[str, Any]:
        """根据上下文优化调度器设置"""
        
        # 分析上下文约束
        session_constraints = context.session_constraints
        
        # 调整资源池设置
        if "memory_limit_mb" in session_constraints:
            self.resource_pool.max_memory_mb = min(
                self.resource_pool.max_memory_mb,
                session_constraints["memory_limit_mb"]
            )
        
        if "cpu_limit_percent" in session_constraints:
            self.resource_pool.max_cpu_percent = min(
                self.resource_pool.max_cpu_percent,
                session_constraints["cpu_limit_percent"]
            )
        
        if "max_concurrent_tools" in session_constraints:
            self.resource_pool.max_concurrent_tools = min(
                self.resource_pool.max_concurrent_tools,
                session_constraints["max_concurrent_tools"]
            )
        
        return {
            "optimization_applied": True,
            "adjusted_limits": {
                "memory_mb": self.resource_pool.max_memory_mb,
                "cpu_percent": self.resource_pool.max_cpu_percent,
                "concurrent_tools": self.resource_pool.max_concurrent_tools
            },
            "context_constraints": session_constraints
        }