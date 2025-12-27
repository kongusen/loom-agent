"""
Loom Weave 快速开始示例

展示如何使用 loom.weave 模块快速创建和运行 Agent。
"""

from loom.weave import create_agent, create_tool, create_crew, run


# ============================================================================
# 示例 1：最简单的 Agent
# ============================================================================

def example_1_simple_agent():
    """创建并运行一个最简单的 Agent"""
    print("=== 示例 1：最简单的 Agent ===")

    # 只需 2 行代码！
    agent = create_agent("助手", role="通用助手")
    result = run(agent, "你好，请介绍一下自己")

    print(f"结果: {result}")


# ============================================================================
# 示例 2：带工具的 Agent
# ============================================================================

def example_2_agent_with_tools():
    """创建一个带自定义工具的 Agent"""
    print("\n=== 示例 2：带工具的 Agent ===")

    # 定义一个简单的工具
    def calculate(expression: str) -> str:
        """计算数学表达式"""
        try:
            result = eval(expression)
            return f"计算结果: {result}"
        except Exception as e:
            return f"计算错误: {e}"

    # 创建工具和 Agent
    calc_tool = create_tool("calculator", calculate, "计算数学表达式")
    agent = create_agent("计算器助手", role="数学助手", tools=[calc_tool])

    # 运行任务
    result = run(agent, "计算 123 + 456")
    print(f"结果: {result}")


# ============================================================================
# 示例 3：Agent 团队（Crew）
# ============================================================================

def example_3_crew():
    """创建一个 Agent 团队协作完成任务"""
    print("\n=== 示例 3：Agent 团队 ===")

    # 创建多个 Agent
    researcher = create_agent("研究员", role="负责研究和收集信息")
    writer = create_agent("作家", role="负责撰写文章")

    # 创建团队
    crew = create_crew("研究写作团队", [researcher, writer])

    # 运行团队任务
    result = run(crew, "研究量子计算并写一篇简短的介绍")
    print(f"结果: {result}")


if __name__ == "__main__":
    # 运行所有示例
    example_1_simple_agent()
    example_2_agent_with_tools()
    example_3_crew()
