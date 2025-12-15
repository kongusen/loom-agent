"""
Crew 路由系统 - 智能任务分配 (Loom Agent v0.1.7+)

将任务智能路由到最合适的 Agent，支持：
- Agent 能力注册和匹配
- 任务分类和分析
- 多种路由策略
- 与递归控制模式无缝集成
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional, Union, Callable
import re

from loom.core.base_agent import BaseAgent
from loom.core.message import Message


# ============================================================================
# Agent 能力描述
# ============================================================================


class AgentType(str, Enum):
    """Agent 类型"""
    SIMPLE = "simple"  # 简单对话
    REACT = "react"  # ReAct 推理
    REFLECTION = "reflection"  # 反思循环
    TREE_OF_THOUGHTS = "tree_of_thoughts"  # 思维树
    PLAN_EXECUTOR = "plan_executor"  # 规划执行
    CUSTOM = "custom"  # 自定义


class ComplexityLevel(str, Enum):
    """任务复杂度级别"""
    SIMPLE = "simple"  # 简单任务（1-2步）
    MEDIUM = "medium"  # 中等任务（3-5步）
    COMPLEX = "complex"  # 复杂任务（6+步）
    EXPERT = "expert"  # 专家级任务（需要深度推理）


@dataclass
class AgentCapability:
    """
    Agent 能力描述

    定义一个 Agent 的能力特征，用于路由决策

    Example:
        capability = AgentCapability(
            agent_type=AgentType.REACT,
            capabilities=["research", "web_search"],
            has_tools=True,
            complexity_level=ComplexityLevel.MEDIUM,
            tags=["research", "information_gathering"]
        )
    """

    # 基本信息
    agent_type: AgentType = AgentType.SIMPLE
    capabilities: List[str] = field(default_factory=list)

    # 能力特征
    has_tools: bool = False
    has_recursive_control: bool = False
    complexity_level: ComplexityLevel = ComplexityLevel.SIMPLE

    # 标签和元数据
    tags: List[str] = field(default_factory=list)
    description: str = ""
    priority: int = 0  # 优先级（越高越优先）

    # 性能特征
    avg_response_time: float = 0.0  # 平均响应时间（秒）
    success_rate: float = 1.0  # 成功率

    def matches(self, required_capabilities: List[str]) -> bool:
        """检查是否匹配所需能力"""
        if not required_capabilities:
            return True
        return any(cap in self.capabilities for cap in required_capabilities)

    def matches_tags(self, required_tags: List[str]) -> bool:
        """检查是否匹配所需标签"""
        if not required_tags:
            return True
        return any(tag in self.tags for tag in required_tags)

    def score(self, task_complexity: ComplexityLevel) -> float:
        """
        计算与任务复杂度的匹配分数

        Returns:
            0-1 之间的分数，1 表示完美匹配
        """
        complexity_map = {
            ComplexityLevel.SIMPLE: 1,
            ComplexityLevel.MEDIUM: 2,
            ComplexityLevel.COMPLEX: 3,
            ComplexityLevel.EXPERT: 4,
        }

        agent_level = complexity_map[self.complexity_level]
        task_level = complexity_map[task_complexity]

        # 如果 Agent 能力高于任务要求，分数略降
        if agent_level >= task_level:
            return 1.0 - (agent_level - task_level) * 0.1
        else:
            # Agent 能力低于任务要求，大幅降分
            return max(0.0, 1.0 - (task_level - agent_level) * 0.3)


# ============================================================================
# 任务分类
# ============================================================================


@dataclass
class TaskCharacteristics:
    """
    任务特征

    描述一个任务的特征，用于路由决策
    """

    # 复杂度
    complexity: ComplexityLevel = ComplexityLevel.SIMPLE
    estimated_steps: int = 1

    # 所需能力
    required_capabilities: List[str] = field(default_factory=list)
    required_tags: List[str] = field(default_factory=list)

    # 任务类型
    task_type: str = "general"  # general, research, writing, analysis, coding, etc.

    # 其他特征
    requires_tools: bool = False
    requires_reasoning: bool = False
    requires_planning: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "complexity": self.complexity.value,
            "estimated_steps": self.estimated_steps,
            "required_capabilities": self.required_capabilities,
            "required_tags": self.required_tags,
            "task_type": self.task_type,
            "requires_tools": self.requires_tools,
            "requires_reasoning": self.requires_reasoning,
            "requires_planning": self.requires_planning,
        }


class TaskClassifier:
    """
    任务分类器

    分析任务特征，为路由提供决策依据

    Example:
        classifier = TaskClassifier()
        characteristics = classifier.classify("研究并分析 AI 的发展趋势")
        print(characteristics.complexity)  # ComplexityLevel.COMPLEX
        print(characteristics.required_capabilities)  # ["research", "analysis"]
    """

    def __init__(
        self,
        llm: Optional[BaseAgent] = None,
        use_llm: bool = False,
    ):
        """
        Args:
            llm: LLM Agent（用于基于 LLM 的分类）
            use_llm: 是否使用 LLM 进行分类（更准确但更慢）
        """
        self.llm = llm
        self.use_llm = use_llm

        # 关键词映射
        self.capability_keywords = {
            "research": ["研究", "调查", "搜索", "查找", "探索", "research", "search", "investigate"],
            "writing": ["写", "撰写", "编写", "创作", "write", "compose", "draft"],
            "analysis": ["分析", "评估", "比较", "总结", "analyze", "evaluate", "compare", "summarize"],
            "coding": ["代码", "编程", "开发", "实现", "code", "program", "develop", "implement"],
            "calculation": ["计算", "算", "数学", "统计", "calculate", "compute", "math", "statistics"],
            "translation": ["翻译", "转换", "translate", "convert"],
            "qa": ["问答", "回答", "解释", "说明", "answer", "explain", "clarify"],
        }

        self.tool_keywords = ["搜索", "查找", "获取", "下载", "search", "fetch", "get", "download", "调用", "call"]
        self.reasoning_keywords = ["分析", "推理", "思考", "判断", "analyze", "reason", "think", "judge"]
        self.planning_keywords = ["计划", "规划", "步骤", "流程", "plan", "steps", "process", "workflow"]

    def classify(self, task: str) -> TaskCharacteristics:
        """
        分类任务

        Args:
            task: 任务描述

        Returns:
            任务特征
        """
        if self.use_llm and self.llm:
            return self._classify_with_llm(task)
        else:
            return self._classify_with_rules(task)

    def _classify_with_rules(self, task: str) -> TaskCharacteristics:
        """基于规则的分类（快速）"""
        characteristics = TaskCharacteristics()

        task_lower = task.lower()

        # 1. 检测所需能力
        for capability, keywords in self.capability_keywords.items():
            if any(kw in task_lower for kw in keywords):
                characteristics.required_capabilities.append(capability)

        # 2. 检测是否需要工具
        characteristics.requires_tools = any(kw in task_lower for kw in self.tool_keywords)

        # 3. 检测是否需要推理
        characteristics.requires_reasoning = any(kw in task_lower for kw in self.reasoning_keywords)

        # 4. 检测是否需要规划
        characteristics.requires_planning = any(kw in task_lower for kw in self.planning_keywords)

        # 5. 估计复杂度
        # 简单规则：包含多个关键动词 = 更复杂
        action_verbs = len(re.findall(r'(研究|分析|写|创建|实现|搜索|计算|翻译)', task))

        if action_verbs == 0:
            action_verbs = len(re.findall(r'(research|analyze|write|create|implement|search|calculate|translate)', task_lower))

        if "并" in task or "然后" in task or "接着" in task or "and then" in task_lower:
            characteristics.estimated_steps = max(2, action_verbs)
        else:
            characteristics.estimated_steps = max(1, action_verbs)

        # 根据步骤数判断复杂度
        if characteristics.estimated_steps <= 2:
            characteristics.complexity = ComplexityLevel.SIMPLE
        elif characteristics.estimated_steps <= 5:
            characteristics.complexity = ComplexityLevel.MEDIUM
        elif characteristics.estimated_steps <= 10:
            characteristics.complexity = ComplexityLevel.COMPLEX
        else:
            characteristics.complexity = ComplexityLevel.EXPERT

        # 6. 确定任务类型
        if "research" in characteristics.required_capabilities:
            characteristics.task_type = "research"
        elif "writing" in characteristics.required_capabilities:
            characteristics.task_type = "writing"
        elif "analysis" in characteristics.required_capabilities:
            characteristics.task_type = "analysis"
        elif "coding" in characteristics.required_capabilities:
            characteristics.task_type = "coding"
        else:
            characteristics.task_type = "general"

        return characteristics

    async def _classify_with_llm(self, task: str) -> TaskCharacteristics:
        """基于 LLM 的分类（更准确）"""
        if not self.llm:
            return self._classify_with_rules(task)

        prompt = f"""Analyze this task and provide its characteristics:

Task: {task}

Please analyze:
1. Complexity level (simple/medium/complex/expert)
2. Estimated steps required
3. Required capabilities (e.g., research, writing, analysis)
4. Whether it requires tools
5. Whether it requires reasoning
6. Whether it requires planning

Respond in JSON format:
{{
    "complexity": "simple|medium|complex|expert",
    "estimated_steps": <number>,
    "required_capabilities": ["capability1", "capability2"],
    "requires_tools": true|false,
    "requires_reasoning": true|false,
    "requires_planning": true|false
}}"""

        message = Message(role="user", content=prompt)
        response = await self.llm.run(message)

        try:
            import json
            data = json.loads(response.content)

            return TaskCharacteristics(
                complexity=ComplexityLevel(data["complexity"]),
                estimated_steps=data["estimated_steps"],
                required_capabilities=data["required_capabilities"],
                requires_tools=data["requires_tools"],
                requires_reasoning=data["requires_reasoning"],
                requires_planning=data["requires_planning"],
            )
        except Exception:
            # 解析失败，回退到规则方法
            return self._classify_with_rules(task)


# ============================================================================
# 路由策略
# ============================================================================


class RoutingStrategy(str, Enum):
    """路由策略"""
    AUTO = "auto"  # 自动（基于任务分析和能力匹配）
    RULE_BASED = "rule_based"  # 基于规则
    LLM_BASED = "llm_based"  # 基于 LLM 决策
    ROUND_ROBIN = "round_robin"  # 轮询
    CAPABILITY_MATCH = "capability_match"  # 能力匹配
    PRIORITY = "priority"  # 优先级
    LOAD_BALANCE = "load_balance"  # 负载均衡


@dataclass
class RoutingResult:
    """路由结果"""
    agent: BaseAgent
    capability: AgentCapability
    score: float  # 匹配分数
    reason: str  # 选择原因


class Router:
    """
    智能路由器

    将任务路由到最合适的 Agent

    Example:
        # 创建路由器
        router = Router(strategy=RoutingStrategy.AUTO)

        # 注册 Agents
        router.register_agent(
            agent=simple_agent,
            capability=AgentCapability(
                agent_type=AgentType.SIMPLE,
                capabilities=["qa", "chat"],
                complexity_level=ComplexityLevel.SIMPLE
            )
        )

        router.register_agent(
            agent=research_agent,
            capability=AgentCapability(
                agent_type=AgentType.REACT,
                capabilities=["research", "web_search"],
                has_tools=True,
                complexity_level=ComplexityLevel.MEDIUM
            )
        )

        # 路由任务
        result = await router.route("研究 AI 的发展趋势")
        agent = result.agent
        print(f"Selected: {result.capability.agent_type} (score: {result.score})")
    """

    def __init__(
        self,
        strategy: RoutingStrategy = RoutingStrategy.AUTO,
        classifier: Optional[TaskClassifier] = None,
        rules: Optional[Dict[str, BaseAgent]] = None,
        llm: Optional[BaseAgent] = None,
    ):
        """
        Args:
            strategy: 路由策略
            classifier: 任务分类器
            rules: 规则映射（用于 RULE_BASED 策略）
            llm: LLM Agent（用于 LLM_BASED 策略）
        """
        self.strategy = strategy
        self.classifier = classifier or TaskClassifier()
        self.rules = rules or {}
        self.llm = llm

        # Agent 注册表
        self.agents: List[BaseAgent] = []
        self.capabilities: Dict[BaseAgent, AgentCapability] = {}

        # 轮询计数器
        self._round_robin_index = 0

        # 负载统计
        self.load_stats: Dict[BaseAgent, int] = {}

    def register_agent(
        self,
        agent: BaseAgent,
        capability: Optional[AgentCapability] = None,
    ) -> None:
        """
        注册 Agent

        Args:
            agent: Agent 实例
            capability: Agent 能力描述（如果为 None，将自动推断）
        """
        if agent in self.agents:
            # 更新能力
            self.capabilities[agent] = capability or self._infer_capability(agent)
            return

        self.agents.append(agent)
        self.capabilities[agent] = capability or self._infer_capability(agent)
        self.load_stats[agent] = 0

    def _infer_capability(self, agent: BaseAgent) -> AgentCapability:
        """自动推断 Agent 能力"""
        capability = AgentCapability()

        # 检查是否有工具
        if hasattr(agent, "tools") and agent.tools:
            capability.has_tools = True
            capability.complexity_level = ComplexityLevel.MEDIUM

        # 检查是否有 react_mode
        if hasattr(agent, "react_mode") and agent.react_mode:
            capability.agent_type = AgentType.REACT
            capability.has_recursive_control = False

        # 检查是否是递归控制包装
        if hasattr(agent, "__class__"):
            class_name = agent.__class__.__name__
            if "Reflection" in class_name:
                capability.agent_type = AgentType.REFLECTION
                capability.has_recursive_control = True
                capability.complexity_level = ComplexityLevel.COMPLEX
            elif "TreeOfThoughts" in class_name or "ToT" in class_name:
                capability.agent_type = AgentType.TREE_OF_THOUGHTS
                capability.has_recursive_control = True
                capability.complexity_level = ComplexityLevel.EXPERT
            elif "PlanExecutor" in class_name:
                capability.agent_type = AgentType.PLAN_EXECUTOR
                capability.has_recursive_control = True
                capability.complexity_level = ComplexityLevel.COMPLEX

        return capability

    async def route(self, task: str) -> RoutingResult:
        """
        路由任务到合适的 Agent

        Args:
            task: 任务描述

        Returns:
            路由结果
        """
        if not self.agents:
            raise ValueError("No agents registered in router")

        if self.strategy == RoutingStrategy.AUTO:
            return await self._route_auto(task)
        elif self.strategy == RoutingStrategy.RULE_BASED:
            return self._route_rule_based(task)
        elif self.strategy == RoutingStrategy.LLM_BASED:
            return await self._route_llm_based(task)
        elif self.strategy == RoutingStrategy.ROUND_ROBIN:
            return self._route_round_robin()
        elif self.strategy == RoutingStrategy.CAPABILITY_MATCH:
            return await self._route_capability_match(task)
        elif self.strategy == RoutingStrategy.PRIORITY:
            return self._route_priority()
        elif self.strategy == RoutingStrategy.LOAD_BALANCE:
            return self._route_load_balance()
        else:
            # 默认使用第一个 Agent
            agent = self.agents[0]
            return RoutingResult(
                agent=agent,
                capability=self.capabilities[agent],
                score=1.0,
                reason="Default fallback"
            )

    async def _route_auto(self, task: str) -> RoutingResult:
        """自动路由（推荐）"""
        # 1. 分类任务
        characteristics = self.classifier.classify(task)

        # 2. 计算每个 Agent 的匹配分数
        best_agent = None
        best_score = -1.0
        best_capability = None

        for agent in self.agents:
            capability = self.capabilities[agent]

            # 基础分数：复杂度匹配
            score = capability.score(characteristics.complexity)

            # 加分：能力匹配
            if capability.matches(characteristics.required_capabilities):
                score += 0.2

            # 加分：标签匹配
            if capability.matches_tags(characteristics.required_tags):
                score += 0.1

            # 加分：工具匹配
            if characteristics.requires_tools and capability.has_tools:
                score += 0.15

            # 加分：推理匹配
            if characteristics.requires_reasoning and capability.has_recursive_control:
                score += 0.1

            # 考虑优先级
            score += capability.priority * 0.05

            # 考虑负载（负载低的加分）
            load_factor = 1.0 / (1.0 + self.load_stats.get(agent, 0) * 0.1)
            score *= load_factor

            if score > best_score:
                best_score = score
                best_agent = agent
                best_capability = capability

        if best_agent is None:
            best_agent = self.agents[0]
            best_capability = self.capabilities[best_agent]
            best_score = 0.5

        # 更新负载统计
        self.load_stats[best_agent] = self.load_stats.get(best_agent, 0) + 1

        return RoutingResult(
            agent=best_agent,
            capability=best_capability,
            score=best_score,
            reason=f"Auto routing based on task complexity ({characteristics.complexity.value}) and capabilities"
        )

    def _route_rule_based(self, task: str) -> RoutingResult:
        """基于规则的路由"""
        task_lower = task.lower()

        # 检查规则
        for pattern, agent in self.rules.items():
            if pattern.lower() in task_lower:
                return RoutingResult(
                    agent=agent,
                    capability=self.capabilities[agent],
                    score=1.0,
                    reason=f"Matched rule: {pattern}"
                )

        # 没有匹配规则，使用第一个
        agent = self.agents[0]
        return RoutingResult(
            agent=agent,
            capability=self.capabilities[agent],
            score=0.5,
            reason="No rule matched, using default"
        )

    async def _route_llm_based(self, task: str) -> RoutingResult:
        """基于 LLM 的路由"""
        if not self.llm:
            # 回退到自动路由
            return await self._route_auto(task)

        # 构建提示
        agent_descriptions = []
        for i, agent in enumerate(self.agents):
            capability = self.capabilities[agent]
            agent_descriptions.append(
                f"{i+1}. {capability.agent_type.value} - {capability.description or 'General agent'}"
            )

        prompt = f"""Given the task and available agents, select the most appropriate agent.

