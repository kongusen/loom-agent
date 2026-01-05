"""
Execution Pattern - 执行模式

适用场景：快速执行、结果导向、低延迟的任务。

核心特性：
- System 1 优先（快速反应）
- 低延迟执行
- 直接行动导向
"""

from loom.patterns import Pattern


class ExecutionPattern(Pattern):
    """
    执行模式：快速执行、结果导向

    适用于：
    - 简单直接的任务
    - 需要快速响应
    - 明确的执行步骤
    - 低延迟要求
    """

    def __init__(self):
        super().__init__(
            name="execution",
            description="Fast execution with action-oriented approach"
        )

    def get_config(self):
        """获取执行模式配置"""
        from loom.api.loom import LoomConfig
        from loom.config import AgentConfig, RouterConfig

        return LoomConfig(
            agent=AgentConfig(
                role="Executor",
                system_prompt=(
                    "You are an executor. "
                    "Act quickly and decisively, focus on results, "
                    "and complete tasks efficiently."
                )
            ),
            router=RouterConfig(
                complexity_threshold=0.8,  # 更难触发 System 2
                confidence_threshold=0.5,  # 低信心阈值，快速行动
            )
        )
