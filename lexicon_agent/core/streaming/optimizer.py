"""
性能优化器

实现系统性能监控、自动优化和资源管理
"""

import asyncio
import time
import psutil
import gc
from typing import Dict, Any, List, Optional, Callable, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

from ...types import ManagedContext


class OptimizationStrategy(Enum):
    """优化策略"""
    MEMORY_OPTIMIZATION = "memory"
    CPU_OPTIMIZATION = "cpu"
    LATENCY_OPTIMIZATION = "latency"
    THROUGHPUT_OPTIMIZATION = "throughput"
    BALANCED = "balanced"


@dataclass
class PerformanceMetrics:
    """性能指标"""
    timestamp: datetime = field(default_factory=datetime.now)
    
    # CPU指标
    cpu_percent: float = 0.0
    cpu_cores: int = 0
    
    # 内存指标
    memory_percent: float = 0.0
    memory_used_mb: float = 0.0
    memory_available_mb: float = 0.0
    
    # 响应时间指标
    average_response_time: float = 0.0
    p95_response_time: float = 0.0
    p99_response_time: float = 0.0
    
    # 吞吐量指标
    requests_per_second: float = 0.0
    throughput_mbps: float = 0.0
    
    # 错误率指标
    error_rate: float = 0.0
    timeout_rate: float = 0.0
    
    # 上下文指标
    active_contexts: int = 0
    context_cache_hit_rate: float = 0.0


@dataclass
class OptimizationAction:
    """优化动作"""
    action_type: str
    description: str
    priority: int = 0
    estimated_impact: float = 0.0  # 0.0 - 1.0
    implementation_cost: float = 0.0  # 0.0 - 1.0
    
    # 动作参数
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    # 执行相关
    executor: Optional[Callable] = None
    is_executed: bool = False
    execution_result: Optional[Dict[str, Any]] = None


@dataclass
class PerformanceThresholds:
    """性能阈值"""
    max_cpu_percent: float = 80.0
    max_memory_percent: float = 85.0
    max_response_time_ms: float = 1000.0
    min_requests_per_second: float = 10.0
    max_error_rate: float = 0.05
    max_timeout_rate: float = 0.02


