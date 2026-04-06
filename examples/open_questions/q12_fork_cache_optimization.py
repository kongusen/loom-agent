"""Q12: Fork Cache Optimization in Multi-Model Scenarios

问题: 需要 Haiku + Opus 协同时，如何平衡 cache 复用和角色最优化？
观测现象: 同模型 cache 好但角色不足；换模型角色好但 cache 失效
实验设计: 比较单模型、Fork 不换模型、Fork 换模型、cache-aware 混合调度
证据要求: 模型切换日志、cache 命中率、成本、时延、质量评审
"""

from loom.cluster.fork import ForkStrategy

async def experiment_cache_optimization():
    strategies = [
        "single_model_opus",
        "fork_same_model",
        "fork_switch_model",
        "cache_aware_hybrid"
    ]

    results = {}
    for strategy in strategies:
        fork = ForkStrategy(strategy=strategy)
        metrics = await fork.run_tasks([
            {"type": "explore", "optimal": "haiku"},
            {"type": "reason", "optimal": "opus"}
        ])

        results[strategy] = {
            "cache_hit_rate": metrics.cache_hits / metrics.total_requests,
            "total_cost": metrics.cost_usd,
            "latency_p95": metrics.latency_p95,
            "quality_score": metrics.avg_quality
        }

    return results
