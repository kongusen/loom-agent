"""
分析师 Agent

预构建的分析师 Agent，具备数学计算能力。
"""

from loom.weave import create_agent
from loom.node.agent import AgentNode
from loom.stdlib.skills import CalculatorSkill


def AnalystAgent(name: str = "analyst") -> AgentNode:
    """
    创建一个分析师 Agent。

    Args:
        name: Agent 名称

    Returns:
        配置好的分析师 Agent

    Example:
        analyst = AnalystAgent("my-analyst")
        result = run(analyst, "计算 2024 年的销售增长率")
    """
    # 创建基础 Agent
    agent = create_agent(
        name,
        role="分析师 - 负责数据分析和计算"
    )

    # 注册计算器技能
    calc_skill = CalculatorSkill()
    calc_skill.register(agent)

    return agent
