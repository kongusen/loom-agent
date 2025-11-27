"""研究员Agent单元测试"""

import asyncio
import pytest
from unittest.mock import Mock, patch, AsyncMock
from typing import List, Dict, Any

from loom.agents.researcher import ResearcherAgent, ResearchPlan, ResearchResult
from loom.interfaces.llm import BaseLLM
from loom.interfaces.tool import BaseTool
from loom.core.events import AgentEvent, AgentEventType


class TestResearcherAgent:
    """研究员Agent单元测试"""

    @pytest.fixture
    def mock_llm(self) -> BaseLLM:
        """创建模拟LLM"""
        mock_llm = Mock(spec=BaseLLM)
        mock_llm.generate = AsyncMock()
        return mock_llm

    @pytest.fixture
    def mock_exa_tool(self) -> BaseTool:
        """创建模拟Exa搜索工具"""
        mock_tool = Mock(spec=BaseTool)
        mock_tool.name = "exa_search"
        mock_tool.run = AsyncMock()
        return mock_tool

    @pytest.fixture
    def researcher_agent(self, mock_llm: BaseLLM, mock_exa_tool: BaseTool) -> ResearcherAgent:
        """创建研究员Agent实例"""
        return ResearcherAgent(llm=mock_llm, tools=[mock_exa_tool])

    @pytest.mark.asyncio
    async def test_analyze_intent(self, researcher_agent: ResearcherAgent, mock_llm: BaseLLM):
        """测试意图分析功能"""
        # 设置模拟响应
        mock_response = Mock()
        mock_response.content = """1. 用户的主要研究目标是了解2024年人工智能在医疗领域的最新应用趋势
2. 用户需要解决的问题是获取最新的AI医疗应用信息
3. 用户可能需要案例研究、技术分析、市场趋势等信息
4. 研究范围限定在2024年和医疗领域"""
        mock_llm.generate.return_value = mock_response

        # 执行测试
        user_query = "2024年人工智能在医疗领域的最新应用趋势"
        intent = await researcher_agent.analyze_intent(user_query)

        # 验证结果
        assert "主要研究目标" in intent
        assert "医疗领域" in intent
        assert "2024年" in intent
        mock_llm.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_research_plan(self, researcher_agent: ResearcherAgent, mock_llm: BaseLLM):
        """测试创建研究计划功能"""
        # 设置模拟响应
        mock_response = Mock()
        mock_response.content = '''{
            "objectives": [
                "了解2024年AI在医疗诊断中的应用",
                "分析AI在药物研发中的最新进展",
                "探讨AI在个性化医疗中的作用"
            ],
            "search_queries": [
                "2024 AI medical diagnosis applications",
                "AI drug discovery latest developments 2024",
                "personalized medicine AI 2024",
                "AI in healthcare 2024 trends",
                "machine learning medical applications 2024"
            ],
            "analysis_steps": [
                "收集和整理搜索结果",
                "分析技术趋势和案例研究",
                "评估市场和商业影响",
                "总结关键发现和趋势"
            ],
            "expected_outcome": "提供2024年AI在医疗领域应用的全面分析报告"
        }'''
        mock_llm.generate.return_value = mock_response

        # 执行测试
        intent_analysis = "用户想了解2024年人工智能在医疗领域的应用趋势"
        plan = await researcher_agent.create_research_plan(intent_analysis)

        # 验证结果
        assert isinstance(plan, ResearchPlan)
        assert len(plan.objectives) >= 3
        assert len(plan.search_queries) >= 5
        assert len(plan.analysis_steps) >= 4
        assert "AI在医疗领域应用的全面分析报告" in plan.expected_outcome
        mock_llm.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_search(self, researcher_agent: ResearcherAgent, mock_exa_tool: BaseTool):
        """测试执行搜索功能"""
        # 设置模拟响应
        mock_search_result = """Exa Search results for 'AI in healthcare 2024':
Total results: 2
================================================================================
1. **AI in Healthcare 2024: Top Trends**
   Domain: healthcareitnews.com
   Published: 2024-01-15
   AI is transforming healthcare with new diagnostic tools and personalized medicine.
   URL: https://example.com/ai-healthcare-2024
--------------------------------------------------------------------------------
2. **Machine Learning Applications in Medicine**
   Domain: medicalaijournal.com
   Published: 2024-02-10
   Latest developments in ML for disease prediction and treatment optimization.
   URL: https://example.com/ml-medicine-2024
--------------------------------------------------------------------------------"""
        mock_exa_tool.run.return_value = mock_search_result

        # 执行测试
        search_query = "AI in healthcare 2024"
        result = await researcher_agent.execute_search(search_query)

        # 验证结果
        assert "Exa Search results" in result
        assert "AI in Healthcare 2024: Top Trends" in result
        assert "https://example.com/ai-healthcare-2024" in result
        mock_exa_tool.run.assert_called_once_with(query=search_query, max_results=10)

    @pytest.mark.asyncio
    async def test_analyze_results(self, researcher_agent: ResearcherAgent, mock_llm: BaseLLM):
        """测试分析搜索结果功能"""
        # 设置模拟响应
        mock_response = Mock()
        mock_response.content = """搜索结果满足研究目标，关键发现包括：
1. AI在医疗诊断中的准确率已达到95%以上
2. 药物研发周期因AI缩短了40%
3. 个性化医疗开始进入临床应用

信息之间存在一致性，不同来源都指出AI在医疗领域的应用正在加速。
需要进一步研究的是AI在医疗领域的伦理和隐私问题。"""
        mock_llm.generate.return_value = mock_response

        # 创建测试数据
        search_results = {
            "query1": "搜索结果1",
            "query2": "搜索结果2"
        }
        research_plan = ResearchPlan(
            objectives=["目标1", "目标2"],
            search_queries=["query1", "query2"],
            analysis_steps=["步骤1", "步骤2"],
            expected_outcome="预期结果"
        )

        # 执行测试
        analysis = await researcher_agent.analyze_results(search_results, research_plan)

        # 验证结果
        assert "关键发现" in analysis
        assert "95%以上" in analysis
        assert "伦理和隐私问题" in analysis
        mock_llm.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_conclusion(self, researcher_agent: ResearcherAgent, mock_llm: BaseLLM):
        """测试生成结论功能"""
        # 设置模拟响应
        mock_response = Mock()
        mock_response.content = """2024年人工智能在医疗领域的应用取得了显著进展，主要体现在：
1. 医疗诊断准确率大幅提升
2. 药物研发效率显著提高
3. 个性化医疗开始临床应用

研究局限性：本次研究主要关注技术层面，未深入探讨伦理和隐私问题。
建议下一步行动：进一步研究AI医疗应用的伦理规范和监管政策。"""
        mock_llm.generate.return_value = mock_response

        # 创建测试数据
        analysis_summary = "分析总结内容"
        research_plan = ResearchPlan(
            objectives=["了解AI在医疗诊断中的应用"],
            search_queries=["query1"],
            analysis_steps=["步骤1"],
            expected_outcome="预期结果"
        )

        # 执行测试
        conclusion = await researcher_agent.generate_conclusion(analysis_summary, research_plan)

        # 验证结果
        assert "2024年人工智能在医疗领域的应用" in conclusion
        assert "医疗诊断准确率" in conclusion
        assert "研究局限性" in conclusion
        mock_llm.generate.assert_called_once()

    @pytest.mark.asyncio
    @patch("loom.agents.researcher.asyncio.sleep")
    async def test_run_research_workflow(self, mock_sleep, researcher_agent: ResearcherAgent, 
                                       mock_llm: BaseLLM, mock_exa_tool: BaseTool):
        """测试完整研究工作流"""
        # 设置模拟响应
        mock_sleep.return_value = asyncio.Future()
        mock_sleep.return_value.set_result(None)

        # 意图分析响应
        mock_llm.generate.side_effect = [
            # 意图分析
            Mock(content="意图分析结果"),
            # 创建研究计划
            Mock(content='''{
                "objectives": ["目标1"],
                "search_queries": ["query1", "query2"],
                "analysis_steps": ["步骤1"],
                "expected_outcome": "预期结果"
            }'''),
            # 分析结果
            Mock(content="分析总结"),
            # 生成结论
            Mock(content="最终结论")
        ]

        # 搜索结果
        mock_exa_tool.run.side_effect = [
            "Exa Search results for 'query1':\nURL: https://example.com/1",
            "Exa Search results for 'query2':\nURL: https://example.com/2"
        ]

        # 执行测试
        user_query = "测试研究查询"
        result = await researcher_agent.run_research_workflow(user_query)

        # 验证结果
        assert isinstance(result, ResearchResult)
        assert result.original_query == user_query
        assert len(result.search_results) == 2
        assert len(result.sources) == 2
        assert "https://example.com/1" in result.sources
        assert "https://example.com/2" in result.sources
        assert mock_llm.generate.call_count == 4
        assert mock_exa_tool.run.call_count == 2
        assert mock_sleep.call_count == 2

    @pytest.mark.asyncio
    async def test_research_method(self, researcher_agent: ResearcherAgent, mock_llm: BaseLLM):
        """测试research方法的事件流"""
        # 设置模拟响应
        mock_response = Mock()
        mock_response.content = "我已经完成了研究，以下是结果..."
        mock_llm.generate.return_value = mock_response

        # 执行测试
        user_query = "测试研究查询"
        events: List[AgentEvent] = []
        async for event in researcher_agent.research(user_query):
            events.append(event)

        # 验证结果
        assert len(events) > 0
        assert any(event.type == AgentEventType.AGENT_FINISH for event in events)
        assert any("研究结果" in event.content for event in events if event.content)


if __name__ == "__main__":
    pytest.main([__file__])
