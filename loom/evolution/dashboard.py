"""演化指标面板

根据 Q4 实验结果建立多维指标监控
"""

from dataclasses import dataclass


@dataclass
class EvolutionMetrics:
    """演化指标"""
    success_rate: float
    avg_cost: float
    skill_reuse_rate: float
    constraint_count: int

class EvolutionDashboard:
    """演化指标面板"""

    def __init__(self):
        self.history: list[EvolutionMetrics] = []

    def record(self, metrics: EvolutionMetrics):
        """记录指标"""
        self.history.append(metrics)

    def analyze_growth(self) -> dict:
        """分析能力增长

        实验结果: 成功率 +0.30, 成本降低 10.1, Skill 复用 +0.44
        """
        if len(self.history) < 2:
            return {"growth": False}

        first = self.history[0]
        last = self.history[-1]

        return {
            "capability_growth": last.success_rate > first.success_rate + 0.15,
            "success_delta": last.success_rate - first.success_rate,
            "cost_reduction": first.avg_cost - last.avg_cost,
            "skill_growth": last.skill_reuse_rate - first.skill_reuse_rate
        }
