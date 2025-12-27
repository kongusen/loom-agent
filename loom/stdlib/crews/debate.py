"""
辩论团队

两个 Agent 进行辩论的团队模式。
"""

from loom.weave import create_agent, create_crew
from loom.node.crew import CrewNode


def DebateCrew(name: str = "debate-crew", topic: str = "未指定主题") -> CrewNode:
    """
    创建一个辩论团队。

    Args:
        name: 团队名称
        topic: 辩论主题

    Returns:
        配置好的辩论团队

    Example:
        crew = DebateCrew("debate", topic="AI 是否会取代人类工作")
        result = run(crew, "开始辩论")
    """
    # 创建正方 Agent
    pro_agent = create_agent(
        f"{name}-pro",
        role=f"辩论正方 - 支持观点：{topic}"
    )

    # 创建反方 Agent
    con_agent = create_agent(
        f"{name}-con",
        role=f"辩论反方 - 反对观点：{topic}"
    )

    # 创建团队
    crew = create_crew(name, [pro_agent, con_agent])

    return crew
