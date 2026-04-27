"""任务类型感知的 d_max 函数

根据 Q2 实验结果实现动态深度限制
"""

from typing import Literal

TaskType = Literal["code", "research", "planning", "debugging", "default"]


def get_dmax_for_task(task_type: TaskType) -> int:
    """根据任务类型返回最优 d_max

    实验结果:
    - code: 2 (快速迭代，浅层足够)
    - research: 5 (需要深度探索)
    - planning: 3 (中等深度)
    - debugging: 5 (需要深入追踪)
    """
    dmax_map = {"code": 2, "research": 5, "planning": 3, "debugging": 5, "default": 3}
    return dmax_map.get(task_type, 3)
