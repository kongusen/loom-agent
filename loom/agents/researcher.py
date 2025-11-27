"""研究员子Agent - 具备智能搜索和反思能力"""

from __future__ import annotations

import asyncio
from typing import AsyncGenerator, Dict, List, Optional, Any
from pydantic import BaseModel, Field

from loom.core.agent_executor import AgentExecutor
from loom.core.types import Message, TurnState, ExecutionContext
from loom.core.events import AgentEvent, AgentEventType
from loom.interfaces.llm import BaseLLM
from loom.interfaces.tool import BaseTool
from loom.llm.factory import LLMFactory
from loom.llm.config import LLMConfig, LLMProvider


class ResearchPlan(BaseModel):
    """研究计划模型"""
    objectives: List[str] = Field(description="研究目标列表")
    search_queries: List[str] = Field(description="搜索查询列表")
    analysis_steps: List[str] = Field(description="分析步骤列表")
    expected_outcome: str = Field(description="预期结果描述")


class ResearchResult(BaseModel):
    """研究结果模型"""
    original_query: str = Field(description="原始用户查询")
    research_plan: ResearchPlan = Field(description="执行的研究计划")
    search_results: Dict[str, str] = Field(description="搜索结果，键为查询，值为结果")
    analysis_summary: str = Field(description="分析总结")
    final_conclusion: str = Field(description="最终结论")
    sources: List[str] = Field(description="引用的来源URL列表")