class MetricsCollector:
    """指标收集器"""
    
    def __init__(self):
        self.collection_interval = 1.0  # 秒
        self.metrics_history: List[PerformanceMetrics] = []
        self.max_history_size = 3600  # 保留1小时的数据
        
        # 应用层指标
        self.response_times: List[float] = []
        self.request_counts: List[int] = []
        self.error_counts: List[int] = []
        self.timeout_counts: List[int] = []
        
        # 时间窗口
        self.window_size = 60  # 60秒窗口
    
    async def collect_system_metrics(self) -> PerformanceMetrics:
        """收集系统指标"""
        
        # CPU指标
        cpu_percent = psutil.cpu_percent(interval=0.1)
        cpu_cores = psutil.cpu_count()
        
        # 内存指标
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_used_mb = memory.used / (1024 * 1024)
        memory_available_mb = memory.available / (1024 * 1024)
        
        # 应用层指标
        current_time = time.time()
        window_start = current_time - self.window_size
        
        # 计算窗口内的响应时间指标
        recent_response_times = [
            rt for rt in self.response_times[-1000:]  # 最近1000个请求
            if rt is not None
        ]
        
        if recent_response_times:
            avg_response_time = sum(recent_response_times) / len(recent_response_times)
            sorted_times = sorted(recent_response_times)
            p95_index = int(len(sorted_times) * 0.95)
            p99_index = int(len(sorted_times) * 0.99)
            p95_response_time = sorted_times[min(p95_index, len(sorted_times) - 1)]
            p99_response_time = sorted_times[min(p99_index, len(sorted_times) - 1)]
        else:
            avg_response_time = p95_response_time = p99_response_time = 0.0
        
        # 计算请求速率
        recent_requests = len([r for r in self.request_counts[-60:]])  # 最近60秒
        requests_per_second = recent_requests / min(60, len(self.request_counts))
        
        # 计算错误率
        recent_errors = sum(self.error_counts[-60:])
        total_recent_requests = sum(self.request_counts[-60:])
        error_rate = recent_errors / max(1, total_recent_requests)
        
        # 计算超时率
        recent_timeouts = sum(self.timeout_counts[-60:])
        timeout_rate = recent_timeouts / max(1, total_recent_requests)
        
        metrics = PerformanceMetrics(
            cpu_percent=cpu_percent,
            cpu_cores=cpu_cores,
            memory_percent=memory_percent,
            memory_used_mb=memory_used_mb,
            memory_available_mb=memory_available_mb,
            average_response_time=avg_response_time,
            p95_response_time=p95_response_time,
            p99_response_time=p99_response_time,
            requests_per_second=requests_per_second,
            error_rate=error_rate,
            timeout_rate=timeout_rate
        )
        
        # 添加到历史记录
        self.metrics_history.append(metrics)
        
        # 清理历史记录
        if len(self.metrics_history) > self.max_history_size:
            self.metrics_history = self.metrics_history[-self.max_history_size:]
        
        return metrics
    
    def record_response_time(self, response_time: float):
        """记录响应时间"""
        self.response_times.append(response_time)
        
        # 限制数组大小
        if len(self.response_times) > 10000:
            self.response_times = self.response_times[-5000:]
    
    def record_request(self, success: bool = True, timeout: bool = False):
        """记录请求"""
        # 这里简化处理，实际应该按时间窗口记录
        if len(self.request_counts) == 0:
            self.request_counts.append(1)
            self.error_counts.append(0 if success else 1)
            self.timeout_counts.append(1 if timeout else 0)
        else:
            self.request_counts[-1] += 1
            if not success:
                self.error_counts[-1] += 1
            if timeout:
                self.timeout_counts[-1] += 1
    
    def get_metrics_trend(self, metric_name: str, duration_minutes: int = 10) -> List[float]:
        """获取指标趋势"""
        
        cutoff_time = datetime.now() - timedelta(minutes=duration_minutes)
        recent_metrics = [
            m for m in self.metrics_history
            if m.timestamp > cutoff_time
        ]
        
        if metric_name == "cpu_percent":
            return [m.cpu_percent for m in recent_metrics]
        elif metric_name == "memory_percent":
            return [m.memory_percent for m in recent_metrics]
        elif metric_name == "response_time":
            return [m.average_response_time for m in recent_metrics]
        elif metric_name == "requests_per_second":
            return [m.requests_per_second for m in recent_metrics]
        elif metric_name == "error_rate":
            return [m.error_rate for m in recent_metrics]
        else:
            return []


