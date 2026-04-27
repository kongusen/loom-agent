"""动态心跳间隔策略

根据 Q7 实验结果实现 by_phase 和 by_volatility 策略
"""

from enum import Enum
from typing import Literal


class Phase(Enum):
    """执行阶段"""

    REASON = "reason"
    ACT = "act"
    OBSERVE = "observe"


class HeartbeatStrategy:
    """动态心跳间隔"""

    def __init__(self, strategy: Literal["by_phase", "by_volatility"] = "by_phase"):
        self.strategy = strategy

    def get_interval(self, phase: Phase, volatility: float = 0.0) -> float:
        """获取心跳间隔

        by_phase: 漏检 0，误中断 1，完成率 0.95
        by_volatility: 漏检 0，误中断 2，完成率 0.90 (高 CPU)
        """
        if self.strategy == "by_phase":
            return 2.0 if phase == Phase.ACT else 8.0
        else:  # by_volatility
            return 1.0 if volatility > 0.7 else 5.0