Task: {task}

Available agents:
{chr(10).join(agent_descriptions)}

Which agent should handle this task? Respond with just the number (1-{len(self.agents)})."""

        message = Message(role="user", content=prompt)
        response = await self.llm.run(message)

        try:
            # 提取数字
            import re
            match = re.search(r'\d+', response.content)
            if match:
                index = int(match.group()) - 1
                if 0 <= index < len(self.agents):
                    agent = self.agents[index]
                    return RoutingResult(
                        agent=agent,
                        capability=self.capabilities[agent],
                        score=1.0,
                        reason=f"LLM selected: {response.content}"
                    )
        except Exception:
            pass

        # 解析失败，回退到自动路由
        return await self._route_auto(task)

    def _route_round_robin(self) -> RoutingResult:
        """轮询路由"""
        agent = self.agents[self._round_robin_index]
        self._round_robin_index = (self._round_robin_index + 1) % len(self.agents)

        return RoutingResult(
            agent=agent,
            capability=self.capabilities[agent],
            score=1.0,
            reason="Round-robin selection"
        )

    async def _route_capability_match(self, task: str) -> RoutingResult:
        """能力匹配路由"""
        characteristics = self.classifier.classify(task)

        # 找到第一个匹配所需能力的 Agent
        for agent in self.agents:
            capability = self.capabilities[agent]
            if capability.matches(characteristics.required_capabilities):
                return RoutingResult(
                    agent=agent,
                    capability=capability,
                    score=1.0,
                    reason=f"Capability match: {characteristics.required_capabilities}"
                )

        # 没有匹配的，使用第一个
        agent = self.agents[0]
        return RoutingResult(
            agent=agent,
            capability=self.capabilities[agent],
            score=0.5,
            reason="No capability match, using default"
        )

    def _route_priority(self) -> RoutingResult:
        """优先级路由"""
        # 选择优先级最高的 Agent
        best_agent = max(self.agents, key=lambda a: self.capabilities[a].priority)

        return RoutingResult(
            agent=best_agent,
            capability=self.capabilities[best_agent],
            score=1.0,
            reason=f"Highest priority: {self.capabilities[best_agent].priority}"
        )

    def _route_load_balance(self) -> RoutingResult:
        """负载均衡路由"""
        # 选择负载最低的 Agent
        best_agent = min(self.agents, key=lambda a: self.load_stats.get(a, 0))
        self.load_stats[best_agent] = self.load_stats.get(best_agent, 0) + 1

        return RoutingResult(
            agent=best_agent,
            capability=self.capabilities[best_agent],
            score=1.0,
            reason=f"Load balancing: {self.load_stats[best_agent]} tasks"
        )

    def get_stats(self) -> Dict[str, Any]:
        """获取路由统计"""
        return {
            "total_agents": len(self.agents),
            "strategy": self.strategy.value,
            "load_stats": {
                self.capabilities[agent].agent_type.value: count
                for agent, count in self.load_stats.items()
            },
        }
