"""研究员子agent - 实现搜索-反思循环逻辑"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field
from enum import Enum

from loom.interfaces.agent import BaseAgent, AgentConfig, AgentResult
from loom.interfaces.tool import BaseTool
from loom.core.turn_state import TurnState
from loom.core.execution_context import ExecutionContext
from loom.core.events import AgentEvent, AgentEventType, EventCollector
from loom.core.types import Message, ToolCall, ToolResult
from loom.utils.logger import logger


class ResearchPhase(Enum):
    """研究阶段枚举"""
    INTENT_ANALYSIS = "intent_analysis"
    PLANNING = "planning"
    SEARCHING = "searching"
    REFLECTION = "reflection"
    COMPLETION = "completion"


class ResearchPlan(BaseModel):
    """研究计划模型"""
    objectives: List[str] = Field(description="研究目标列表")
    search_queries: List[str] = Field(description="搜索查询列表")
    current_query_index: int = Field(default=0, description="当前搜索查询索引")
    completed_objectives: List[str] = Field(default_factory=list, description="已完成的研究目标")


class ResearchState(TurnState):
    """研究员agent的状态模型"""
    phase: ResearchPhase = Field(default=ResearchPhase.INTENT_ANALYSIS, description="当前研究阶段")
    plan: Optional[ResearchPlan] = Field(default=None, description="研究计划")
    search_results: List[Dict[str, Any]] = Field(default_factory=list, description="搜索结果列表")
    reflection_notes: List[str] = Field(default_factory=list, description="反思笔记列表")
    final_conclusion: Optional[str] = Field(default=None, description="最终结论")


class ResearcherAgent(BaseAgent):
    """研究员子agent - 实现搜索-反思循环逻辑"""

    name = "researcher_agent"
    description = "研究员子agent，支持搜索-反思循环逻辑，用于深入研究特定主题"

    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self.max_search_rounds = 3  # 最大搜索轮数
        self.exa_tool: Optional[BaseTool] = None

    async def initialize(self, context: ExecutionContext) -> None:
        """初始化agent"""
        await super().initialize(context)
        
        # 检查是否有exa_search工具
        for tool in self.tools:
            if tool.name == "exa_search":
                self.exa_tool = tool
                break
        
        if not self.exa_tool:
            raise ValueError("研究员agent需要exa_search工具")

    async def _analyze_intent(self, message: Message, state: ResearchState) -> Tuple[ResearchState, List[AgentEvent]]:
        """分析用户意图"""
        events = EventCollector()
        
        try:
            # 使用LLM分析用户意图
            prompt = f"""
            请分析用户的研究意图，并制定详细的研究计划。
            
            用户指令：{message.content}
            
            请返回：
            1. 研究目标列表（3-5个具体目标）
            2. 搜索查询列表（每个目标对应1-2个搜索查询）
            
            格式要求：
            目标：
            - [目标1]
            - [目标2]
            - [目标3]
            
            查询：
            - [查询1]
            - [查询2]
            - [查询3]
            """
            
            response = await self.llm.generate(
                messages=[Message(role="user", content=prompt)],
                context=state,
                events=events
            )
            
            # 解析LLM响应，提取研究目标和搜索查询
            objectives = []
            search_queries = []
            lines = response.content.strip().split("\n")
            
            parsing_objectives = False
            parsing_queries = False
            
            for line in lines:
                line = line.strip()
                if line == "目标：":
                    parsing_objectives = True
                    parsing_queries = False
                elif line == "查询：":
                    parsing_objectives = False
                    parsing_queries = True
                elif line.startswith("-") and parsing_objectives:
                    objectives.append(line[2:].strip())
                elif line.startswith("-") and parsing_queries:
                    search_queries.append(line[2:].strip())
            
            # 创建研究计划
            plan = ResearchPlan(
                objectives=objectives,
                search_queries=search_queries
            )
            
            # 更新状态
            state = state.copy(
                update={
                    "phase": ResearchPhase.PLANNING,
                    "plan": plan
                }
            )
            
            events.add(AgentEvent.agent(
                agent_name=self.name,
                message=f"已分析用户意图，制定研究计划：目标{len(objectives)}个，查询{len(search_queries)}个"
            ))
            
        except Exception as e:
            logger.error(f"意图分析失败: {str(e)}")
            events.add(AgentEvent.error(
                agent_name=self.name,
                error=str(e),
                context=f"意图分析失败: {str(e)}"
            ))
            raise
        
        return state, events.get_events()

    async def _execute_search(self, state: ResearchState) -> Tuple[ResearchState, List[AgentEvent]]:
        """执行搜索"""
        events = EventCollector()
        
        if not state.plan:
            raise ValueError("研究计划未初始化")
        
        try:
            # 获取当前搜索查询
            current_query = state.plan.search_queries[state.plan.current_query_index]
            
            events.add(AgentEvent.tool_call(
                agent_name=self.name,
                tool_name="exa_search",
                tool_args={"query": current_query, "max_results": 5}
            ))
            
            # 执行搜索
            search_result = await self.exa_tool.run(query=current_query, max_results=5)
            
            events.add(AgentEvent.tool_result(
                agent_name=self.name,
                tool_name="exa_search",
                tool_result=search_result
            ))
            
            # 更新状态
            state = state.copy(
                update={
                    "phase": ResearchPhase.REFLECTION,
                    "search_results": state.search_results + [{"query": current_query, "result": search_result}]
                }
            )
            
            events.add(AgentEvent.agent(
                agent_name=self.name,
                message=f"已完成搜索：{current_query}"
            ))
            
        except Exception as e:
            logger.error(f"搜索执行失败: {str(e)}")
            events.add(AgentEvent.error(
                agent_name=self.name,
                error=str(e),
                context=f"搜索执行失败: {str(e)}"
            ))
            raise
        
        return state, events.get_events()

    async def _reflect_on_results(self, state: ResearchState) -> Tuple[ResearchState, List[AgentEvent]]:
        """反思搜索结果"""
        events = EventCollector()
        
        if not state.plan:
            raise ValueError("研究计划未初始化")
        
        try:
            # 获取当前搜索结果
            current_search = state.search_results[-1]
            current_query = current_search["query"]
            search_result = current_search["result"]
            
            # 使用LLM反思搜索结果
            prompt = f"""
            请反思以下搜索结果，并评估是否满足当前研究目标。
            
            当前查询：{current_query}
            搜索结果：
            {search_result}
            
            研究目标：
            {"\n".join([f"- {obj}" for obj in state.plan.objectives])}
            
            请返回：
            1. 搜索结果质量评估（高/中/低）
            2. 是否满足当前研究目标（是/否）
            3. 下一步建议（继续搜索下一个查询/调整查询/完成研究）
            4. 反思笔记
            
            格式要求：
            质量评估：[高/中/低]
            目标满足：[是/否]
            下一步建议：[继续搜索下一个查询/调整查询/完成研究]
            反思笔记：[具体笔记内容]
            """
            
            response = await self.llm.generate(
                messages=[Message(role="user", content=prompt)],
                context=state,
                events=events
            )
            
            # 解析LLM响应
            lines = response.content.strip().split("\n")
            quality = "中"
            goal_met = False
            next_step = "继续搜索下一个查询"
            reflection_note = ""
            
            for line in lines:
                line = line.strip()
                if line.startswith("质量评估："):
                    quality = line[6:].strip()
                elif line.startswith("目标满足："):
                    goal_met = line[6:].strip() == "是"
                elif line.startswith("下一步建议："):
                    next_step = line[7:].strip()
                elif line.startswith("反思笔记："):
                    reflection_note = line[7:].strip()
            
            # 更新状态
            state = state.copy(
                update={
                    "reflection_notes": state.reflection_notes + [reflection_note]
                }
            )
            
            # 根据反思结果决定下一步行动
            if next_step == "继续搜索下一个查询":
                # 检查是否还有更多查询
                if state.plan.current_query_index < len(state.plan.search_queries) - 1:
                    state = state.copy(
                        update={
                            "phase": ResearchPhase.SEARCHING,
                            "plan": state.plan.copy(update={"current_query_index": state.plan.current_query_index + 1})
                        }
                    )
                else:
                    # 所有查询都已完成，进入完成阶段
                    state = state.copy(update={"phase": ResearchPhase.COMPLETION})
            elif next_step == "调整查询":
                # 调整当前查询，重新搜索
                state = state.copy(update={"phase": ResearchPhase.SEARCHING})
            elif next_step == "完成研究":
                # 进入完成阶段
                state = state.copy(update={"phase": ResearchPhase.COMPLETION})
            
            events.add(AgentEvent.agent(
                agent_name=self.name,
                message=f"已完成反思：质量{quality}，目标满足{goal_met}，下一步{next_step}"
            ))
            
        except Exception as e:
            logger.error(f"结果反思失败: {str(e)}")
            events.add(AgentEvent.error(
                agent_name=self.name,
                error=str(e),
                context=f"结果反思失败: {str(e)}"
            ))
            raise
        
        return state, events.get_events()

    async def _generate_final_conclusion(self, state: ResearchState) -> Tuple[ResearchState, List[AgentEvent]]:
        """生成最终结论"""
        events = EventCollector()
        
        try:
            # 使用LLM生成最终结论
            prompt = f"""
            请根据以下研究过程和结果，生成最终结论。
            
            研究目标：
            {"\n".join([f"- {obj}" for obj in state.plan.objectives])}
            
            搜索历史：
            {"\n".join([f"- 查询：{search['query']}" for search in state.search_results])}
            
            反思笔记：
            {"\n".join([f"- {note}" for note in state.reflection_notes])}
            
            请返回：
            1. 研究总结
            2. 关键发现
            3. 最终结论
            4. 参考资源
            
            格式要求：
            研究总结：[研究过程总结]
            关键发现：
            - [发现1]
            - [发现2]
            - [发现3]
            最终结论：[最终结论]
            参考资源：
            - [资源1]
            - [资源2]
            - [资源3]
            """
            
            response = await self.llm.generate(
                messages=[Message(role="user", content=prompt)],
                context=state,
                events=events
            )
            
            # 更新状态
            state = state.copy(
                update={
                    "final_conclusion": response.content
                }
            )
            
            events.add(AgentEvent.agent(
                agent_name=self.name,
                message="已生成最终结论"
            ))
            
        except Exception as e:
            logger.error(f"最终结论生成失败: {str(e)}")
            events.add(AgentEvent.error(
                agent_name=self.name,
                error=str(e),
                context=f"最终结论生成失败: {str(e)}"
            ))
            raise
        
        return state, events.get_events()

    async def execute(self, message: Message, state: Optional[TurnState] = None) -> AgentResult:
        """执行agent"""
        if state is None:
            state = ResearchState.initial()
        elif not isinstance(state, ResearchState):
            # 转换为ResearchState
            state_dict = state.to_dict()
            state_dict.pop("turn_counter", None)
            state_dict.pop("turn_id", None)
            state_dict.pop("parent_turn_id", None)
            state_dict.pop("depth", None)
            state_dict.pop("max_depth", None)
            state_dict.pop("is_recursive", None)
            state_dict.pop("tool_calls", None)
            state_dict.pop("tool_results", None)
            state_dict.pop("errors", None)
            state_dict.pop("metadata", None)
            state_dict.pop("loop_detected", None)
            state_dict.pop("loop_count", None)
            state = ResearchState(**state_dict)
        
        events = EventCollector()
        
        try:
            # 根据当前阶段执行相应操作
            if state.phase == ResearchPhase.INTENT_ANALYSIS:
                state, phase_events = await self._analyze_intent(message, state)
                events.extend(phase_events)
            elif state.phase == ResearchPhase.PLANNING:
                # 从计划阶段直接进入搜索阶段
                state = state.copy(update={"phase": ResearchPhase.SEARCHING})
                events.add(AgentEvent.agent(
                    agent_name=self.name,
                    message="研究计划已制定，开始执行搜索"
                ))
            elif state.phase == ResearchPhase.SEARCHING:
                state, phase_events = await self._execute_search(state)
                events.extend(phase_events)
            elif state.phase == ResearchPhase.REFLECTION:
                state, phase_events = await self._reflect_on_results(state)
                events.extend(phase_events)
            elif state.phase == ResearchPhase.COMPLETION:
                if not state.final_conclusion:
                    state, phase_events = await self._generate_final_conclusion(state)
                    events.extend(phase_events)
            
            # 检查是否完成
            is_complete = state.phase == ResearchPhase.COMPLETION and state.final_conclusion is not None
            
            # 生成响应消息
            if is_complete:
                response_message = Message(role="assistant", content=state.final_conclusion)
            else:
                # 根据当前阶段生成状态消息
                if state.phase == ResearchPhase.INTENT_ANALYSIS:
                    response_message = Message(role="assistant", content="正在分析您的研究意图...")
                elif state.phase == ResearchPhase.PLANNING:
                    response_message = Message(role="assistant", content="正在制定研究计划...")
                elif state.phase == ResearchPhase.SEARCHING:
                    current_query = state.plan.search_queries[state.plan.current_query_index]
                    response_message = Message(role="assistant", content=f"正在搜索：{current_query}...")
                elif state.phase == ResearchPhase.REFLECTION:
                    response_message = Message(role="assistant", content="正在反思搜索结果...")
                else:
                    response_message = Message(role="assistant", content="正在生成最终结论...")
            
            return AgentResult(
                message=response_message,
                state=state,
                events=events.get_events(),
                is_complete=is_complete
            )
            
        except Exception as e:
            logger.error(f"研究员agent执行失败: {str(e)}")
            events.add(AgentEvent.error(
                agent_name=self.name,
                error=str(e),
                context=f"研究员agent执行失败: {str(e)}"
            ))
            
            return AgentResult(
                message=Message(role="assistant", content=f"研究执行失败：{str(e)}"),
                state=state,
                events=events.get_events(),
                is_complete=True
            )

    async def finalize(self, context: ExecutionContext) -> None:
        """清理资源"""
        await super().finalize(context)
        self.exa_tool = None