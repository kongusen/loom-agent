"""
编排策略实现

基于Claude Code的信息控制机制实现五种编排策略：
- Prior：预优先编排
- Posterior：后优先编排  
- Functional：功能化编排
- Component：组件化编排
- Puppeteer：木偶师编排
"""

import asyncio
import time
from typing import Dict, Any, List, Optional, AsyncIterator
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime

from ...types import Agent, ToolCall, ToolResult, OrchestrationStrategy


@dataclass
class ExecutionPlan:
    """执行计划"""
    strategy_type: str
    agent_assignments: Dict[str, List[str]]  # agent_id -> tasks
    dependency_graph: Dict[str, List[str]]  # task -> dependencies
    execution_order: List[str]
    parallel_groups: List[List[str]] = field(default_factory=list)
    coordination_points: List[str] = field(default_factory=list)


@dataclass 
class TaskAssignment:
    """任务分配"""
    task_id: str
    agent_id: str
    task_type: str
    priority: int = 0
    dependencies: List[str] = field(default_factory=list)
    estimated_duration: float = 0.0
    
    
class BaseOrchestrationStrategy(ABC):
    """基础编排策略抽象类"""
    
    def __init__(self, strategy_type: OrchestrationStrategy):
        self.strategy_type = strategy_type
        self.name = strategy_type.value
        self.execution_history: List[Dict[str, Any]] = []
        self.performance_metrics = {
            "total_executions": 0,
            "average_duration": 0.0,
            "success_rate": 0.0
        }
    
    @abstractmethod
    async def determine_agent_count(self, task_requirements: Dict[str, Any]) -> int:
        """确定所需智能体数量"""
        pass
    
    @abstractmethod 
    async def get_context_distribution_method(self) -> str:
        """获取上下文分发方法"""
        pass
    
    @abstractmethod
    async def create_execution_plan(self, agents: List[Agent], 
                                  context: Dict[str, Any]) -> Dict[str, Any]:
        """创建执行计划"""
        pass
    
    @abstractmethod
    async def execute(self, orchestration_flow) -> Dict[str, Any]:
        """执行编排策略"""
        pass
    
    def _record_execution(self, duration: float, success: bool, 
                         metadata: Dict[str, Any] = None):
        """记录执行结果"""
        
        execution_record = {
            "timestamp": datetime.now().isoformat(),
            "duration": duration,
            "success": success,
            "metadata": metadata or {}
        }
        
        self.execution_history.append(execution_record)
        
        # 更新性能指标
        self.performance_metrics["total_executions"] += 1
        total_count = self.performance_metrics["total_executions"]
        current_avg = self.performance_metrics["average_duration"]
        
        self.performance_metrics["average_duration"] = (
            (current_avg * (total_count - 1) + duration) / total_count
        )
        
        success_count = sum(1 for record in self.execution_history if record["success"])
        self.performance_metrics["success_rate"] = success_count / total_count


