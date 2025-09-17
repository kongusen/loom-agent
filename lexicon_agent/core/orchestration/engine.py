"""
编排引擎

管理智能体选择、上下文分布和交互流程控制
"""

import asyncio
import time
from typing import Dict, Any, List, Optional, AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime
import json

from ...types import (
    Agent, CoordinationEvent, CoordinationEventType, OrchestrationResult,
    OrchestrationStrategy, ToolCall, ToolResult, ManagedContext
)


@dataclass
class UserInput:
    """用户输入"""
    message: str
    intent: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OrchestrationContext:
    """编排上下文"""
    user_input: UserInput
    available_agents: List[Agent]
    session_context: Dict[str, Any] = field(default_factory=dict)
    constraints: Dict[str, Any] = field(default_factory=dict)
    orchestration_id: str = field(default_factory=lambda: f"orch_{int(time.time())}")


@dataclass
class OrchestrationFlow:
    """编排流程"""
    selected_agents: List[Agent]
    context_distribution: Dict[str, Any]
    execution_plan: Dict[str, Any]
    coordination_events: List[CoordinationEvent] = field(default_factory=list)


class AgentSelector:
    """智能体选择器"""
    
    def __init__(self):
        self.selection_cache: Dict[str, List[Agent]] = {}
        self.agent_performance_history: Dict[str, List[float]] = {}
    
    async def select(self, available_agents: List[Agent], 
                    intent: Dict[str, Any],
                    strategy: 'OrchestrationStrategy') -> List[Agent]:
        """基于意图和策略选择智能体"""
        
        # 分析任务需求
        task_requirements = self._analyze_task_requirements(intent)
        
        # 评估智能体能力匹配度
        agent_scores = []
        for agent in available_agents:
            if agent.status != "available":
                continue
                
            capability_score = self._calculate_capability_match(agent, task_requirements)
            performance_score = self._get_performance_score(agent)
            workload_score = self._calculate_workload_score(agent)
            
            total_score = (capability_score * 0.5 + 
                          performance_score * 0.3 + 
                          workload_score * 0.2)
            
            agent_scores.append((agent, total_score))
        
        # 按分数排序
        agent_scores.sort(key=lambda x: x[1], reverse=True)
        
        # 根据策略选择数量
        selection_count = await strategy.determine_agent_count(task_requirements)
        
        selected_agents = [agent for agent, score in agent_scores[:selection_count]]
        
        return selected_agents
    
    def _analyze_task_requirements(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """分析任务需求"""
        
        primary_intent = intent.get("primary_intent", "unknown")
        complexity = intent.get("complexity_indicators", {})
        
        requirements = {
            "complexity_level": self._assess_complexity(complexity),
            "domain_expertise": self._identify_domain(primary_intent),
            "collaboration_needed": self._assess_collaboration_need(complexity),
            "resource_intensity": self._assess_resource_needs(complexity)
        }
        
        return requirements
    
    def _assess_complexity(self, complexity_indicators: Dict[str, Any]) -> int:
        """评估复杂度级别 (1-5)"""
        
        factors = [
            complexity_indicators.get("word_count", 0) > 50,
            complexity_indicators.get("has_multiple_sentences", False),
            complexity_indicators.get("has_conditionals", False),
            complexity_indicators.get("has_comparisons", False)
        ]
        
        return min(5, sum(factors) + 1)
    
    def _identify_domain(self, primary_intent: str) -> List[str]:
        """识别领域专业需求"""
        
        domain_mapping = {
            "analysis": ["data_analysis", "code_analysis"],
            "command": ["code_generation", "file_operations"],
            "question": ["knowledge_retrieval", "research"],
            "modification": ["code_editing", "content_creation"]
        }
        
        return domain_mapping.get(primary_intent, ["general"])
    
    def _assess_collaboration_need(self, complexity: Dict[str, Any]) -> bool:
        """评估是否需要协作"""
        
        complexity_level = self._assess_complexity(complexity)
        return complexity_level > 3
    
    def _assess_resource_needs(self, complexity: Dict[str, Any]) -> str:
        """评估资源需求强度"""
        
        complexity_level = self._assess_complexity(complexity)
        
        if complexity_level > 4:
            return "high"
        elif complexity_level > 2:
            return "medium"
        else:
            return "low"
    
    def _calculate_capability_match(self, agent: Agent, requirements: Dict[str, Any]) -> float:
        """计算能力匹配度"""
        
        domain_expertise = requirements.get("domain_expertise", [])
        agent_capabilities = agent.capabilities
        
        if not domain_expertise:
            return 0.5  # 中等匹配度
        
        # 计算领域匹配度
        matches = sum(1 for domain in domain_expertise 
                     if any(domain in cap for cap in agent_capabilities))
        
        domain_match_score = matches / len(domain_expertise)
        
        # 考虑专业化程度
        specialization_bonus = 0.2 if agent.specialization in domain_expertise else 0
        
        return min(1.0, domain_match_score + specialization_bonus)
    
    def _get_performance_score(self, agent: Agent) -> float:
        """获取性能分数"""
        
        history = self.agent_performance_history.get(agent.agent_id, [])
        
        if not history:
            return 0.7  # 默认中等性能
        
        # 使用最近的性能数据，权重衰减
        weights = [0.5, 0.3, 0.2]  # 最近的性能权重更高
        weighted_performance = sum(
            score * weight for score, weight in zip(history[-3:], weights[:len(history)])
        ) / sum(weights[:len(history)])
        
        return weighted_performance
    
    def _calculate_workload_score(self, agent: Agent) -> float:
        """计算工作负载分数（负载越低分数越高）"""
        
        # 简化实现：基于状态
        if agent.status == "available":
            return 1.0
        elif agent.status == "busy":
            return 0.3
        else:  # offline
            return 0.0
    
    async def update_performance(self, agent_id: str, performance_score: float):
        """更新智能体性能记录"""
        
        if agent_id not in self.agent_performance_history:
            self.agent_performance_history[agent_id] = []
        
        self.agent_performance_history[agent_id].append(performance_score)
        
        # 保留最近10次记录
        if len(self.agent_performance_history[agent_id]) > 10:
            self.agent_performance_history[agent_id] = self.agent_performance_history[agent_id][-10:]


class ContextDistributor:
    """上下文分发器"""
    
    def __init__(self):
        self.distribution_strategies = {
            "broadcast": self._broadcast_distribution,
            "selective": self._selective_distribution,
            "hierarchical": self._hierarchical_distribution,
            "adaptive": self._adaptive_distribution
        }
    
    async def distribute(self, context: OrchestrationContext,
                        selected_agents: List[Agent],
                        strategy: 'OrchestrationStrategy') -> Dict[str, Any]:
        """分发上下文到选定的智能体"""
        
        distribution_method = await strategy.get_context_distribution_method()
        
        if distribution_method in self.distribution_strategies:
            return await self.distribution_strategies[distribution_method](
                context, selected_agents
            )
        else:
            return await self._adaptive_distribution(context, selected_agents)
    
    async def _broadcast_distribution(self, context: OrchestrationContext,
                                    agents: List[Agent]) -> Dict[str, Any]:
        """广播分发：所有智能体获得完整上下文"""
        
        distributed_context = {}
        
        full_context = {
            "user_input": context.user_input.__dict__,
            "session_context": context.session_context,
            "constraints": context.constraints,
            "orchestration_id": context.orchestration_id
        }
        
        for agent in agents:
            distributed_context[agent.agent_id] = full_context.copy()
        
        return {
            "distribution_method": "broadcast",
            "context_map": distributed_context,
            "total_agents": len(agents),
            "context_size": len(json.dumps(full_context))
        }
    
    async def _selective_distribution(self, context: OrchestrationContext,
                                    agents: List[Agent]) -> Dict[str, Any]:
        """选择性分发：根据智能体能力分发相关上下文"""
        
        distributed_context = {}
        
        for agent in agents:
            # 基于智能体能力过滤上下文
            relevant_context = self._filter_context_for_agent(
                context, agent
            )
            distributed_context[agent.agent_id] = relevant_context
        
        return {
            "distribution_method": "selective",
            "context_map": distributed_context,
            "total_agents": len(agents),
            "customization_level": "high"
        }
    
    async def _hierarchical_distribution(self, context: OrchestrationContext,
                                       agents: List[Agent]) -> Dict[str, Any]:
        """分层分发：主智能体获得完整上下文，其他获得摘要"""
        
        distributed_context = {}
        
        if not agents:
            return {"distribution_method": "hierarchical", "context_map": {}}
        
        # 选择主智能体（第一个或性能最好的）
        primary_agent = agents[0]
        secondary_agents = agents[1:]
        
        # 主智能体获得完整上下文
        full_context = {
            "user_input": context.user_input.__dict__,
            "session_context": context.session_context,
            "constraints": context.constraints,
            "role": "primary",
            "orchestration_id": context.orchestration_id
        }
        distributed_context[primary_agent.agent_id] = full_context
        
        # 次要智能体获得摘要上下文
        summary_context = self._create_summary_context(context)
        for agent in secondary_agents:
            agent_context = summary_context.copy()
            agent_context["role"] = "secondary"
            agent_context["primary_agent"] = primary_agent.agent_id
            distributed_context[agent.agent_id] = agent_context
        
        return {
            "distribution_method": "hierarchical",
            "context_map": distributed_context,
            "primary_agent": primary_agent.agent_id,
            "secondary_agents": [a.agent_id for a in secondary_agents]
        }
    
    async def _adaptive_distribution(self, context: OrchestrationContext,
                                   agents: List[Agent]) -> Dict[str, Any]:
        """自适应分发：根据任务复杂度自动选择分发策略"""
        
        complexity = context.user_input.intent.get("complexity_indicators", {})
        complexity_level = len([v for v in complexity.values() if v])
        
        if complexity_level > 3:
            return await self._hierarchical_distribution(context, agents)
        elif len(agents) > 3:
            return await self._selective_distribution(context, agents)
        else:
            return await self._broadcast_distribution(context, agents)
    
    def _filter_context_for_agent(self, context: OrchestrationContext,
                                 agent: Agent) -> Dict[str, Any]:
        """为特定智能体过滤上下文"""
        
        base_context = {
            "user_input": context.user_input.__dict__,
            "orchestration_id": context.orchestration_id,
            "agent_role": agent.specialization
        }
        
        # 根据智能体能力添加相关上下文
        if "data_analysis" in agent.capabilities:
            base_context["session_context"] = context.session_context
        
        if "code_generation" in agent.capabilities:
            base_context["constraints"] = context.constraints
        
        return base_context
    
    def _create_summary_context(self, context: OrchestrationContext) -> Dict[str, Any]:
        """创建摘要上下文"""
        
        return {
            "user_intent": context.user_input.intent.get("primary_intent", "unknown"),
            "task_summary": context.user_input.message[:200],  # 截断长消息
            "orchestration_id": context.orchestration_id,
            "coordination_mode": "hierarchical"
        }


class InteractionController:
    """交互控制器"""
    
    def __init__(self):
        self.active_flows: Dict[str, OrchestrationFlow] = {}
        self.event_handlers = {
            CoordinationEventType.AGENT_JOIN: self._handle_agent_join,
            CoordinationEventType.AGENT_LEAVE: self._handle_agent_leave,
            CoordinationEventType.CONTEXT_SHARE: self._handle_context_share,
            CoordinationEventType.TASK_HANDOFF: self._handle_task_handoff
        }
    
    async def create_flow(self, selected_agents: List[Agent],
                         distributed_context: Dict[str, Any],
                         strategy: 'OrchestrationStrategy') -> OrchestrationFlow:
        """创建编排流程"""
        
        execution_plan = await strategy.create_execution_plan(
            selected_agents, distributed_context
        )
        
        flow = OrchestrationFlow(
            selected_agents=selected_agents,
            context_distribution=distributed_context,
            execution_plan=execution_plan
        )
        
        # 注册流程
        flow_id = f"flow_{int(time.time())}_{len(self.active_flows)}"
        self.active_flows[flow_id] = flow
        
        return flow
    
    async def handle_coordination_event(self, event: CoordinationEvent,
                                      flow: OrchestrationFlow) -> Dict[str, Any]:
        """处理协调事件"""
        
        if event.type in self.event_handlers:
            result = await self.event_handlers[event.type](event, flow)
            
            # 记录事件
            flow.coordination_events.append(event)
            
            return result
        else:
            return {"status": "unknown_event", "event_type": event.type}
    
    async def _handle_agent_join(self, event: CoordinationEvent,
                               flow: OrchestrationFlow) -> Dict[str, Any]:
        """处理智能体加入"""
        
        new_agent = event.agent
        
        # 检查是否已经在流程中
        if new_agent in flow.selected_agents:
            return {"status": "already_present", "agent_id": new_agent.agent_id}
        
        # 添加到流程
        flow.selected_agents.append(new_agent)
        
        # 为新智能体分发上下文（简化实现）
        new_context = {
            "role": "dynamic_join",
            "join_time": datetime.now().isoformat(),
            "existing_agents": [a.agent_id for a in flow.selected_agents[:-1]]
        }
        flow.context_distribution[new_agent.agent_id] = new_context
        
        return {
            "status": "joined",
            "agent_id": new_agent.agent_id,
            "total_agents": len(flow.selected_agents)
        }
    
    async def _handle_agent_leave(self, event: CoordinationEvent,
                                flow: OrchestrationFlow) -> Dict[str, Any]:
        """处理智能体离开"""
        
        leaving_agent = event.agent
        
        # 从流程中移除
        if leaving_agent in flow.selected_agents:
            flow.selected_agents.remove(leaving_agent)
            
            # 清理上下文分发
            if leaving_agent.agent_id in flow.context_distribution:
                del flow.context_distribution[leaving_agent.agent_id]
            
            return {
                "status": "left",
                "agent_id": leaving_agent.agent_id,
                "remaining_agents": len(flow.selected_agents)
            }
        else:
            return {"status": "not_found", "agent_id": leaving_agent.agent_id}
    
    async def _handle_context_share(self, event: CoordinationEvent,
                                  flow: OrchestrationFlow) -> Dict[str, Any]:
        """处理上下文共享"""
        
        source_agent = event.agent
        shared_data = event.data.get("shared_context", {})
        target_agents = event.data.get("target_agents", [])
        
        # 如果没有指定目标，广播给所有其他智能体
        if not target_agents:
            target_agents = [a.agent_id for a in flow.selected_agents 
                           if a.agent_id != source_agent.agent_id]
        
        # 分发共享上下文
        shared_count = 0
        for agent_id in target_agents:
            if agent_id in flow.context_distribution:
                if "shared_contexts" not in flow.context_distribution[agent_id]:
                    flow.context_distribution[agent_id]["shared_contexts"] = []
                
                flow.context_distribution[agent_id]["shared_contexts"].append({
                    "source": source_agent.agent_id,
                    "data": shared_data,
                    "timestamp": datetime.now().isoformat()
                })
                shared_count += 1
        
        return {
            "status": "shared",
            "source_agent": source_agent.agent_id,
            "targets_reached": shared_count,
            "data_size": len(json.dumps(shared_data))
        }
    
    async def _handle_task_handoff(self, event: CoordinationEvent,
                                 flow: OrchestrationFlow) -> Dict[str, Any]:
        """处理任务移交"""
        
        source_agent = event.agent
        task_data = event.data.get("task", {})
        target_agent_id = event.data.get("target_agent")
        
        if not target_agent_id:
            return {"status": "no_target", "source_agent": source_agent.agent_id}
        
        # 查找目标智能体
        target_agent = None
        for agent in flow.selected_agents:
            if agent.agent_id == target_agent_id:
                target_agent = agent
                break
        
        if not target_agent:
            return {"status": "target_not_found", "target_agent": target_agent_id}
        
        # 执行任务移交
        if target_agent_id in flow.context_distribution:
            if "handoff_tasks" not in flow.context_distribution[target_agent_id]:
                flow.context_distribution[target_agent_id]["handoff_tasks"] = []
            
            flow.context_distribution[target_agent_id]["handoff_tasks"].append({
                "source": source_agent.agent_id,
                "task": task_data,
                "handoff_time": datetime.now().isoformat()
            })
        
        return {
            "status": "handed_off",
            "source_agent": source_agent.agent_id,
            "target_agent": target_agent_id,
            "task_id": task_data.get("id", "unknown")
        }


class OrchestrationEngine:
    """编排引擎主类，实现多智能体协调"""
    
    def __init__(self):
        self.agent_selector = AgentSelector()
        self.context_distributor = ContextDistributor() 
        self.interaction_controller = InteractionController()
        self.orchestration_strategies = {}  # 将在strategies模块中注册
        
        # 性能指标
        self.orchestration_metrics = {
            "total_orchestrations": 0,
            "average_orchestration_time": 0.0,
            "agent_utilization": {},
            "success_rate": 0.0
        }
    
    def register_strategy(self, name: str, strategy: 'OrchestrationStrategy'):
        """注册编排策略"""
        self.orchestration_strategies[name] = strategy
    
    async def orchestrate(self, user_input: UserInput,
                         available_agents: List[Agent],
                         context: OrchestrationContext) -> OrchestrationResult:
        """编排的主入口方法"""
        
        start_time = time.time()
        orchestration_id = context.orchestration_id
        
        try:
            # 1. 意图识别和策略选择
            intent = await self._analyze_intent(user_input)
            strategy = self._select_orchestration_strategy(intent, context)
            
            # 2. 智能体选择和上下文分布
            selected_agents = await self.agent_selector.select(
                available_agents, intent, strategy
            )
            
            if not selected_agents:
                return OrchestrationResult(
                    primary_result={"error": "No suitable agents found"},
                    participating_agents=[],
                    orchestration_metadata={"status": "failed", "reason": "no_agents"}
                )
            
            distributed_context = await self.context_distributor.distribute(
                context, selected_agents, strategy
            )
            
            # 3. 交互流程控制
            orchestration_flow = await self.interaction_controller.create_flow(
                selected_agents, distributed_context, strategy
            )
            
            # 4. 执行编排策略
            result = await strategy.execute(orchestration_flow)
            
            # 5. 更新性能指标
            execution_time = time.time() - start_time
            self._update_metrics(selected_agents, execution_time, True)
            
            return OrchestrationResult(
                primary_result=result,
                participating_agents=selected_agents,
                context_usage=distributed_context,
                orchestration_metadata={
                    "orchestration_id": orchestration_id,
                    "strategy_used": strategy.__class__.__name__,
                    "execution_time": execution_time,
                    "agent_count": len(selected_agents),
                    "status": "completed"
                }
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            self._update_metrics([], execution_time, False)
            
            return OrchestrationResult(
                primary_result={"error": str(e)},
                participating_agents=[],
                orchestration_metadata={
                    "orchestration_id": orchestration_id,
                    "status": "failed",
                    "error": str(e),
                    "execution_time": execution_time
                }
            )
    
    async def orchestrate_tools(self, tool_calls: List[ToolCall],
                              context: ManagedContext,
                              execution_strategy: str = 'smart_parallel') -> AsyncIterator[Dict[str, Any]]:
        """编排工具执行（简化实现）"""
        
        # 这里应该集成智能工具调度器，目前提供基础实现
        for tool_call in tool_calls:
            yield {
                "type": "tool_execution_start",
                "tool_name": tool_call.tool_name,
                "call_id": tool_call.call_id
            }
            
            # 模拟工具执行
            await asyncio.sleep(0.1)
            
            yield {
                "type": "tool_execution_complete",
                "tool_name": tool_call.tool_name,
                "call_id": tool_call.call_id,
                "result": {"status": "success", "data": "mock_result"}
            }
    
    async def _analyze_intent(self, user_input: UserInput) -> Dict[str, Any]:
        """分析用户意图"""
        
        # 如果用户输入已经包含意图分析，直接使用
        if user_input.intent:
            return user_input.intent
        
        # 简化的意图分析
        message = user_input.message.lower()
        
        intent_indicators = {
            "analysis": ["analyze", "examine", "study", "investigate", "review"],
            "creation": ["create", "make", "build", "generate", "write"],
            "modification": ["update", "change", "modify", "edit", "fix"],
            "question": ["what", "how", "why", "when", "where", "?"]
        }
        
        intent_scores = {}
        for intent_type, indicators in intent_indicators.items():
            score = sum(1 for indicator in indicators if indicator in message)
            intent_scores[intent_type] = score
        
        primary_intent = max(intent_scores.items(), key=lambda x: x[1])[0]
        
        return {
            "primary_intent": primary_intent,
            "confidence": min(1.0, intent_scores[primary_intent] / 3),
            "all_scores": intent_scores,
            "complexity_indicators": {
                "word_count": len(user_input.message.split()),
                "has_multiple_sentences": "." in user_input.message,
                "has_conditionals": any(word in message for word in ["if", "when", "unless"]),
                "has_comparisons": any(word in message for word in ["than", "versus", "compare"])
            }
        }
    
    def _select_orchestration_strategy(self, intent: Dict[str, Any], 
                                     context: OrchestrationContext) -> 'OrchestrationStrategy':
        """选择编排策略"""
        
        # 简化的策略选择逻辑
        complexity_level = len([v for v in intent.get("complexity_indicators", {}).values() if v])
        agent_count = len(context.available_agents)
        
        # 默认策略选择
        if complexity_level > 3 and agent_count > 3:
            strategy_name = "hierarchical"
        elif agent_count > 2:
            strategy_name = "functional"
        else:
            strategy_name = "prior"
        
        # 从注册的策略中获取，如果没有注册则使用默认策略
        if strategy_name in self.orchestration_strategies:
            return self.orchestration_strategies[strategy_name]
        else:
            # 返回默认策略（后续在strategies模块中实现）
            from .strategies import DefaultOrchestrationStrategy
            return DefaultOrchestrationStrategy()
    
    def _update_metrics(self, agents: List[Agent], execution_time: float, success: bool):
        """更新编排指标"""
        
        self.orchestration_metrics["total_orchestrations"] += 1
        
        # 更新平均编排时间
        total_count = self.orchestration_metrics["total_orchestrations"]
        current_avg = self.orchestration_metrics["average_orchestration_time"]
        
        self.orchestration_metrics["average_orchestration_time"] = (
            (current_avg * (total_count - 1) + execution_time) / total_count
        )
        
        # 更新智能体利用率
        for agent in agents:
            if agent.agent_id not in self.orchestration_metrics["agent_utilization"]:
                self.orchestration_metrics["agent_utilization"][agent.agent_id] = 0
            self.orchestration_metrics["agent_utilization"][agent.agent_id] += 1
        
        # 更新成功率
        current_success_rate = self.orchestration_metrics["success_rate"]
        self.orchestration_metrics["success_rate"] = (
            (current_success_rate * (total_count - 1) + (1.0 if success else 0.0)) / total_count
        )
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """获取性能指标"""
        return self.orchestration_metrics.copy()
    
    async def get_orchestration_status(self) -> Dict[str, Any]:
        """获取编排状态"""
        
        active_flows = len(self.interaction_controller.active_flows)
        
        return {
            "active_flows": active_flows,
            "registered_strategies": list(self.orchestration_strategies.keys()),
            "performance_metrics": self.get_performance_metrics(),
            "system_health": "healthy" if active_flows < 10 else "busy"
        }