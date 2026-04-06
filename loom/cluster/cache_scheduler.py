"""Cache-aware 混合调度

根据 Q12 实验结果实现混合调度策略
"""

from typing import Literal

ModelType = Literal["haiku", "opus"]

class CacheAwareScheduler:
    """Cache-aware 混合调度"""

    def __init__(self):
        self.cache_hit_rate = 0.0

    def select_model(
        self,
        task_type: Literal["explore", "reason"],
        cache_available: bool
    ) -> ModelType:
        """选择最优模型

        实验结果:
        - cache_aware_hybrid: 命中 0.65, 成本 $0.88, 延迟 720ms, 质量 0.91
        """
        if task_type == "explore":
            # 探索任务优先 haiku
            return "haiku"

        # 推理任务：有 cache 用 opus，否则用 haiku
        if cache_available and self.cache_hit_rate > 0.5:
            return "opus"
        return "haiku"

    def update_cache_stats(self, hit: bool):
        """更新 cache 统计"""
        alpha = 0.1
        self.cache_hit_rate = alpha * (1.0 if hit else 0.0) + (1 - alpha) * self.cache_hit_rate