class PriorOrchestrationStrategy(BaseOrchestrationStrategy):
    """预优先编排策略
    
    在LLM响应前进行智能体协调，类似Claude Code的预处理机制
    """
    
    def __init__(self):
        super().__init__(OrchestrationStrategy.PRIOR)
    
    async def determine_agent_count(self, task_requirements: Dict[str, Any]) -> int:
        """根据任务复杂度确定智能体数量"""
        
        complexity = task_requirements.get("complexity_level", 1)
        collaboration_needed = task_requirements.get("collaboration_needed", False)
        
        if complexity >= 4 and collaboration_needed:
            return 3  # 高复杂度协作任务
        elif complexity >= 3 or collaboration_needed:
            return 2  # 中等复杂度或需要协作
        else:
            return 1  # 简单任务
    
    async def get_context_distribution_method(self) -> str:
        """使用广播分发确保所有智能体获得完整上下文"""
        return "broadcast"
    
    async def create_execution_plan(self, agents: List[Agent], 
                                  context: Dict[str, Any]) -> Dict[str, Any]:
        """创建预优先执行计划"""
        
        plan = ExecutionPlan(
            strategy_type="prior",
            agent_assignments={},
            dependency_graph={},
            execution_order=[]
        )
        
        if not agents:
            return plan.__dict__
        
        # Prior策略：所有智能体并行预处理
        primary_agent = agents[0]
        
        # 主智能体负责主要任务
        plan.agent_assignments[primary_agent.agent_id] = ["primary_analysis", "response_generation"]
        
        # 辅助智能体并行预处理
        for i, agent in enumerate(agents[1:], 1):
            plan.agent_assignments[agent.agent_id] = [f"context_preparation_{i}", f"knowledge_retrieval_{i}"]
        
        # 并行执行组
        if len(agents) > 1:
            parallel_group = [agent.agent_id for agent in agents[1:]]
            plan.parallel_groups.append(parallel_group)
        
        # 执行顺序：先并行预处理，后主要处理
        plan.execution_order = [
            "parallel_preprocessing",
            "primary_processing", 
            "result_synthesis"
        ]
        
        # 协调点
        plan.coordination_points = ["preprocessing_complete", "synthesis_ready"]
        
        return plan.__dict__
    
    async def execute(self, orchestration_flow) -> Dict[str, Any]:
        """执行预优先编排"""
        
        start_time = time.time()
        
        try:
            agents = orchestration_flow.selected_agents
            context_map = orchestration_flow.context_distribution
            
            if not agents:
                return {"status": "no_agents", "result": None}
            
            # Phase 1: 并行预处理
            preprocessing_results = await self._parallel_preprocessing(
                agents[1:] if len(agents) > 1 else [],
                context_map
            )
            
            # Phase 2: 主智能体处理（使用预处理结果）
            primary_result = await self._primary_processing(
                agents[0],
                context_map.get(agents[0].agent_id, {}),
                preprocessing_results
            )
            
            # Phase 3: 结果合成
            final_result = await self._synthesize_results(
                primary_result,
                preprocessing_results,
                agents
            )
            
            execution_time = time.time() - start_time
            self._record_execution(execution_time, True, {
                "agents_used": len(agents),
                "preprocessing_tasks": len(preprocessing_results)
            })
            
            return {
                "status": "completed",
                "strategy": "prior", 
                "result": final_result,
                "execution_time": execution_time,
                "preprocessing_results": preprocessing_results
            }
            
        except Exception as e:
            execution_time = time.time() - start_time
            self._record_execution(execution_time, False, {"error": str(e)})
            
            return {
                "status": "failed",
                "strategy": "prior",
                "error": str(e),
                "execution_time": execution_time
            }
    
    async def _parallel_preprocessing(self, agents: List[Agent], 
                                    context_map: Dict[str, Any]) -> List[Dict[str, Any]]:
        """并行预处理"""
        
        if not agents:
            return []
        
        async def preprocess_agent(agent: Agent) -> Dict[str, Any]:
            agent_context = context_map.get(agent.agent_id, {})
            
            # 模拟预处理任务
            await asyncio.sleep(0.1)
            
            return {
                "agent_id": agent.agent_id,
                "task": "preprocessing",
                "result": f"Preprocessed context for {agent.specialization}",
                "context_size": len(str(agent_context)),
                "completion_time": time.time()
            }
        
        tasks = [preprocess_agent(agent) for agent in agents]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 过滤异常结果
        valid_results = [r for r in results if not isinstance(r, Exception)]
        
        return valid_results
    
    async def _primary_processing(self, primary_agent: Agent, 
                                agent_context: Dict[str, Any],
                                preprocessing_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """主智能体处理"""
        
        # 模拟主要处理逻辑
        await asyncio.sleep(0.2)
        
        # 整合预处理结果
        integrated_context = {
            "primary_context": agent_context,
            "preprocessing_insights": [r["result"] for r in preprocessing_results],
            "context_enrichment": f"Enhanced by {len(preprocessing_results)} agents"
        }
        
        return {
            "agent_id": primary_agent.agent_id,
            "task": "primary_processing",
            "result": "Primary task completed with preprocessing insights",
            "integrated_context": integrated_context,
            "completion_time": time.time()
        }
    
    async def _synthesize_results(self, primary_result: Dict[str, Any],
                                preprocessing_results: List[Dict[str, Any]],
                                agents: List[Agent]) -> Dict[str, Any]:
        """合成最终结果"""
        
        return {
            "synthesis_type": "prior_orchestration",
            "primary_output": primary_result["result"],
            "preprocessing_contributions": len(preprocessing_results),
            "participating_agents": [agent.agent_id for agent in agents],
            "total_processing_time": time.time(),
            "coordination_effectiveness": "high" if preprocessing_results else "low"
        }


class PosteriorOrchestrationStrategy(BaseOrchestrationStrategy):
    """后优先编排策略
    
    在LLM响应后进行智能体协调，类似Claude Code的后处理机制
    """
    
    def __init__(self):
        super().__init__(OrchestrationStrategy.POSTERIOR)
    
    async def determine_agent_count(self, task_requirements: Dict[str, Any]) -> int:
        """后处理通常需要较少智能体"""
        
        complexity = task_requirements.get("complexity_level", 1)
        resource_intensity = task_requirements.get("resource_intensity", "low")
        
        if resource_intensity == "high":
            return 2
        elif complexity >= 3:
            return 2
        else:
            return 1
    
    async def get_context_distribution_method(self) -> str:
        """使用选择性分发，针对性处理"""
        return "selective"
    
    async def create_execution_plan(self, agents: List[Agent], 
                                  context: Dict[str, Any]) -> Dict[str, Any]:
        """创建后优先执行计划"""
        
        plan = ExecutionPlan(
            strategy_type="posterior",
            agent_assignments={},
            dependency_graph={},
            execution_order=[]
        )
        
        if not agents:
            return plan.__dict__
        
        primary_agent = agents[0]
        
        # 主智能体先执行主要任务
        plan.agent_assignments[primary_agent.agent_id] = [
            "initial_response", "primary_processing"
        ]
        
        # 后处理智能体处理特定任务
        for i, agent in enumerate(agents[1:], 1):
            specialization_tasks = self._get_specialization_tasks(agent.specialization)
            plan.agent_assignments[agent.agent_id] = specialization_tasks
        
        # 顺序执行
        plan.execution_order = [
            "primary_processing",
            "result_evaluation", 
            "specialized_post_processing",
            "final_integration"
        ]
        
        # 依赖关系
        plan.dependency_graph = {
            "result_evaluation": ["primary_processing"],
            "specialized_post_processing": ["result_evaluation"],
            "final_integration": ["specialized_post_processing"]
        }
        
        return plan.__dict__
    
    def _get_specialization_tasks(self, specialization: str) -> List[str]:
        """根据专业化获取任务"""
        
        task_mapping = {
            "data_analysis": ["result_validation", "statistical_analysis"],
            "code_generation": ["code_review", "optimization_suggestions"],
            "knowledge_retrieval": ["fact_checking", "source_verification"],
            "content_creation": ["style_analysis", "improvement_suggestions"]
        }
        
        return task_mapping.get(specialization, ["general_review"])
    
    async def execute(self, orchestration_flow) -> Dict[str, Any]:
        """执行后优先编排"""
        
        start_time = time.time()
        
        try:
            agents = orchestration_flow.selected_agents
            context_map = orchestration_flow.context_distribution
            
            if not agents:
                return {"status": "no_agents", "result": None}
            
            # Phase 1: 主智能体初始处理
            primary_result = await self._primary_processing(
                agents[0],
                context_map.get(agents[0].agent_id, {})
            )
            
            # Phase 2: 结果评估
            evaluation_result = await self._evaluate_result(primary_result)
            
            # Phase 3: 专业化后处理（如果需要）
            post_processing_results = []
            if len(agents) > 1 and evaluation_result.get("needs_improvement", False):
                post_processing_results = await self._specialized_post_processing(
                    agents[1:], 
                    context_map,
                    primary_result
                )
            
            # Phase 4: 最终整合
            final_result = await self._integrate_results(
                primary_result,
                evaluation_result,
                post_processing_results,
                agents
            )
            
            execution_time = time.time() - start_time
            self._record_execution(execution_time, True, {
                "agents_used": len(agents),
                "post_processing_tasks": len(post_processing_results)
            })
            
            return {
                "status": "completed",
                "strategy": "posterior",
                "result": final_result,
                "execution_time": execution_time,
                "evaluation": evaluation_result,
                "improvements": post_processing_results
            }
            
        except Exception as e:
            execution_time = time.time() - start_time
            self._record_execution(execution_time, False, {"error": str(e)})
            
            return {
                "status": "failed", 
                "strategy": "posterior",
                "error": str(e),
                "execution_time": execution_time
            }
    
    async def _primary_processing(self, primary_agent: Agent, 
                                agent_context: Dict[str, Any]) -> Dict[str, Any]:
        """主智能体处理"""
        
        await asyncio.sleep(0.2)
        
        return {
            "agent_id": primary_agent.agent_id,
            "initial_response": "Primary response generated",
            "processing_quality": "standard",
            "completion_time": time.time(),
            "context_utilization": len(str(agent_context))
        }
    
    async def _evaluate_result(self, primary_result: Dict[str, Any]) -> Dict[str, Any]:
        """评估初始结果"""
        
        await asyncio.sleep(0.05)
        
        # 简化的评估逻辑
        quality_score = 0.8  # 模拟质量评分
        
        return {
            "quality_score": quality_score,
            "needs_improvement": quality_score < 0.9,
            "improvement_areas": ["detail_enhancement", "accuracy_check"],
            "evaluation_time": time.time()
        }
    
    async def _specialized_post_processing(self, agents: List[Agent],
                                         context_map: Dict[str, Any],
                                         primary_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """专业化后处理"""
        
        async def post_process_agent(agent: Agent) -> Dict[str, Any]:
            agent_context = context_map.get(agent.agent_id, {})
            
            await asyncio.sleep(0.1)
            
            return {
                "agent_id": agent.agent_id,
                "specialization": agent.specialization,
                "improvement": f"Enhanced by {agent.specialization} specialist",
                "context_used": len(str(agent_context)),
                "completion_time": time.time()
            }
        
        tasks = [post_process_agent(agent) for agent in agents]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return [r for r in results if not isinstance(r, Exception)]
    
    async def _integrate_results(self, primary_result: Dict[str, Any],
                               evaluation_result: Dict[str, Any],
                               post_processing_results: List[Dict[str, Any]],
                               agents: List[Agent]) -> Dict[str, Any]:
        """整合所有结果"""
        
        return {
            "integration_type": "posterior_orchestration",
            "final_output": primary_result["initial_response"],
            "quality_improvements": len(post_processing_results),
            "quality_score": evaluation_result["quality_score"],
            "participating_agents": [agent.agent_id for agent in agents],
            "enhancement_details": [r["improvement"] for r in post_processing_results],
            "total_processing_time": time.time()
        }


class FunctionalOrchestrationStrategy(BaseOrchestrationStrategy):
    """功能化编排策略
    
    按功能模块分配智能体，类似Claude Code的模块化工具调用
    """
    
    def __init__(self):
        super().__init__(OrchestrationStrategy.FUNCTIONAL)
        self.function_registry = {
            "analysis": ["data_analysis", "code_analysis", "content_analysis"],
            "generation": ["code_generation", "content_creation", "response_generation"],
            "retrieval": ["knowledge_retrieval", "information_search", "context_gathering"],
            "validation": ["fact_checking", "code_review", "quality_assurance"]
        }
    
    async def determine_agent_count(self, task_requirements: Dict[str, Any]) -> int:
        """根据所需功能确定智能体数量"""
        
        domain_expertise = task_requirements.get("domain_expertise", [])
        complexity = task_requirements.get("complexity_level", 1)
        
        # 映射领域到功能
        required_functions = set()
        for domain in domain_expertise:
            for func, domains in self.function_registry.items():
                if any(d in domain for d in domains):
                    required_functions.add(func)
        
        # 基础功能至少需要1个智能体
        if not required_functions:
            required_functions.add("generation")
        
        # 复杂任务可能需要额外的验证功能
        if complexity >= 4:
            required_functions.add("validation")
        
        return min(len(required_functions), 4)  # 最多4个智能体
    
    async def get_context_distribution_method(self) -> str:
        """使用选择性分发，按功能分配上下文"""
        return "selective"
    
    async def create_execution_plan(self, agents: List[Agent], 
                                  context: Dict[str, Any]) -> Dict[str, Any]:
        """创建功能化执行计划"""
        
        plan = ExecutionPlan(
            strategy_type="functional",
            agent_assignments={},
            dependency_graph={},
            execution_order=[]
        )
        
        if not agents:
            return plan.__dict__
        
        # 分配功能角色
        functional_assignments = self._assign_functional_roles(agents)
        
        for agent_id, functions in functional_assignments.items():
            plan.agent_assignments[agent_id] = [
                f"{func}_task" for func in functions
            ]
        
        # 功能执行顺序
        execution_sequence = ["analysis", "retrieval", "generation", "validation"]
        
        plan.execution_order = [
            f"{func}_phase" for func in execution_sequence
            if any(func in assignment for assignment in functional_assignments.values())
        ]
        
        # 依赖关系：后续功能依赖前面的功能
        for i in range(1, len(plan.execution_order)):
            current_phase = plan.execution_order[i]
            previous_phase = plan.execution_order[i-1]
            plan.dependency_graph[current_phase] = [previous_phase]
        
        return plan.__dict__
    
    def _assign_functional_roles(self, agents: List[Agent]) -> Dict[str, List[str]]:
        """分配功能角色"""
        
        assignments = {}
        available_functions = ["analysis", "retrieval", "generation", "validation"]
        
        for i, agent in enumerate(agents):
            # 基于智能体能力分配功能
            agent_functions = []
            
            if any("analysis" in cap for cap in agent.capabilities):
                agent_functions.append("analysis")
            if any("retrieval" in cap for cap in agent.capabilities):
                agent_functions.append("retrieval")
            if any("generation" in cap for cap in agent.capabilities):
                agent_functions.append("generation")
            if any("review" in cap for cap in agent.capabilities):
                agent_functions.append("validation")
            
            # 如果没有匹配的能力，分配默认功能
            if not agent_functions:
                if i < len(available_functions):
                    agent_functions.append(available_functions[i])
                else:
                    agent_functions.append("generation")
            
            assignments[agent.agent_id] = agent_functions
        
        return assignments
    
    async def execute(self, orchestration_flow) -> Dict[str, Any]:
        """执行功能化编排"""
        
        start_time = time.time()
        
        try:
            agents = orchestration_flow.selected_agents
            context_map = orchestration_flow.context_distribution
            execution_plan = orchestration_flow.execution_plan
            
            if not agents:
                return {"status": "no_agents", "result": None}
            
            # 获取功能分配
            functional_assignments = self._assign_functional_roles(agents)
            
            # 按功能顺序执行
            execution_results = {}
            accumulated_context = {}
            
            for function in ["analysis", "retrieval", "generation", "validation"]:
                # 找到负责此功能的智能体
                responsible_agents = [
                    agent for agent in agents
                    if function in functional_assignments.get(agent.agent_id, [])
                ]
                
                if responsible_agents:
                    function_result = await self._execute_function_phase(
                        function,
                        responsible_agents,
                        context_map,
                        accumulated_context
                    )
                    
                    execution_results[function] = function_result
                    
                    # 累积上下文供后续功能使用
                    accumulated_context[function] = function_result
            
            # 整合所有功能结果
            final_result = await self._integrate_functional_results(
                execution_results,
                functional_assignments,
                agents
            )
            
            execution_time = time.time() - start_time
            self._record_execution(execution_time, True, {
                "functions_executed": len(execution_results),
                "agents_used": len(agents)
            })
            
            return {
                "status": "completed",
                "strategy": "functional",
                "result": final_result,
                "execution_time": execution_time,
                "function_results": execution_results,
                "functional_assignments": functional_assignments
            }
            
        except Exception as e:
            execution_time = time.time() - start_time
            self._record_execution(execution_time, False, {"error": str(e)})
            
            return {
                "status": "failed",
                "strategy": "functional", 
                "error": str(e),
                "execution_time": execution_time
            }
    
    async def _execute_function_phase(self, function: str,
                                    agents: List[Agent],
                                    context_map: Dict[str, Any],
                                    accumulated_context: Dict[str, Any]) -> Dict[str, Any]:
        """执行功能阶段"""
        
        async def execute_agent_function(agent: Agent) -> Dict[str, Any]:
            agent_context = context_map.get(agent.agent_id, {})
            
            # 合并累积上下文
            enhanced_context = {**agent_context, **accumulated_context}
            
            await asyncio.sleep(0.1)  # 模拟处理时间
            
            return {
                "agent_id": agent.agent_id,
                "function": function,
                "result": f"{function.title()} completed by {agent.specialization}",
                "context_size": len(str(enhanced_context)),
                "completion_time": time.time()
            }
        
        # 并行执行同功能的智能体
        tasks = [execute_agent_function(agent) for agent in agents]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        valid_results = [r for r in results if not isinstance(r, Exception)]
        
        return {
            "function_type": function,
            "agent_results": valid_results,
            "execution_count": len(valid_results),
            "phase_completion_time": time.time()
        }
    
    async def _integrate_functional_results(self, execution_results: Dict[str, Any],
                                          functional_assignments: Dict[str, List[str]],
                                          agents: List[Agent]) -> Dict[str, Any]:
        """整合功能结果"""
        
        return {
            "integration_type": "functional_orchestration",
            "functions_completed": list(execution_results.keys()),
            "total_function_phases": len(execution_results),
            "participating_agents": [agent.agent_id for agent in agents],
            "functional_pipeline": [
                {
                    "function": func,
                    "agent_count": len(result["agent_results"]),
                    "output": f"{func} processing complete"
                }
                for func, result in execution_results.items()
            ],
            "integration_time": time.time()
        }


class ComponentOrchestrationStrategy(BaseOrchestrationStrategy):
    """组件化编排策略
    
    将任务分解为独立组件，智能体负责不同组件，类似Claude Code的组件化架构
    """
    
    def __init__(self):
        super().__init__(OrchestrationStrategy.COMPONENT)
        self.component_types = [
            "input_processing", "context_analysis", "core_logic", 
            "output_formatting", "quality_control"
        ]
    
    async def determine_agent_count(self, task_requirements: Dict[str, Any]) -> int:
        """根据组件复杂度确定智能体数量"""
        
        complexity = task_requirements.get("complexity_level", 1)
        collaboration_needed = task_requirements.get("collaboration_needed", False)
        
        if complexity >= 4:
            return min(4, len(self.component_types))  # 高复杂度需要更多组件
        elif complexity >= 3 or collaboration_needed:
            return 3  # 中等复杂度
        else:
            return 2  # 基础组件
    
    async def get_context_distribution_method(self) -> str:
        """使用分层分发，主组件获得完整上下文"""
        return "hierarchical"
    
    async def create_execution_plan(self, agents: List[Agent], 
                                  context: Dict[str, Any]) -> Dict[str, Any]:
        """创建组件化执行计划"""
        
        plan = ExecutionPlan(
            strategy_type="component",
            agent_assignments={},
            dependency_graph={},
            execution_order=[]
        )
        
        if not agents:
            return plan.__dict__
        
        # 分配组件角色
        component_assignments = self._assign_component_roles(agents)
        
        for agent_id, component in component_assignments.items():
            plan.agent_assignments[agent_id] = [f"{component}_processing"]
        
        # 组件执行顺序（流水线）
        assigned_components = list(component_assignments.values())
        plan.execution_order = [f"{comp}_phase" for comp in assigned_components]
        
        # 依赖关系：流水线依赖
        for i in range(1, len(plan.execution_order)):
            current_phase = plan.execution_order[i]
            previous_phase = plan.execution_order[i-1]
            plan.dependency_graph[current_phase] = [previous_phase]
        
        return plan.__dict__
    
    def _assign_component_roles(self, agents: List[Agent]) -> Dict[str, str]:
        """分配组件角色"""
        
        assignments = {}
        
        # 确定需要的组件数量
        num_components = min(len(agents), len(self.component_types))
        selected_components = self.component_types[:num_components]
        
        for i, agent in enumerate(agents[:num_components]):
            assignments[agent.agent_id] = selected_components[i]
        
        return assignments
    
    async def execute(self, orchestration_flow) -> Dict[str, Any]:
        """执行组件化编排"""
        
        start_time = time.time()
        
        try:
            agents = orchestration_flow.selected_agents
            context_map = orchestration_flow.context_distribution
            
            if not agents:
                return {"status": "no_agents", "result": None}
            
            # 获取组件分配
            component_assignments = self._assign_component_roles(agents)
            
            # 流水线执行组件
            pipeline_results = {}
            current_output = None
            
            for agent in agents:
                component = component_assignments.get(agent.agent_id)
                if component:
                    component_result = await self._execute_component(
                        component,
                        agent,
                        context_map.get(agent.agent_id, {}),
                        current_output
                    )
                    
                    pipeline_results[component] = component_result
                    current_output = component_result  # 传递给下一个组件
            
            # 整合流水线结果
            final_result = await self._integrate_pipeline_results(
                pipeline_results,
                component_assignments,
                agents
            )
            
            execution_time = time.time() - start_time
            self._record_execution(execution_time, True, {
                "components_executed": len(pipeline_results),
                "agents_used": len(agents)
            })
            
            return {
                "status": "completed",
                "strategy": "component",
                "result": final_result,
                "execution_time": execution_time,
                "pipeline_results": pipeline_results,
                "component_assignments": component_assignments
            }
            
        except Exception as e:
            execution_time = time.time() - start_time
            self._record_execution(execution_time, False, {"error": str(e)})
            
            return {
                "status": "failed",
                "strategy": "component",
                "error": str(e),
                "execution_time": execution_time
            }
    
    async def _execute_component(self, component: str,
                               agent: Agent,
                               agent_context: Dict[str, Any],
                               input_from_previous: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """执行单个组件"""
        
        await asyncio.sleep(0.1)  # 模拟处理时间
        
        # 合并输入
        component_input = {
            "agent_context": agent_context,
            "previous_output": input_from_previous
        }
        
        return {
            "component_type": component,
            "agent_id": agent.agent_id,
            "input_size": len(str(component_input)),
            "output": f"{component} processing complete",
            "processing_metadata": {
                "component_specialization": agent.specialization,
                "has_previous_input": input_from_previous is not None
            },
            "completion_time": time.time()
        }
    
    async def _integrate_pipeline_results(self, pipeline_results: Dict[str, Any],
                                        component_assignments: Dict[str, str],
                                        agents: List[Agent]) -> Dict[str, Any]:
        """整合流水线结果"""
        
        return {
            "integration_type": "component_orchestration",
            "pipeline_stages": list(pipeline_results.keys()),
            "total_components": len(pipeline_results),
            "participating_agents": [agent.agent_id for agent in agents],
            "pipeline_flow": [
                {
                    "stage": component,
                    "agent": agent_id,
                    "output": result["output"]
                }
                for component, result in pipeline_results.items()
                for agent_id, assigned_component in component_assignments.items()
                if assigned_component == component
            ],
            "integration_time": time.time()
        }


class PuppeteerOrchestrationStrategy(BaseOrchestrationStrategy):
    """木偶师编排策略
    
    一个主智能体控制其他智能体，类似Claude Code中的主控制器模式
    """
    
    def __init__(self):
        super().__init__(OrchestrationStrategy.PUPPETEER)
        self.control_commands = [
            "delegate_task", "collect_results", "coordinate_timing", 
            "resolve_conflicts", "optimize_performance"
        ]
    
    async def determine_agent_count(self, task_requirements: Dict[str, Any]) -> int:
        """木偶师策略需要1个主控制器 + 多个受控智能体"""
        
        complexity = task_requirements.get("complexity_level", 1)
        collaboration_needed = task_requirements.get("collaboration_needed", False)
        
        if complexity >= 4 and collaboration_needed:
            return 4  # 1个主控制器 + 3个受控智能体
        elif complexity >= 3 or collaboration_needed:
            return 3  # 1个主控制器 + 2个受控智能体
        else:
            return 2  # 1个主控制器 + 1个受控智能体
    
    async def get_context_distribution_method(self) -> str:
        """使用分层分发，主控制器获得完整信息"""
        return "hierarchical"
    
    async def create_execution_plan(self, agents: List[Agent], 
                                  context: Dict[str, Any]) -> Dict[str, Any]:
        """创建木偶师执行计划"""
        
        plan = ExecutionPlan(
            strategy_type="puppeteer",
            agent_assignments={},
            dependency_graph={},
            execution_order=[]
        )
        
        if not agents:
            return plan.__dict__
        
        # 第一个智能体是主控制器（木偶师）
        puppeteer_agent = agents[0]
        puppet_agents = agents[1:]
        
        # 主控制器任务
        plan.agent_assignments[puppeteer_agent.agent_id] = [
            "control_coordination", "task_delegation", "result_integration"
        ]
        
        # 受控智能体任务
        for i, puppet in enumerate(puppet_agents):
            plan.agent_assignments[puppet.agent_id] = [f"execute_subtask_{i+1}"]
        
        # 执行顺序：主控制器指挥，受控智能体并行执行
        plan.execution_order = [
            "puppeteer_initialization",
            "parallel_puppet_execution", 
            "puppeteer_coordination",
            "result_collection"
        ]
        
        # 并行组：所有受控智能体
        if puppet_agents:
            plan.parallel_groups.append([agent.agent_id for agent in puppet_agents])
        
        # 协调点
        plan.coordination_points = [
            "delegation_complete", "execution_synchronized", "collection_ready"
        ]
        
        return plan.__dict__
    
    async def execute(self, orchestration_flow) -> Dict[str, Any]:
        """执行木偶师编排"""
        
        start_time = time.time()
        
        try:
            agents = orchestration_flow.selected_agents
            context_map = orchestration_flow.context_distribution
            
            if not agents:
                return {"status": "no_agents", "result": None}
            
            puppeteer_agent = agents[0]
            puppet_agents = agents[1:]
            
            # Phase 1: 木偶师初始化和任务分析
            coordination_plan = await self._puppeteer_initialization(
                puppeteer_agent,
                context_map.get(puppeteer_agent.agent_id, {}),
                puppet_agents
            )
            
            # Phase 2: 并行执行受控任务
            puppet_results = await self._parallel_puppet_execution(
                puppet_agents,
                context_map,
                coordination_plan
            )
            
            # Phase 3: 木偶师协调和控制
            coordination_result = await self._puppeteer_coordination(
                puppeteer_agent,
                puppet_results,
                coordination_plan
            )
            
            # Phase 4: 结果收集和整合
            final_result = await self._collect_and_integrate_results(
                puppeteer_agent,
                puppet_results,
                coordination_result,
                agents
            )
            
            execution_time = time.time() - start_time
            self._record_execution(execution_time, True, {
                "puppets_controlled": len(puppet_agents),
                "coordination_cycles": 1
            })
            
            return {
                "status": "completed",
                "strategy": "puppeteer",
                "result": final_result,
                "execution_time": execution_time,
                "coordination_plan": coordination_plan,
                "puppet_results": puppet_results
            }
            
        except Exception as e:
            execution_time = time.time() - start_time
            self._record_execution(execution_time, False, {"error": str(e)})
            
            return {
                "status": "failed",
                "strategy": "puppeteer",
                "error": str(e),
                "execution_time": execution_time
            }
    
    async def _puppeteer_initialization(self, puppeteer: Agent,
                                      puppeteer_context: Dict[str, Any],
                                      puppet_agents: List[Agent]) -> Dict[str, Any]:
        """木偶师初始化"""
        
        await asyncio.sleep(0.1)
        
        # 分析任务并制定控制计划
        coordination_plan = {
            "puppeteer_id": puppeteer.agent_id,
            "puppet_assignments": {},
            "control_strategy": "parallel_with_checkpoints",
            "coordination_intervals": 3,
            "expected_duration": 1.0
        }
        
        # 为每个受控智能体分配具体任务
        for i, puppet in enumerate(puppet_agents):
            task_assignment = {
                "task_id": f"subtask_{i+1}",
                "specialization_focus": puppet.specialization,
                "expected_output": f"Specialized result from {puppet.specialization}",
                "control_checkpoints": ["start", "midpoint", "completion"]
            }
            coordination_plan["puppet_assignments"][puppet.agent_id] = task_assignment
        
        return coordination_plan
    
    async def _parallel_puppet_execution(self, puppet_agents: List[Agent],
                                       context_map: Dict[str, Any],
                                       coordination_plan: Dict[str, Any]) -> List[Dict[str, Any]]:
        """并行执行受控任务"""
        
        async def execute_puppet_task(puppet: Agent) -> Dict[str, Any]:
            puppet_context = context_map.get(puppet.agent_id, {})
            assignment = coordination_plan["puppet_assignments"].get(puppet.agent_id, {})
            
            await asyncio.sleep(0.2)  # 模拟执行时间
            
            return {
                "puppet_id": puppet.agent_id,
                "task_id": assignment.get("task_id", "unknown"),
                "specialization": puppet.specialization,
                "result": f"Completed {assignment.get('specialization_focus', 'task')}",
                "control_status": "responsive",
                "execution_metadata": {
                    "context_size": len(str(puppet_context)),
                    "checkpoints_hit": len(assignment.get("control_checkpoints", []))
                },
                "completion_time": time.time()
            }
        
        tasks = [execute_puppet_task(puppet) for puppet in puppet_agents]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return [r for r in results if not isinstance(r, Exception)]
    
    async def _puppeteer_coordination(self, puppeteer: Agent,
                                    puppet_results: List[Dict[str, Any]],
                                    coordination_plan: Dict[str, Any]) -> Dict[str, Any]:
        """木偶师协调控制"""
        
        await asyncio.sleep(0.1)
        
        # 评估受控智能体的执行情况
        coordination_quality = len([r for r in puppet_results if r.get("control_status") == "responsive"])
        total_puppets = len(puppet_results)
        
        coordination_effectiveness = coordination_quality / total_puppets if total_puppets > 0 else 0
        
        return {
            "coordination_type": "puppeteer_control",
            "puppeteer_id": puppeteer.agent_id,
            "coordination_effectiveness": coordination_effectiveness,
            "puppet_responsiveness": f"{coordination_quality}/{total_puppets}",
            "control_commands_issued": len(self.control_commands),
            "coordination_time": time.time()
        }
    
    async def _collect_and_integrate_results(self, puppeteer: Agent,
                                           puppet_results: List[Dict[str, Any]],
                                           coordination_result: Dict[str, Any],
                                           all_agents: List[Agent]) -> Dict[str, Any]:
        """收集和整合结果"""
        
        return {
            "integration_type": "puppeteer_orchestration",
            "master_controller": puppeteer.agent_id,
            "controlled_agents": [r["puppet_id"] for r in puppet_results],
            "coordination_effectiveness": coordination_result["coordination_effectiveness"],
            "puppet_outputs": [r["result"] for r in puppet_results],
            "control_summary": f"Puppeteer {puppeteer.agent_id} controlled {len(puppet_results)} agents",
            "total_agents": len(all_agents),
            "integration_time": time.time()
        }


class DefaultOrchestrationStrategy(BaseOrchestrationStrategy):
    """默认编排策略，用于未指定策略时的回退"""
    
    def __init__(self):
        super().__init__(OrchestrationStrategy.FUNCTIONAL)
    
    async def determine_agent_count(self, task_requirements: Dict[str, Any]) -> int:
        return 1  # 默认单智能体
    
    async def get_context_distribution_method(self) -> str:
        return "broadcast"  # 默认广播
    
    async def create_execution_plan(self, agents: List[Agent], 
                                  context: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "strategy_type": "default",
            "agent_assignments": {agent.agent_id: ["default_task"] for agent in agents},
            "execution_order": ["default_execution"],
            "dependency_graph": {}
        }
    
    async def execute(self, orchestration_flow) -> Dict[str, Any]:
        """执行默认策略"""
        
        start_time = time.time()
        
        try:
            agents = orchestration_flow.selected_agents
            
            if not agents:
                return {"status": "no_agents", "result": None}
            
            # 简单执行第一个智能体
            primary_agent = agents[0]
            
            await asyncio.sleep(0.1)  # 模拟处理
            
            result = {
                "default_execution": f"Task completed by {primary_agent.agent_id}",
                "agent_used": primary_agent.agent_id,
                "execution_type": "default_single_agent"
            }
            
            execution_time = time.time() - start_time
            self._record_execution(execution_time, True)
            
            return {
                "status": "completed",
                "strategy": "default",
                "result": result,
                "execution_time": execution_time
            }
            
        except Exception as e:
            execution_time = time.time() - start_time
            self._record_execution(execution_time, False, {"error": str(e)})
            
            return {
                "status": "failed",
                "strategy": "default",
                "error": str(e),
                "execution_time": execution_time
            }