"""
统一执行上下文 - Loom 框架四大核心能力的协调中心

实现智能上下文在 TT 递归中组织复杂任务的能力
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, TYPE_CHECKING
from pathlib import Path
import time
import uuid

from loom.core.context_assembly import ContextAssembler, ComponentPriority
from loom.builtin.tools.task import TaskTool
from loom.core.events import EventProcessor, EventFilter, AgentEventType

# 避免循环导入
if TYPE_CHECKING:
    from loom.core.agent_executor import TaskHandler


@dataclass
class CoordinationConfig:
    """
    统一协调配置类 - 管理所有协调参数

    集中管理魔法数字，便于调优和测试
    """
    # 任务分析阈值
    deep_recursion_threshold: int = 3
    """深度递归阈值 - 超过此深度会调整上下文策略"""

    high_complexity_threshold: float = 0.7
    """高复杂度阈值 - 超过此值会启用子代理"""

    completion_score_threshold: float = 0.8
    """任务完成度阈值 - 超过此值认为可以完成任务"""

    # 缓存配置
    context_cache_size: int = 100
    """上下文组件缓存大小"""

    subagent_pool_size: int = 5
    """子代理池大小"""

    # 事件处理配置
    event_batch_size: int = 10
    """事件批处理大小"""

    event_batch_timeout: float = 0.05
    """事件批处理超时时间（秒）- 降低延迟"""

    # 性能目标
    max_execution_time: float = 30.0
    """最大执行时间（秒）"""

    max_token_usage: float = 0.8
    """最大 token 使用率"""

    min_cache_hit_rate: float = 0.6
    """最小缓存命中率"""

    max_subagent_count: int = 3
    """最大子代理数量"""


@dataclass
class UnifiedExecutionContext:
    """
    统一的执行上下文，协调四大核心能力

    实现目标：
    1. 智能上下文在 TT 递归中组织复杂任务
    2. 动态调整策略和资源分配
    3. 统一的状态管理和性能优化
    4. 跨组件的协调和通信
    """

    # 基础信息
    execution_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    correlation_id: Optional[str] = None
    working_dir: Optional[Path] = None

    # 协调配置
    config: CoordinationConfig = field(default_factory=CoordinationConfig)

    # 四大核心能力实例
    context_assembler: Optional[ContextAssembler] = None
    task_tool: Optional[TaskTool] = None
    event_processor: Optional[EventProcessor] = None
    task_handlers: List['TaskHandler'] = field(default_factory=list)

    # 统一状态管理
    execution_state: Dict[str, Any] = field(default_factory=dict)
    performance_metrics: Dict[str, Any] = field(default_factory=dict)

    # 运行时状态已移除 - 这些字段应该在 IntelligentCoordinator 中管理


class IntelligentCoordinator:
    """
    智能协调器 - 统一管理四大核心能力
    
    核心功能：
    1. 协调 ContextAssembler 与 TT 递归的集成
    2. 管理 TaskTool 的子代理执行策略
    3. 优化 EventProcessor 的事件处理
    4. 动态调整 TaskHandler 的处理策略
    """
    
    def __init__(self, context: UnifiedExecutionContext):
        self.context = context
        self.config = context.config
        
        # 运行时状态
        self.current_task_type: Optional[str] = None
        self.task_complexity_score: float = 0.0
        self.recursion_context: Dict[str, Any] = {}  # 快捷访问配置
        self._strategy_history: List[Dict[str, Any]] = []
    
    # 移除魔法属性注入方法 - 改为直接在协调器内部处理
    
    def coordinate_tt_recursion(self, 
                               messages: List,
                               turn_state,
                               context) -> List:
        """协调 TT 递归执行"""
        
        # 1. 分析任务类型和复杂度
        self._analyze_task_context(messages, turn_state)
        
        # 2. 智能上下文组装
        assembled_context = self._intelligent_context_assembly(
            messages, turn_state
        )
        
        # 3. 动态任务处理策略
        task_strategy = self._determine_task_strategy(messages, turn_state)
        
        # 4. 协调执行计划
        execution_plan = self._create_execution_plan(
            assembled_context, task_strategy
        )
        
        return execution_plan
    
    def _analyze_task_context(self, messages: List, turn_state):
        """分析任务上下文"""
        if not messages:
            return
        
        # 分析任务类型
        task_content = messages[0].content if messages else ""
        self.current_task_type = self._classify_task_type(task_content)
        
        # 计算任务复杂度
        self.task_complexity_score = self._calculate_task_complexity(
            task_content, turn_state
        )
        
        # 更新递归上下文
        self.recursion_context.update({
            "turn_counter": turn_state.turn_counter,
            "max_iterations": turn_state.max_iterations,
            "task_type": self.current_task_type,
            "complexity": self.task_complexity_score
        })
    
    def _classify_task_type(self, task_content: str) -> str:
        """分类任务类型"""
        task_lower = task_content.lower()
        
        if any(keyword in task_lower for keyword in ["analyze", "analysis", "分析"]):
            return "analysis"
        elif any(keyword in task_lower for keyword in ["generate", "create", "生成", "创建"]):
            return "generation"
        elif any(keyword in task_lower for keyword in ["sql", "query", "查询"]):
            return "sql"
        elif any(keyword in task_lower for keyword in ["test", "testing", "测试"]):
            return "testing"
        elif any(keyword in task_lower for keyword in ["report", "报告"]):
            return "reporting"
        else:
            return "general"
    
    def _calculate_task_complexity(self, task_content: str, turn_state) -> float:
        """计算任务复杂度"""
        complexity = 0.0
        
        # 基于内容长度
        complexity += min(len(task_content) / 1000, 0.3)
        
        # 基于关键词数量
        complex_keywords = ["complex", "multiple", "several", "various", 
                           "复杂", "多个", "各种", "多种"]
        keyword_count = sum(1 for kw in complex_keywords if kw in task_content.lower())
        complexity += min(keyword_count * 0.1, 0.3)
        
        # 基于递归深度
        recursion_factor = turn_state.turn_counter / turn_state.max_iterations
        complexity += recursion_factor * 0.4
        
        return min(complexity, 1.0)
    
    def _intelligent_context_assembly(self, messages: List, turn_state) -> str:
        """智能上下文组装"""
        if not self.context.context_assembler:
            return ""

        assembler = self.context.context_assembler

        # 基于任务类型调整策略
        task_type = self.current_task_type
        complexity = self.task_complexity_score

        if task_type == "analysis" and complexity > self.config.high_complexity_threshold:
            # 复杂分析任务需要更多示例和指导
            assembler.adjust_priority("examples", ComponentPriority.MEDIUM)
            assembler.adjust_priority("analysis_guidelines", ComponentPriority.HIGH)

        elif task_type == "sql" and complexity > 0.5:
            # SQL 任务需要表结构和查询示例
            assembler.adjust_priority("schema_info", ComponentPriority.HIGH)
            assembler.adjust_priority("query_examples", ComponentPriority.MEDIUM)

        # 基于递归深度调整优先级
        recursion_depth = turn_state.turn_counter
        if recursion_depth > self.config.deep_recursion_threshold:
            # 深度递归时，优先保留核心指令
            assembler.adjust_priority("base_instructions", ComponentPriority.CRITICAL)
            assembler.adjust_priority("tool_definitions", ComponentPriority.HIGH)

            # 降低示例优先级以节省空间
            assembler.adjust_priority("examples", ComponentPriority.LOW)

        return assembler.assemble()
    
    def _determine_task_strategy(self, messages: List, turn_state) -> Dict[str, Any]:
        """确定任务处理策略"""
        strategy = {
            "use_sub_agents": False,
            "parallel_execution": False,
            "context_priority": "balanced",
            "event_batching": True,
            "subagent_types": [],
            "context_focus": []
        }

        task_type = self.current_task_type
        complexity = self.task_complexity_score

        # 基于任务复杂度决定是否使用子代理
        if complexity > self.config.high_complexity_threshold:
            strategy["use_sub_agents"] = True
            strategy["parallel_execution"] = True

            # 根据任务类型选择子代理类型
            if task_type == "analysis":
                strategy["subagent_types"] = ["code-analyzer", "quality-checker"]
            elif task_type == "sql":
                strategy["subagent_types"] = ["sql-expert", "data-analyzer"]
            elif task_type == "reporting":
                strategy["subagent_types"] = ["report-writer", "data-processor"]

        # 基于递归深度调整策略
        if turn_state.turn_counter > self.config.deep_recursion_threshold:
            strategy["context_priority"] = "minimal"
            strategy["event_batching"] = True
            strategy["context_focus"] = ["base_instructions", "tool_definitions"]

        return strategy
    
    def _create_execution_plan(self,
                              assembled_context: str,
                              task_strategy: Dict[str, Any]) -> Dict[str, Any]:
        """创建执行计划"""
        return {
            "context": assembled_context,
            "strategy": task_strategy,
            "coordinator_config": {
                "task_type": self.current_task_type,
                "complexity": self.task_complexity_score,
                "recursion_context": self.recursion_context
            },
            "performance_targets": self._get_performance_targets(task_strategy)
        }

    def _get_performance_targets(self, strategy: Dict[str, Any]) -> Dict[str, Any]:
        """获取性能目标"""
        targets = {
            "max_execution_time": self.config.max_execution_time,
            "max_token_usage": self.config.max_token_usage,
            "min_cache_hit_rate": self.config.min_cache_hit_rate,
            "max_subagent_count": self.config.max_subagent_count
        }

        if strategy["use_sub_agents"]:
            targets["max_execution_time"] = self.config.max_execution_time * 2
            targets["max_subagent_count"] = len(strategy["subagent_types"])

        return targets
    
    
    def get_unified_metrics(self) -> Dict[str, Any]:
        """获取统一的性能指标"""
        metrics = {
            "execution_id": self.context.execution_id,
            "timestamp": time.time(),
            "task_analysis": {
                "task_type": self.current_task_type,
                "complexity_score": self.task_complexity_score,
                "recursion_context": self.recursion_context
            }
        }

        # 收集各组件指标
        if self.context.context_assembler:
            metrics["context_assembler"] = self.context.context_assembler.get_component_stats()

        if self.context.task_tool:
            metrics["task_tool"] = self.context.task_tool.get_pool_stats()

        if self.context.event_processor:
            metrics["event_processor"] = self.context.event_processor.get_stats()

        return metrics
    
    def adjust_strategy_based_on_performance(self,
                                           current_metrics: Dict[str, Any]):
        """基于性能指标动态调整策略"""

        # 分析性能瓶颈
        bottlenecks = self._identify_bottlenecks(current_metrics)

        adjustments_made = []

        for bottleneck in bottlenecks:
            if bottleneck == "context_assembly_slow":
                # 调整上下文组装策略
                if self.context.context_assembler:
                    self.context.context_assembler.enable_caching = True
                    self.context.context_assembler._cache_size = self.config.context_cache_size * 2
                    adjustments_made.append("增加上下文缓存大小")

            elif bottleneck == "sub_agent_creation_overhead":
                # 调整子代理池策略
                if self.context.task_tool:
                    self.context.task_tool.pool_size = self.config.subagent_pool_size * 2
                    self.context.task_tool.enable_pooling = True
                    adjustments_made.append("增加子代理池大小")

            elif bottleneck == "event_processing_latency":
                # 调整事件处理策略
                if self.context.event_processor:
                    for filter_obj in self.context.event_processor.filters:
                        filter_obj.batch_size = self.config.event_batch_size * 2
                        filter_obj.batch_timeout = self.config.event_batch_timeout / 2
                    adjustments_made.append("优化事件处理批量设置")

        # 记录策略调整历史
        self._strategy_history.append({
            "timestamp": time.time(),
            "bottlenecks": bottlenecks,
            "adjustments": adjustments_made
        })
    
    def _identify_bottlenecks(self, metrics: Dict[str, Any]) -> List[str]:
        """识别性能瓶颈"""
        bottlenecks = []
        
        # 检查上下文组装性能
        if "context_assembler" in metrics:
            ca_metrics = metrics["context_assembler"]
            if ca_metrics.get("budget_utilization", 0) > 0.9:
                bottlenecks.append("context_assembly_slow")
        
        # 检查子代理性能
        if "task_tool" in metrics:
            tt_metrics = metrics["task_tool"]
            if tt_metrics.get("cache_hit_rate", 0) < 0.3:
                bottlenecks.append("sub_agent_creation_overhead")
        
        # 检查事件处理性能
        if "event_processor" in metrics:
            ep_metrics = metrics["event_processor"]
            if ep_metrics.get("average_processing_time", 0) > 0.1:
                bottlenecks.append("event_processing_latency")
        
        return bottlenecks
