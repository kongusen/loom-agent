"""
Loom 标准库使用示例

展示如何使用预构建的 Skills、Agents 和 Crews。
"""

from loom.stdlib.agents import AnalystAgent
from loom.stdlib.skills import CalculatorSkill
from loom.weave import create_agent, run

# ============================================================================
# 示例 1：使用 Skills 增强 Agent
# ============================================================================


def example_1_skills():
    """展示如何使用 Skills 增强 Agent"""
    print("=== 示例 1：使用 Skills 增强 Agent ===")

    # 创建一个基础 Agent
    agent = create_agent("助手", role="通用助手")

    # 注册计算器技能
    calc_skill = CalculatorSkill()
    calc_skill.register(agent)

    # 现在 Agent 可以进行计算
    result = run(agent, "计算 123 * 456")
    print(f"结果: {result}\n")


# ============================================================================
# 示例 2：使用预构建的 Agent
# ============================================================================


def example_2_prebuilt_agents():
    """展示如何使用预构建的 Agent"""
    print("=== 示例 2：使用预构建的 Agent ===")

    # 使用分析师 Agent（自带计算能力）
    analyst = AnalystAgent("my-analyst")
    result = run(analyst, "计算 2024 * 365")
    print(f"分析师结果: {result}\n")


if __name__ == "__main__":
    # 运行示例
    example_1_skills()
    example_2_prebuilt_agents()