class ResearcherAgent:
    """研究员子Agent - 具备智能搜索、分析和反思能力"""

    def __init__(self,
                 llm: Optional[BaseLLM] = None,
                 tools: Optional[List[BaseTool]] = None,
                 max_iterations: int = 10,
                 max_context_tokens: int = 16000):
        """初始化研究员Agent"""
        if llm is None:
            # 默认使用OpenAI兼容模型配置（阿里qwen-turbo）
            config = LLMConfig.custom(
                model_name="qwen-turbo",
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
                api_key=None,  # 从环境变量获取
                temperature=0.1,
                max_tokens=2048
            )
            llm = LLMFactory.create(config)

        if tools is None:
            # 默认添加Exa搜索工具
            from loom.builtin.tools.exa_search import ExaSearchTool
            tools = [ExaSearchTool(api_key="974916d1-902a")]

        tools_map = {t.name: t for t in tools}
        
        # 研究员系统指令
        system_instructions = """
        你是一个专业的研究员Agent，具备以下能力：
        1. 深度分析用户需求，制定详细的研究计划
        2. 使用搜索工具获取相关信息
        3. 对搜索结果进行批判性分析和综合
        4. 通过反思循环不断优化搜索策略
        5. 提供结构化、有深度的研究报告

        研究流程：
        1. 意图分析：理解用户的真实需求和研究目标
        2. 计划制定：创建详细的研究计划，包括搜索查询和分析步骤
        3. 信息收集：执行搜索并收集相关信息
        4. 分析综合：对收集到的信息进行分析和综合
        5. 反思优化：评估结果是否满足需求，如有必要调整策略
        6. 报告生成：整理并返回完整的研究结果

        输出要求：
        - 始终使用中文输出
        - 提供结构化的研究报告
        - 包含所有引用的来源
        - 结论要基于搜索结果，客观中立
        """

        self.executor = AgentExecutor(
            llm=llm,
            tools=tools_map,
            max_iterations=max_iterations,
            max_context_tokens=max_context_tokens,
            system_instructions=system_instructions
        )

    async def research(self, query: str) -> AsyncGenerator[AgentEvent, None]:
        """执行研究任务"""
        # 初始化状态
        turn_state = TurnState.initial(max_iterations=self.executor.max_iterations)
        context = ExecutionContext.create()
        
        # 初始消息：用户查询
        messages = [Message(role="user", content=query)]
        
        # 执行研究流程
        async for event in self.executor.tt(messages, turn_state, context):
            yield event

    async def analyze_intent(self, query: str) -> str:
        """分析用户意图"""
        prompt = f"""
        请分析以下用户查询的意图：
        {query}

        请回答：
        1. 用户的主要研究目标是什么？
        2. 用户需要解决什么问题？
        3. 用户可能需要哪些类型的信息？
        4. 研究的范围和边界是什么？
        """
        
        messages = [
            Message(role="system", content="你是一个意图分析专家，擅长理解用户的研究需求。"),
            Message(role="user", content=prompt)
        ]
        
        result = await self.executor.llm.generate(messages)
        return result.content

    async def create_research_plan(self, intent_analysis: str) -> ResearchPlan:
        """创建研究计划"""
        prompt = f"""
        基于以下意图分析，创建一个详细的研究计划：
        {intent_analysis}

        研究计划应包括：
        1. 明确的研究目标（至少3个）
        2. 具体的搜索查询（至少5个）
        3. 系统的分析步骤（至少4个）
        4. 预期的研究结果

        请以JSON格式返回，确保符合以下结构：
        {{
            "objectives": ["目标1", "目标2", "目标3"],
            "search_queries": ["查询1", "查询2", "查询3", "查询4", "查询5"],
            "analysis_steps": ["步骤1", "步骤2", "步骤3", "步骤4"],
            "expected_outcome": "预期结果描述"
        }}
        """
        
        messages = [
            Message(role="system", content="你是一个研究计划专家，擅长制定详细的研究方案。"),
            Message(role="user", content=prompt)
        ]
        
        result = await self.executor.llm.generate(messages)
        return ResearchPlan.parse_raw(result.content)

    async def execute_search(self, query: str) -> str:
        """执行搜索"""
        if "exa_search" not in self.executor.tools:
            raise ValueError("Exa搜索工具未配置")
        
        tool = self.executor.tools["exa_search"]
        result = await tool.run(query=query, max_results=10)
        return result

    async def analyze_results(self, search_results: Dict[str, str], research_plan: ResearchPlan) -> str:
        """分析搜索结果"""
        results_text = "\n\n".join([f"**查询：{query}**\n{result}" for query, result in search_results.items()])
        
        prompt = f"""
        基于以下研究计划和搜索结果，进行深入分析：
        
        研究计划：
        {research_plan.model_dump_json(indent=2)}
        
        搜索结果：
        {results_text}
        
        请分析：
        1. 搜索结果是否满足研究目标？
        2. 有哪些关键发现和洞察？
        3. 信息之间有什么关联和模式？
        4. 存在哪些知识 gaps或需要进一步研究的地方？
        5. 不同来源的信息是否一致？如有冲突如何解释？
        
        请提供结构化的分析总结。
        """
        
        messages = [
            Message(role="system", content="你是一个信息分析专家，擅长从搜索结果中提取有价值的洞察。"),
            Message(role="user", content=prompt)
        ]
        
        result = await self.executor.llm.generate(messages)
        return result.content

    async def generate_conclusion(self, analysis_summary: str, research_plan: ResearchPlan) -> str:
        """生成最终结论"""
        prompt = f"""
        基于以下研究计划和分析总结，生成最终结论：
        
        研究计划：
        {research_plan.model_dump_json(indent=2)}
        
        分析总结：
        {analysis_summary}
        
        请生成：
        1. 简洁明了的最终结论
        2. 对用户问题的直接回答
        3. 研究的局限性（如有）
        4. 建议的下一步行动（如有）
        
        结论应基于事实，客观中立，并直接回应用户的原始需求。
        """
        
        messages = [
            Message(role="system", content="你是一个结论生成专家，擅长总结研究成果。"),
            Message(role="user", content=prompt)
        ]
        
        result = await self.executor.llm.generate(messages)
        return result.content

    async def run_research_workflow(self, query: str) -> ResearchResult:
        """运行完整的研究工作流"""
        # 1. 意图分析
        intent_analysis = await self.analyze_intent(query)
        
        # 2. 创建研究计划
        research_plan = await self.create_research_plan(intent_analysis)
        
        # 3. 执行搜索
        search_results = {}
        for search_query in research_plan.search_queries:
            result = await self.execute_search(search_query)
            search_results[search_query] = result
            # 添加适当的延迟避免API限制
            await asyncio.sleep(1)
        
        # 4. 分析结果
        analysis_summary = await self.analyze_results(search_results, research_plan)
        
        # 5. 生成结论
        final_conclusion = await self.generate_conclusion(analysis_summary, research_plan)
        
        # 6. 提取来源
        sources = []
        for result in search_results.values():
            # 简单的URL提取逻辑，实际项目中可以更完善
            lines = result.split('\n')
            for line in lines:
                if line.strip().startswith('URL:'):
                    url = line.split('URL:')[1].strip()
                    if url not in sources:
                        sources.append(url)
        
        return ResearchResult(
            original_query=query,
            research_plan=research_plan,
            search_results=search_results,
            analysis_summary=analysis_summary,
            final_conclusion=final_conclusion,
            sources=sources
        )
