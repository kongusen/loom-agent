"""
智能体协调器

提供高级的多智能体协调接口，整合编排引擎和策略
"""

import asyncio
import time
from typing import Dict, Any, List, Optional, AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime

from ...types import Agent, AgentEvent, AgentEventType
from .engine import OrchestrationEngine, UserInput, OrchestrationContext
from .strategies import (
    PriorOrchestrationStrategy, PosteriorOrchestrationStrategy,
    FunctionalOrchestrationStrategy, ComponentOrchestrationStrategy,
    PuppeteerOrchestrationStrategy, DefaultOrchestrationStrategy
)


@dataclass
class CoordinationRequest:
    """协调请求"""
    user_message: str
    available_agents: List[Agent]
    session_constraints: Dict[str, Any] = field(default_factory=dict)
    preferred_strategy: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CoordinationResult:
    """协调结果"""
    success: bool
    primary_result: Dict[str, Any]
    participating_agents: List[Agent]
    strategy_used: str
    execution_time: float
    coordination_metadata: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None


class AgentCoordinator:
    """智能体协调器
    
    提供简化的多智能体协调接口，自动选择最佳策略
    """
    
    def __init__(self):
        self.orchestration_engine = OrchestrationEngine()
        self.coordination_history: List[CoordinationResult] = []
        
        # 注册所有策略
        self._register_strategies()
        
        # 协调统计
        self.coordination_stats = {
            "total_coordinations": 0,
            "strategy_usage": {},
            "average_execution_time": 0.0,
            "success_rate": 0.0
        }
    
    def _register_strategies(self):
        """注册所有编排策略"""
        
        strategies = {
            "prior": PriorOrchestrationStrategy(),
            "posterior": PosteriorOrchestrationStrategy(),
            "functional": FunctionalOrchestrationStrategy(),
            "component": ComponentOrchestrationStrategy(),
            "puppeteer": PuppeteerOrchestrationStrategy(),
            "default": DefaultOrchestrationStrategy()
        }
        
        for name, strategy in strategies.items():
            self.orchestration_engine.register_strategy(name, strategy)
    
    async def coordinate(self, request: CoordinationRequest) -> CoordinationResult:
        """协调多智能体执行任务"""
        
        start_time = time.time()
        
        try:
            # 构建编排上下文
            user_input = UserInput(
                message=request.user_message,
                intent=self._analyze_user_intent(request.user_message),
                context=request.metadata
            )
            
            orchestration_context = OrchestrationContext(
                user_input=user_input,
                available_agents=request.available_agents,
                session_context=request.session_constraints,
                constraints=self._build_constraints(request)
            )
            
            # 执行编排
            orchestration_result = await self.orchestration_engine.orchestrate(
                user_input=user_input,
                available_agents=request.available_agents,
                context=orchestration_context
            )
            
            # 构建协调结果
            execution_time = time.time() - start_time
            
            coordination_result = CoordinationResult(
                success=orchestration_result.orchestration_metadata.get("status") == "completed",
                primary_result=orchestration_result.primary_result,
                participating_agents=orchestration_result.participating_agents,
                strategy_used=orchestration_result.orchestration_metadata.get("strategy_used", "unknown"),
                execution_time=execution_time,
                coordination_metadata=orchestration_result.orchestration_metadata
            )
            
            # 记录协调历史
            self.coordination_history.append(coordination_result)
            self._update_coordination_stats(coordination_result)
            
            return coordination_result
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            error_result = CoordinationResult(
                success=False,
                primary_result={"error": str(e)},
                participating_agents=[],
                strategy_used="none",
                execution_time=execution_time,
                error_message=str(e)
            )
            
            self.coordination_history.append(error_result)
            self._update_coordination_stats(error_result)
            
            return error_result
    
    async def coordinate_streaming(self, request: CoordinationRequest) -> AsyncIterator[AgentEvent]:
        """流式协调，实时返回协调事件"""
        
        yield AgentEvent(
            type=AgentEventType.COORDINATION_START,
            content=f"开始协调 {len(request.available_agents)} 个智能体",
            metadata={"request_id": id(request)}
        )
        
        try:
            # 分析和策略选择
            yield AgentEvent(
                type=AgentEventType.THINKING,
                content="分析任务需求，选择最佳编排策略...",
                metadata={"phase": "strategy_selection"}
            )
            
            coordination_result = await self.coordinate(request)
            
            if coordination_result.success:
                yield AgentEvent(
                    type=AgentEventType.COORDINATION_SUCCESS,
                    content=f"协调成功，使用策略: {coordination_result.strategy_used}",
                    metadata={
                        "strategy": coordination_result.strategy_used,
                        "agents_used": len(coordination_result.participating_agents),
                        "execution_time": coordination_result.execution_time
                    }
                )
                
                yield AgentEvent(
                    type=AgentEventType.RESPONSE_COMPLETE,
                    content=coordination_result.primary_result,
                    metadata=coordination_result.coordination_metadata
                )
            else:
                yield AgentEvent(
                    type=AgentEventType.ERROR,
                    content=f"协调失败: {coordination_result.error_message}",
                    metadata={"error_type": "coordination_failure"}
                )
                
        except Exception as e:
            yield AgentEvent(
                type=AgentEventType.ERROR,
                content=f"协调过程异常: {str(e)}",
                metadata={"error_type": "coordination_exception"}
            )
    
    async def recommend_strategy(self, request: CoordinationRequest) -> Dict[str, Any]:
        """推荐最佳编排策略"""
        
        user_intent = self._analyze_user_intent(request.user_message)
        
        # 策略选择逻辑
        complexity_level = len([v for v in user_intent.get("complexity_indicators", {}).values() if v])
        agent_count = len(request.available_agents)
        
        strategy_scores = {}
        
        # Prior策略：适合预处理密集型任务
        if "分析" in request.user_message or "analysis" in request.user_message.lower():
            strategy_scores["prior"] = 0.8
        else:
            strategy_scores["prior"] = 0.4
        
        # Posterior策略：适合后处理和优化任务
        if "优化" in request.user_message or "improve" in request.user_message.lower():
            strategy_scores["posterior"] = 0.9
        else:
            strategy_scores["posterior"] = 0.3
        
        # Functional策略：适合功能明确的任务
        if complexity_level >= 3 and agent_count >= 2:
            strategy_scores["functional"] = 0.7
        else:
            strategy_scores["functional"] = 0.4
        
        # Component策略：适合可分解的复杂任务
        if complexity_level >= 4:
            strategy_scores["component"] = 0.8
        else:
            strategy_scores["component"] = 0.3
        
        # Puppeteer策略：适合需要严格控制的任务
        if agent_count >= 3 and ("控制" in request.user_message or "coordinate" in request.user_message.lower()):
            strategy_scores["puppeteer"] = 0.9
        else:
            strategy_scores["puppeteer"] = 0.2
        
        # 选择最高分策略
        recommended_strategy = max(strategy_scores.items(), key=lambda x: x[1])
        
        return {
            "recommended_strategy": recommended_strategy[0],
            "confidence": recommended_strategy[1],
            "all_scores": strategy_scores,
            "reasoning": self._generate_strategy_reasoning(
                recommended_strategy[0], user_intent, agent_count
            )
        }
    
    def _analyze_user_intent(self, message: str) -> Dict[str, Any]:
        """分析用户意图"""
        
        message_lower = message.lower()
        
        # 意图分类
        intent_indicators = {
            "analysis": ["分析", "analyze", "examine", "study", "investigate"],
            "creation": ["创建", "create", "make", "build", "generate", "write"],
            "modification": ["修改", "update", "change", "modify", "edit", "fix"],
            "coordination": ["协调", "coordinate", "organize", "manage", "control"],
            "optimization": ["优化", "optimize", "improve", "enhance", "refine"]
        }
        
        intent_scores = {}
        for intent_type, indicators in intent_indicators.items():
            score = sum(1 for indicator in indicators if indicator in message_lower)
            intent_scores[intent_type] = score
        
        primary_intent = max(intent_scores.items(), key=lambda x: x[1])[0] if intent_scores else "general"
        
        # 复杂度指标
        complexity_indicators = {
            "word_count": len(message.split()),
            "has_multiple_sentences": "。" in message or "." in message,
            "has_conditionals": any(word in message_lower for word in ["如果", "if", "when", "unless"]),
            "has_comparisons": any(word in message_lower for word in ["比较", "versus", "compare", "than"]),
            "has_coordination_words": any(word in message_lower for word in ["协调", "coordinate", "together", "collaborate"])
        }
        
        return {
            "primary_intent": primary_intent,
            "confidence": min(1.0, intent_scores.get(primary_intent, 0) / 3),
            "all_scores": intent_scores,
            "complexity_indicators": complexity_indicators
        }
    
    def _build_constraints(self, request: CoordinationRequest) -> Dict[str, Any]:
        """构建约束条件"""
        
        return {
            "max_agents": len(request.available_agents),
            "preferred_strategy": request.preferred_strategy,
            "session_constraints": request.session_constraints,
            "coordination_timeout": 30.0,  # 30秒超时
            "allow_parallel_execution": True,
            "require_consensus": False
        }
    
    def _generate_strategy_reasoning(self, strategy: str, intent: Dict[str, Any], 
                                   agent_count: int) -> str:
        """生成策略选择理由"""
        
        reasoning_templates = {
            "prior": "选择预优先策略，因为任务需要充分的预处理和分析准备",
            "posterior": "选择后优先策略，因为任务重点在于结果的后处理和优化",
            "functional": f"选择功能化策略，因为有{agent_count}个智能体可以按功能分工",
            "component": "选择组件化策略，因为任务复杂度高，适合分解为独立组件",
            "puppeteer": f"选择木偶师策略，因为需要对{agent_count}个智能体进行集中控制",
            "default": "使用默认策略，因为任务相对简单或智能体数量有限"
        }
        
        base_reason = reasoning_templates.get(strategy, "未知策略")
        
        # 添加意图相关的理由
        primary_intent = intent.get("primary_intent", "general")
        if primary_intent != "general":
            base_reason += f"，主要意图为{primary_intent}"
        
        return base_reason
    
    def _update_coordination_stats(self, result: CoordinationResult):
        """更新协调统计"""
        
        self.coordination_stats["total_coordinations"] += 1
        
        # 更新策略使用统计
        strategy = result.strategy_used
        if strategy not in self.coordination_stats["strategy_usage"]:
            self.coordination_stats["strategy_usage"][strategy] = 0
        self.coordination_stats["strategy_usage"][strategy] += 1
        
        # 更新平均执行时间
        total_count = self.coordination_stats["total_coordinations"]
        current_avg = self.coordination_stats["average_execution_time"]
        
        self.coordination_stats["average_execution_time"] = (
            (current_avg * (total_count - 1) + result.execution_time) / total_count
        )
        
        # 更新成功率
        success_count = sum(1 for r in self.coordination_history if r.success)
        self.coordination_stats["success_rate"] = success_count / total_count
    
    def get_coordination_history(self, limit: int = 10) -> List[CoordinationResult]:
        """获取协调历史"""
        return self.coordination_history[-limit:]
    
    def get_coordination_statistics(self) -> Dict[str, Any]:
        """获取协调统计信息"""
        
        strategy_distribution = {}
        total_coordinations = self.coordination_stats["total_coordinations"]
        
        for strategy, count in self.coordination_stats["strategy_usage"].items():
            strategy_distribution[strategy] = {
                "count": count,
                "percentage": (count / total_coordinations * 100) if total_coordinations > 0 else 0
            }
        
        return {
            "basic_stats": self.coordination_stats,
            "strategy_distribution": strategy_distribution,
            "recent_performance": self._calculate_recent_performance(),
            "agent_utilization": self._calculate_agent_utilization()
        }
    
    def _calculate_recent_performance(self, window_size: int = 5) -> Dict[str, Any]:
        """计算最近的性能指标"""
        
        recent_results = self.coordination_history[-window_size:]
        
        if not recent_results:
            return {"message": "No recent coordination data"}
        
        recent_success_rate = sum(1 for r in recent_results if r.success) / len(recent_results)
        recent_avg_time = sum(r.execution_time for r in recent_results) / len(recent_results)
        
        return {
            "window_size": len(recent_results),
            "success_rate": recent_success_rate,
            "average_execution_time": recent_avg_time,
            "trend": "improving" if recent_success_rate > 0.8 else "stable"
        }
    
    def _calculate_agent_utilization(self) -> Dict[str, Any]:
        """计算智能体利用率"""
        
        agent_usage = {}
        total_participations = 0
        
        for result in self.coordination_history:
            for agent in result.participating_agents:
                if agent.agent_id not in agent_usage:
                    agent_usage[agent.agent_id] = 0
                agent_usage[agent.agent_id] += 1
                total_participations += 1
        
        if total_participations == 0:
            return {"message": "No agent utilization data"}
        
        # 计算利用率百分比
        utilization_percentages = {
            agent_id: (count / total_participations * 100)
            for agent_id, count in agent_usage.items()
        }
        
        return {
            "total_participations": total_participations,
            "agent_usage_counts": agent_usage,
            "utilization_percentages": utilization_percentages,
            "most_utilized_agent": max(agent_usage.items(), key=lambda x: x[1])[0] if agent_usage else None
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        
        try:
            # 检查编排引擎状态
            engine_status = await self.orchestration_engine.get_orchestration_status()
            
            # 检查策略可用性
            available_strategies = list(self.orchestration_engine.orchestration_strategies.keys())
            
            # 计算健康分数
            health_score = self._calculate_health_score(engine_status)
            
            return {
                "status": "healthy" if health_score > 0.8 else "degraded" if health_score > 0.5 else "unhealthy",
                "health_score": health_score,
                "engine_status": engine_status,
                "available_strategies": available_strategies,
                "coordination_stats": self.coordination_stats,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "health_score": 0.0,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _calculate_health_score(self, engine_status: Dict[str, Any]) -> float:
        """计算健康分数"""
        
        score = 0.0
        
        # 检查策略可用性 (40%)
        expected_strategies = 5  # prior, posterior, functional, component, puppeteer
        available_strategies = len(engine_status.get("registered_strategies", []))
        strategy_score = min(1.0, available_strategies / expected_strategies)
        score += strategy_score * 0.4
        
        # 检查成功率 (30%)
        success_rate = self.coordination_stats.get("success_rate", 0.0)
        score += success_rate * 0.3
        
        # 检查系统健康状态 (20%)
        system_health = engine_status.get("system_health", "unknown")
        health_score = 1.0 if system_health == "healthy" else 0.5 if system_health == "busy" else 0.0
        score += health_score * 0.2
        
        # 检查活跃流程数量 (10%)
        active_flows = engine_status.get("active_flows", 0)
        flow_score = 1.0 if active_flows < 5 else 0.5 if active_flows < 10 else 0.0
        score += flow_score * 0.1
        
        return min(1.0, score)
    
    async def reset_coordinator(self):
        """重置协调器状态"""
        
        self.coordination_history.clear()
        self.coordination_stats = {
            "total_coordinations": 0,
            "strategy_usage": {},
            "average_execution_time": 0.0,
            "success_rate": 0.0
        }
        
        # 重新注册策略
        self._register_strategies()