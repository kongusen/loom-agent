"""
End-to-End Real API Test

基于真实API的端到端测试，验证完整的分形递归系统。

测试场景：递归文档分析系统
- 分形容器：多层嵌套结构
- 编排器：并行协调执行
- 真实LLM：OpenAI API调用
- 四范式：Planning, MultiAgent, ToolUse, Reflection

需要配置环境变量：
- OPENAI_API_KEY
- ENABLE_REAL_API_TESTS=true
"""

import pytest

from loom.config import LLMConfig
from loom.fractal.container import NodeContainer
from loom.agent.card import AgentCapability, AgentCard
from loom.runtime import Task, TaskStatus
from loom.providers.llm.openai import OpenAIProvider
from tests.api_config import requires_real_api


class RealLLMAgent:
    """
    真实LLM Agent

    使用OpenAI API进行实际的文本分析。
    """

    def __init__(self, node_id: str, analysis_type: str, openai_config: dict):
        """
        初始化真实LLM Agent

        Args:
            node_id: 节点ID
            analysis_type: 分析类型（summary, keyword, sentiment）
            openai_config: OpenAI配置
        """
        self.node_id = node_id
        self.source_uri = f"node://{node_id}"
        self.analysis_type = analysis_type
        self.agent_card = AgentCard(
            agent_id=node_id,
            name=f"{analysis_type.capitalize()} LLM Agent",
            description=f"Real LLM agent for {analysis_type} analysis",
            capabilities=[AgentCapability.TOOL_USE],
        )

        # 创建LLM provider
        self.provider = OpenAIProvider(
            LLMConfig(
                provider="openai",
                api_key=openai_config["api_key"],
                base_url=openai_config["base_url"],
                model=openai_config["model"],
                temperature=0.3,  # 低温度，更确定的输出
                max_tokens=200,
            )
        )

    async def execute_task(self, task: Task) -> Task:
        """
        执行分析任务（使用真实LLM）

        Args:
            task: 任务对象

        Returns:
            更新后的任务
        """
        input_text = task.parameters.get("text", "")

        # 根据分析类型构建提示词
        if self.analysis_type == "summary":
            prompt = f"Summarize the following text in one sentence:\\n\\n{input_text}"
        elif self.analysis_type == "keyword":
            prompt = f"Extract 3-5 keywords from the following text:\\n\\n{input_text}"
        elif self.analysis_type == "sentiment":
            prompt = f"Analyze the sentiment of the following text (positive/negative/neutral):\\n\\n{input_text}"
        else:
            prompt = f"Analyze the following text:\\n\\n{input_text}"

        try:
            # 调用真实LLM API
            response = await self.provider.chat(messages=[{"role": "user", "content": prompt}])

            task.result = {
                "agent_id": self.node_id,
                "analysis_type": self.analysis_type,
                "result": response.content,
                "token_usage": response.token_usage,
            }
            task.status = TaskStatus.COMPLETED
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)

        return task

    def get_capabilities(self) -> AgentCard:
        """获取能力声明"""
        return self.agent_card


class TestEndToEndRealAPI:
    """端到端真实API测试"""

    @requires_real_api
    @pytest.mark.asyncio
    async def test_single_llm_agent(self, openai_config):
        """测试单个真实LLM agent"""
        # 创建真实LLM agent
        agent = RealLLMAgent("llm-summary", "summary", openai_config)

        # 创建任务
        task = Task(
            action="analyze",
            parameters={
                "text": "Artificial intelligence is transforming how we work and live. "
                "It enables automation, improves decision-making, and creates new opportunities."
            },
        )

        # 执行任务
        result = await agent.execute_task(task)

        # 验证结果
        assert result.status == TaskStatus.COMPLETED
        assert result.result is not None
        assert "result" in result.result
        assert len(result.result["result"]) > 0
        assert "token_usage" in result.result
        print(f"\n✅ LLM Summary: {result.result['result']}")

    @requires_real_api
    @pytest.mark.asyncio
    async def test_fractal_container_with_real_llm(self, openai_config):
        """测试分形容器嵌套真实LLM agent"""
        # 创建真实LLM agent（叶子节点）
        llm_agent = RealLLMAgent("llm-nested", "summary", openai_config)

        # 创建两层嵌套容器
        container_l1 = NodeContainer(
            node_id="container-l1-real",
            agent_card=AgentCard(
                agent_id="container-l1-real",
                name="Real API Container L1",
                description="First layer container with real LLM",
                capabilities=[AgentCapability.MULTI_AGENT],
            ),
            child=llm_agent,
        )

        container_l2 = NodeContainer(
            node_id="container-l2-real",
            agent_card=AgentCard(
                agent_id="container-l2-real",
                name="Real API Container L2",
                description="Second layer container",
                capabilities=[AgentCapability.MULTI_AGENT],
            ),
            child=container_l1,
        )

        # 创建任务
        task = Task(
            action="analyze",
            parameters={
                "text": "The future of AI is bright. Machine learning models are becoming more capable, "
                "efficient, and accessible to developers worldwide."
            },
        )

        # 执行任务（递归到真实LLM）
        result = await container_l2.execute_task(task)

        # 验证结果
        assert result.status == TaskStatus.COMPLETED
        assert result.result["agent_id"] == "llm-nested"
        assert len(result.result["result"]) > 0
        print(f"\n✅ Fractal + Real LLM: {result.result['result']}")