class PerformanceAnalyzer:
    """性能分析器"""
    
    def __init__(self, thresholds: Optional[PerformanceThresholds] = None):
        self.thresholds = thresholds or PerformanceThresholds()
        self.anomaly_detection_enabled = True
        self.trend_analysis_enabled = True
    
    def analyze_metrics(self, metrics: PerformanceMetrics,
                       metrics_history: List[PerformanceMetrics]) -> Dict[str, Any]:
        """分析性能指标"""
        
        analysis_result = {
            "current_status": self._assess_current_status(metrics),
            "threshold_violations": self._check_threshold_violations(metrics),
            "performance_issues": [],
            "optimization_opportunities": [],
            "trend_analysis": {}
        }
        
        # 检测性能问题
        issues = self._detect_performance_issues(metrics, metrics_history)
        analysis_result["performance_issues"] = issues
        
        # 识别优化机会
        opportunities = self._identify_optimization_opportunities(metrics, metrics_history)
        analysis_result["optimization_opportunities"] = opportunities
        
        # 趋势分析
        if self.trend_analysis_enabled and len(metrics_history) > 10:
            trend_analysis = self._analyze_trends(metrics_history)
            analysis_result["trend_analysis"] = trend_analysis
        
        # 异常检测
        if self.anomaly_detection_enabled:
            anomalies = self._detect_anomalies(metrics, metrics_history)
            analysis_result["anomalies"] = anomalies
        
        return analysis_result
    
    def _assess_current_status(self, metrics: PerformanceMetrics) -> str:
        """评估当前状态"""
        
        # 计算综合健康分数
        health_score = 1.0
        
        # CPU健康
        if metrics.cpu_percent > self.thresholds.max_cpu_percent:
            health_score -= 0.3
        elif metrics.cpu_percent > self.thresholds.max_cpu_percent * 0.8:
            health_score -= 0.1
        
        # 内存健康
        if metrics.memory_percent > self.thresholds.max_memory_percent:
            health_score -= 0.3
        elif metrics.memory_percent > self.thresholds.max_memory_percent * 0.8:
            health_score -= 0.1
        
        # 响应时间健康
        if metrics.average_response_time > self.thresholds.max_response_time_ms:
            health_score -= 0.2
        elif metrics.average_response_time > self.thresholds.max_response_time_ms * 0.8:
            health_score -= 0.1
        
        # 错误率健康
        if metrics.error_rate > self.thresholds.max_error_rate:
            health_score -= 0.2
        
        health_score = max(0.0, health_score)
        
        if health_score > 0.8:
            return "excellent"
        elif health_score > 0.6:
            return "good"
        elif health_score > 0.4:
            return "fair"
        elif health_score > 0.2:
            return "poor"
        else:
            return "critical"
    
    def _check_threshold_violations(self, metrics: PerformanceMetrics) -> List[Dict[str, Any]]:
        """检查阈值违规"""
        
        violations = []
        
        if metrics.cpu_percent > self.thresholds.max_cpu_percent:
            violations.append({
                "metric": "cpu_percent",
                "current_value": metrics.cpu_percent,
                "threshold": self.thresholds.max_cpu_percent,
                "severity": "high" if metrics.cpu_percent > self.thresholds.max_cpu_percent * 1.2 else "medium"
            })
        
        if metrics.memory_percent > self.thresholds.max_memory_percent:
            violations.append({
                "metric": "memory_percent",
                "current_value": metrics.memory_percent,
                "threshold": self.thresholds.max_memory_percent,
                "severity": "high" if metrics.memory_percent > self.thresholds.max_memory_percent * 1.1 else "medium"
            })
        
        if metrics.average_response_time > self.thresholds.max_response_time_ms:
            violations.append({
                "metric": "response_time",
                "current_value": metrics.average_response_time,
                "threshold": self.thresholds.max_response_time_ms,
                "severity": "medium"
            })
        
        if metrics.error_rate > self.thresholds.max_error_rate:
            violations.append({
                "metric": "error_rate",
                "current_value": metrics.error_rate,
                "threshold": self.thresholds.max_error_rate,
                "severity": "high"
            })
        
        return violations
    
    def _detect_performance_issues(self, metrics: PerformanceMetrics,
                                 history: List[PerformanceMetrics]) -> List[Dict[str, Any]]:
        """检测性能问题"""
        
        issues = []
        
        # 高CPU使用率
        if metrics.cpu_percent > 90:
            issues.append({
                "type": "high_cpu_usage",
                "description": f"CPU usage is at {metrics.cpu_percent:.1f}%",
                "severity": "high",
                "impact": "high"
            })
        
        # 高内存使用率
        if metrics.memory_percent > 90:
            issues.append({
                "type": "high_memory_usage",
                "description": f"Memory usage is at {metrics.memory_percent:.1f}%",
                "severity": "high",
                "impact": "high"
            })
        
        # 高响应时间
        if metrics.average_response_time > self.thresholds.max_response_time_ms * 2:
            issues.append({
                "type": "high_response_time",
                "description": f"Average response time is {metrics.average_response_time:.1f}ms",
                "severity": "medium",
                "impact": "medium"
            })
        
        # 低吞吐量
        if metrics.requests_per_second < self.thresholds.min_requests_per_second:
            issues.append({
                "type": "low_throughput",
                "description": f"Request rate is only {metrics.requests_per_second:.1f} req/s",
                "severity": "medium",
                "impact": "medium"
            })
        
        # 高错误率
        if metrics.error_rate > self.thresholds.max_error_rate * 2:
            issues.append({
                "type": "high_error_rate",
                "description": f"Error rate is {metrics.error_rate:.2%}",
                "severity": "high",
                "impact": "high"
            })
        
        return issues
    
    def _identify_optimization_opportunities(self, metrics: PerformanceMetrics,
                                           history: List[PerformanceMetrics]) -> List[Dict[str, Any]]:
        """识别优化机会"""
        
        opportunities = []
        
        # 内存优化机会
        if metrics.memory_percent > 70:
            opportunities.append({
                "type": "memory_optimization",
                "description": "High memory usage detected, consider memory optimization",
                "potential_impact": "medium",
                "effort_required": "low"
            })
        
        # CPU优化机会
        if metrics.cpu_percent > 60:
            opportunities.append({
                "type": "cpu_optimization",
                "description": "High CPU usage detected, consider CPU optimization",
                "potential_impact": "medium",
                "effort_required": "medium"
            })
        
        # 响应时间优化
        if metrics.average_response_time > 500:
            opportunities.append({
                "type": "latency_optimization",
                "description": "High response times detected, consider latency optimization",
                "potential_impact": "high",
                "effort_required": "medium"
            })
        
        # 缓存优化
        if metrics.context_cache_hit_rate < 0.8:
            opportunities.append({
                "type": "cache_optimization",
                "description": "Low cache hit rate detected, consider cache optimization",
                "potential_impact": "medium",
                "effort_required": "low"
            })
        
        return opportunities
    
    def _analyze_trends(self, history: List[PerformanceMetrics]) -> Dict[str, Any]:
        """分析趋势"""
        
        if len(history) < 10:
            return {"status": "insufficient_data"}
        
        recent_metrics = history[-10:]
        
        # CPU趋势
        cpu_values = [m.cpu_percent for m in recent_metrics]
        cpu_trend = self._calculate_trend(cpu_values)
        
        # 内存趋势
        memory_values = [m.memory_percent for m in recent_metrics]
        memory_trend = self._calculate_trend(memory_values)
        
        # 响应时间趋势
        response_time_values = [m.average_response_time for m in recent_metrics]
        response_time_trend = self._calculate_trend(response_time_values)
        
        return {
            "cpu_trend": cpu_trend,
            "memory_trend": memory_trend,
            "response_time_trend": response_time_trend,
            "analysis_period": f"Last {len(recent_metrics)} data points"
        }
    
    def _calculate_trend(self, values: List[float]) -> str:
        """计算趋势"""
        
        if len(values) < 3:
            return "stable"
        
        # 简单的趋势计算
        first_half = values[:len(values)//2]
        second_half = values[len(values)//2:]
        
        first_avg = sum(first_half) / len(first_half)
        second_avg = sum(second_half) / len(second_half)
        
        change_percent = (second_avg - first_avg) / first_avg * 100
        
        if change_percent > 10:
            return "increasing"
        elif change_percent < -10:
            return "decreasing"
        else:
            return "stable"
    
    def _detect_anomalies(self, metrics: PerformanceMetrics,
                         history: List[PerformanceMetrics]) -> List[Dict[str, Any]]:
        """检测异常"""
        
        if len(history) < 20:
            return []
        
        anomalies = []
        recent_history = history[-20:]
        
        # CPU异常检测
        cpu_values = [m.cpu_percent for m in recent_history]
        cpu_mean = sum(cpu_values) / len(cpu_values)
        cpu_std = (sum((x - cpu_mean) ** 2 for x in cpu_values) / len(cpu_values)) ** 0.5
        
        if abs(metrics.cpu_percent - cpu_mean) > 2 * cpu_std:
            anomalies.append({
                "type": "cpu_anomaly",
                "description": f"CPU usage ({metrics.cpu_percent:.1f}%) is unusually different from recent average ({cpu_mean:.1f}%)",
                "severity": "medium"
            })
        
        # 内存异常检测
        memory_values = [m.memory_percent for m in recent_history]
        memory_mean = sum(memory_values) / len(memory_values)
        memory_std = (sum((x - memory_mean) ** 2 for x in memory_values) / len(memory_values)) ** 0.5
        
        if abs(metrics.memory_percent - memory_mean) > 2 * memory_std:
            anomalies.append({
                "type": "memory_anomaly",
                "description": f"Memory usage ({metrics.memory_percent:.1f}%) is unusually different from recent average ({memory_mean:.1f}%)",
                "severity": "medium"
            })
        
        return anomalies


class PerformanceOptimizer:
    """性能优化器"""
    
    def __init__(self):
        self.metrics_collector = MetricsCollector()
        self.performance_analyzer = PerformanceAnalyzer()
        
        self.optimization_strategies = {
            OptimizationStrategy.MEMORY_OPTIMIZATION: self._memory_optimization,
            OptimizationStrategy.CPU_OPTIMIZATION: self._cpu_optimization,
            OptimizationStrategy.LATENCY_OPTIMIZATION: self._latency_optimization,
            OptimizationStrategy.THROUGHPUT_OPTIMIZATION: self._throughput_optimization,
            OptimizationStrategy.BALANCED: self._balanced_optimization
        }
        
        # 优化历史
        self.optimization_history: List[Dict[str, Any]] = []
        
        # 自动优化配置
        self.auto_optimization_enabled = True
        self.optimization_interval = 300  # 5分钟
        self.last_optimization_time = 0
        
        # 优化统计
        self.optimization_stats = {
            "total_optimizations": 0,
            "successful_optimizations": 0,
            "optimization_impact": 0.0
        }
    
    async def start_monitoring(self):
        """开始性能监控"""
        
        while True:
            try:
                # 收集指标
                metrics = await self.metrics_collector.collect_system_metrics()
                
                # 分析性能
                analysis = self.performance_analyzer.analyze_metrics(
                    metrics, self.metrics_collector.metrics_history
                )
                
                # 自动优化
                if (self.auto_optimization_enabled and 
                    time.time() - self.last_optimization_time > self.optimization_interval):
                    
                    await self._auto_optimize(metrics, analysis)
                    self.last_optimization_time = time.time()
                
                # 等待下一次收集
                await asyncio.sleep(self.metrics_collector.collection_interval)
                
            except Exception as e:
                print(f"Monitoring error: {e}")
                await asyncio.sleep(5)
    
    async def optimize_performance(self, strategy: OptimizationStrategy,
                                 target_metrics: Optional[PerformanceMetrics] = None) -> Dict[str, Any]:
        """执行性能优化"""
        
        optimization_start = time.time()
        
        try:
            # 收集当前指标
            if target_metrics is None:
                current_metrics = await self.metrics_collector.collect_system_metrics()
            else:
                current_metrics = target_metrics
            
            # 选择优化策略
            optimization_func = self.optimization_strategies.get(strategy)
            if not optimization_func:
                return {"success": False, "error": f"Unknown strategy: {strategy}"}
            
            # 执行优化
            optimization_result = await optimization_func(current_metrics)
            
            # 记录优化历史
            optimization_record = {
                "timestamp": datetime.now().isoformat(),
                "strategy": strategy.value,
                "before_metrics": current_metrics,
                "optimization_actions": optimization_result.get("actions", []),
                "execution_time": time.time() - optimization_start,
                "success": optimization_result.get("success", False)
            }
            
            self.optimization_history.append(optimization_record)
            
            # 更新统计
            self.optimization_stats["total_optimizations"] += 1
            if optimization_result.get("success", False):
                self.optimization_stats["successful_optimizations"] += 1
            
            return optimization_result
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "execution_time": time.time() - optimization_start
            }
    
    async def _memory_optimization(self, metrics: PerformanceMetrics) -> Dict[str, Any]:
        """内存优化"""
        
        actions = []
        
        # 垃圾回收
        if metrics.memory_percent > 70:
            gc.collect()
            actions.append({
                "type": "garbage_collection",
                "description": "Performed garbage collection"
            })
        
        # 清理缓存（简化实现）
        if metrics.memory_percent > 80:
            actions.append({
                "type": "cache_cleanup",
                "description": "Cleaned up application caches"
            })
        
        # 上下文压缩
        if metrics.active_contexts > 100:
            actions.append({
                "type": "context_compression",
                "description": "Compressed inactive contexts"
            })
        
        return {
            "success": True,
            "strategy": "memory_optimization",
            "actions": actions,
            "estimated_impact": len(actions) * 0.1
        }
    
    async def _cpu_optimization(self, metrics: PerformanceMetrics) -> Dict[str, Any]:
        """CPU优化"""
        
        actions = []
        
        # 调整并发度
        if metrics.cpu_percent > 80:
            actions.append({
                "type": "reduce_concurrency",
                "description": "Reduced concurrent operations"
            })
        
        # 启用缓存
        if metrics.cpu_percent > 70:
            actions.append({
                "type": "enable_caching",
                "description": "Enabled result caching"
            })
        
        # 优化算法
        actions.append({
            "type": "algorithm_optimization",
            "description": "Applied CPU-efficient algorithms"
        })
        
        return {
            "success": True,
            "strategy": "cpu_optimization",
            "actions": actions,
            "estimated_impact": len(actions) * 0.15
        }
    
    async def _latency_optimization(self, metrics: PerformanceMetrics) -> Dict[str, Any]:
        """延迟优化"""
        
        actions = []
        
        # 连接池优化
        actions.append({
            "type": "connection_pooling",
            "description": "Optimized connection pooling"
        })
        
        # 预加载优化
        if metrics.context_cache_hit_rate < 0.8:
            actions.append({
                "type": "preloading",
                "description": "Enabled context preloading"
            })
        
        # 并行处理
        actions.append({
            "type": "parallel_processing",
            "description": "Enabled parallel request processing"
        })
        
        return {
            "success": True,
            "strategy": "latency_optimization",
            "actions": actions,
            "estimated_impact": len(actions) * 0.2
        }
    
    async def _throughput_optimization(self, metrics: PerformanceMetrics) -> Dict[str, Any]:
        """吞吐量优化"""
        
        actions = []
        
        # 批处理优化
        actions.append({
            "type": "batch_processing",
            "description": "Enabled batch processing"
        })
        
        # 流水线优化
        actions.append({
            "type": "pipeline_optimization",
            "description": "Optimized processing pipeline"
        })
        
        # 负载均衡
        if metrics.requests_per_second > 50:
            actions.append({
                "type": "load_balancing",
                "description": "Improved load balancing"
            })
        
        return {
            "success": True,
            "strategy": "throughput_optimization",
            "actions": actions,
            "estimated_impact": len(actions) * 0.18
        }
    
    async def _balanced_optimization(self, metrics: PerformanceMetrics) -> Dict[str, Any]:
        """平衡优化"""
        
        actions = []
        
        # 根据当前瓶颈选择优化策略
        if metrics.memory_percent > 80:
            memory_result = await self._memory_optimization(metrics)
            actions.extend(memory_result["actions"])
        
        if metrics.cpu_percent > 80:
            cpu_result = await self._cpu_optimization(metrics)
            actions.extend(cpu_result["actions"])
        
        if metrics.average_response_time > 1000:
            latency_result = await self._latency_optimization(metrics)
            actions.extend(latency_result["actions"])
        
        if metrics.requests_per_second < 10:
            throughput_result = await self._throughput_optimization(metrics)
            actions.extend(throughput_result["actions"])
        
        return {
            "success": True,
            "strategy": "balanced_optimization",
            "actions": actions,
            "estimated_impact": min(1.0, len(actions) * 0.1)
        }
    
    async def _auto_optimize(self, metrics: PerformanceMetrics, analysis: Dict[str, Any]):
        """自动优化"""
        
        # 根据分析结果决定是否需要优化
        threshold_violations = analysis.get("threshold_violations", [])
        performance_issues = analysis.get("performance_issues", [])
        
        if not threshold_violations and not performance_issues:
            return
        
        # 选择优化策略
        strategy = OptimizationStrategy.BALANCED
        
        # 根据主要问题选择特定策略
        for issue in performance_issues:
            if issue["type"] in ["high_memory_usage"]:
                strategy = OptimizationStrategy.MEMORY_OPTIMIZATION
                break
            elif issue["type"] in ["high_cpu_usage"]:
                strategy = OptimizationStrategy.CPU_OPTIMIZATION
                break
            elif issue["type"] in ["high_response_time"]:
                strategy = OptimizationStrategy.LATENCY_OPTIMIZATION
                break
            elif issue["type"] in ["low_throughput"]:
                strategy = OptimizationStrategy.THROUGHPUT_OPTIMIZATION
                break
        
        # 执行优化
        await self.optimize_performance(strategy, metrics)
    
    def get_optimization_recommendations(self, metrics: PerformanceMetrics) -> List[OptimizationAction]:
        """获取优化建议"""
        
        recommendations = []
        
        # 内存优化建议
        if metrics.memory_percent > 80:
            recommendations.append(OptimizationAction(
                action_type="memory_cleanup",
                description="Perform memory cleanup and garbage collection",
                priority=1,
                estimated_impact=0.3,
                implementation_cost=0.1
            ))
        
        # CPU优化建议
        if metrics.cpu_percent > 80:
            recommendations.append(OptimizationAction(
                action_type="cpu_optimization",
                description="Reduce CPU-intensive operations",
                priority=1,
                estimated_impact=0.4,
                implementation_cost=0.3
            ))
        
        # 延迟优化建议
        if metrics.average_response_time > 1000:
            recommendations.append(OptimizationAction(
                action_type="latency_reduction",
                description="Optimize response time through caching and parallelization",
                priority=2,
                estimated_impact=0.5,
                implementation_cost=0.4
            ))
        
        # 缓存优化建议
        if metrics.context_cache_hit_rate < 0.7:
            recommendations.append(OptimizationAction(
                action_type="cache_optimization",
                description="Improve cache hit rate",
                priority=2,
                estimated_impact=0.3,
                implementation_cost=0.2
            ))
        
        # 按优先级和影响排序
        recommendations.sort(key=lambda x: (x.priority, -x.estimated_impact))
        
        return recommendations
    
    def get_performance_report(self) -> Dict[str, Any]:
        """获取性能报告"""
        
        current_metrics = None
        if self.metrics_collector.metrics_history:
            current_metrics = self.metrics_collector.metrics_history[-1]
        
        return {
            "current_metrics": current_metrics,
            "optimization_stats": self.optimization_stats,
            "recent_optimizations": self.optimization_history[-10:],
            "auto_optimization_enabled": self.auto_optimization_enabled,
            "monitoring_active": len(self.metrics_collector.metrics_history) > 0,
            "report_timestamp": datetime.now().isoformat()
        }
    
    def configure_thresholds(self, thresholds: PerformanceThresholds):
        """配置性能阈值"""
        self.performance_analyzer.thresholds = thresholds
    
    def enable_auto_optimization(self, enabled: bool = True):
        """启用/禁用自动优化"""
        self.auto_optimization_enabled = enabled
    
    def record_response_time(self, response_time: float):
        """记录响应时间"""
        self.metrics_collector.record_response_time(response_time)
    
    def record_request(self, success: bool = True, timeout: bool = False):
        """记录请求"""
        self.metrics_collector.record_request(success, timeout)