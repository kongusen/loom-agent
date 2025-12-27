"""
计算器技能

提供基本的数学计算能力。
"""

from typing import List
from loom.stdlib.skills.base import Skill
from loom.node.tool import ToolNode
from loom.weave import create_tool


class CalculatorSkill(Skill):
    """
    计算器技能。

    提供基本的数学表达式计算功能。
    """

    def __init__(self):
        super().__init__(
            name="calculator",
            description="执行数学计算"
        )

    def get_tools(self) -> List[ToolNode]:
        """返回计算器工具"""

        def calculate(expression: str) -> str:
            """
            计算数学表达式。

            Args:
                expression: 数学表达式，例如 "2 + 2" 或 "10 * 5"

            Returns:
                计算结果
            """
            try:
                # 安全的计算：只允许基本数学运算
                allowed_chars = set("0123456789+-*/()., ")
                if not all(c in allowed_chars for c in expression):
                    return "错误：表达式包含不允许的字符"

                result = eval(expression, {"__builtins__": {}}, {})
                return f"计算结果: {result}"
            except Exception as e:
                return f"计算错误: {str(e)}"

        return [create_tool("calculator", calculate, "计算数学表达式")]

    def get_system_prompt(self) -> str:
        """返回计算器的系统提示词"""
        return """你可以使用 calculator 工具来执行数学计算。
当用户询问数学问题时，使用此工具获取准确的计算结果。"""
