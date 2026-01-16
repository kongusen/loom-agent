"""
Analytical Pattern - 分析模式

适用场景：需要深度分析、多角度思考、系统性推理的任务。

核心特性：
- System 2 优先（深度思考）
- 高信心阈值（确保质量）
- 启用反思机制
"""

from loom.patterns.base import Pattern


class AnalyticalPattern(Pattern):
    """
    分析模式：深度分析、系统性思考

    适用于：
    - 复杂问题分析
    - 多角度评估
    - 系统性推理
    - 决策支持
    """

    def __init__(self):
        super().__init__(
            name="analytical",
            description="Deep analysis with systematic reasoning"
        )

    def get_config(self):
        """获取分析模式配置"""
        from loom.api.loom import LoomConfig
        from loom.config import AgentConfig

        return LoomConfig(
            agent=AgentConfig(
                name="analytical-analyst",
                role="Analyst",
                system_prompt=(
                    "You are an analytical thinker. "
                    "Approach problems systematically, consider multiple perspectives, "
                    "and provide well-reasoned conclusions."
                )
            )
        )
