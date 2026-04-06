"""Q2: d_max Setting Basis

问题: 拆解深度上限是否应是任务类型相关的函数？
观测现象: 统一 d_max 在某些任务上过早终止，在另一些任务上过深递归
实验设计: 不同任务类型在不同 d_max 下运行，统计成功率、深度、成本
证据要求: 任务分桶、深度分布、成功率曲线、成本对照表
"""

from loom.cluster.fork import ClusterOrchestrator

async def experiment_dmax_by_task():
    task_types = ["code", "research", "planning", "debugging"]
    dmax_values = [2, 3, 5, 8]

    results = {}
    for task_type in task_types:
        results[task_type] = {}
        for dmax in dmax_values:
            orchestrator = ClusterOrchestrator(d_max=dmax)
            metrics = await orchestrator.run_task_batch(task_type, n=10)

            results[task_type][dmax] = {
                "success_rate": metrics.success_count / 10,
                "avg_depth": metrics.avg_recursion_depth,
                "subagent_count": metrics.total_subagents,
                "total_cost": metrics.total_tokens
            }

    return results
