"""
Creative Pattern - 创造模式

适用场景：需要创新思维、发散思考、探索多种可能性的任务。

核心特性：
- 低信心阈值（鼓励尝试）
- 鼓励探索和实验
- 多样性优先
"""

from loom.patterns import Pattern


class CreativePattern(Pattern):
    """
    创造模式：创新思维、发散思考

    适用于：
    - 头脑风暴
    - 创意方案设计
    - 问题的多种解决方案
    - 探索性任务
    """

    def __init__(self):
        super().__init__(
            name="creative",
            description="Creative thinking with divergent exploration"
        )

    def get_config(self):
        """获取创造模式配置"""
        from loom.api.loom import LoomConfig
        from loom.config import AgentConfig

        return LoomConfig(
            agent=AgentConfig(
                role="Creative Thinker",
                system_prompt=(
                    "You are a creative thinker. "
                    "Explore multiple possibilities, think outside the box, "
                    "and generate innovative solutions."
                )
            )
        )
