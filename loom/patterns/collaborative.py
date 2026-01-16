"""
Collaborative Pattern - 协作模式

适用场景：复杂任务需要分解为子任务，通过并行协作完成。

核心特性：
- 启用分型能力（任务分解）
- 并行执行子任务
- 轻量级模型合成结果
"""

from loom.patterns.base import Pattern


class CollaborativePattern(Pattern):
    """
    协作模式：任务分解、并行协作

    适用于：
    - 复杂多步骤任务
    - 需要多个专业领域协作
    - 可并行处理的独立子任务
    - 大规模信息处理
    """

    def __init__(self):
        super().__init__(
            name="collaborative", description="Task decomposition with parallel collaboration"
        )

    def get_config(self):
        """获取协作模式配置"""
        from loom.api.loom import LoomConfig
        from loom.config import AgentConfig, ExecutionConfig, FractalConfig
        from loom.config.fractal import GrowthTrigger

        return LoomConfig(
            agent=AgentConfig(
                name="collaborative-coordinator",
                role="Coordinator",
                system_prompt=(
                    "You are a coordinator. "
                    "Break down complex tasks into manageable subtasks, "
                    "delegate to specialized agents, and synthesize results."
                ),
            ),
            fractal=FractalConfig(
                enabled=True,
                max_depth=3,
                enable_explicit_delegation=True,
                synthesis_model="lightweight",  # 使用轻量级模型合成
                growth_trigger=GrowthTrigger.COMPLEXITY,
            ),
            execution=ExecutionConfig(parallel_execution=True, concurrency_limit=5),
        )
