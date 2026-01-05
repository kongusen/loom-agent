"""
Iterative Pattern - 迭代模式

适用场景：需要逐步优化、反馈循环、持续改进的任务。

核心特性：
- 启用反思机制
- 多轮迭代优化
- 质量评估和改进
"""

from loom.patterns import Pattern


class IterativePattern(Pattern):
    """
    迭代模式：逐步优化、反馈循环

    适用于：
    - 需要持续改进的任务
    - 质量要求高的输出
    - 需要多轮优化的方案
    - 学习和适应性任务
    """

    def __init__(self):
        super().__init__(
            name="iterative",
            description="Iterative refinement with feedback loops"
        )

    def get_config(self):
        """获取迭代模式配置"""
        from loom.api.loom import LoomConfig
        from loom.config import AgentConfig, RouterConfig

        return LoomConfig(
            agent=AgentConfig(
                role="Refiner",
                system_prompt=(
                    "You are a refiner. "
                    "Iteratively improve solutions, learn from feedback, "
                    "and continuously optimize for quality."
                )
            ),
            router=RouterConfig(
                complexity_threshold=0.7,
                confidence_threshold=0.7,  # 中等信心阈值
            )
        )
