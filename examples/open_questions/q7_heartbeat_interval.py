"""Q7: Heartbeat Interval Optimization

问题: T_hb 是否应是任务类型、Act phase、波动性相关的动态值？
观测现象: 固定间隔下，要么感知过疏导致盲区，要么过频导致无效中断
实验设计: 比较固定、按任务、按 phase、按波动性四类策略
证据要求: heartbeat 日志、事件漏检率、误中断率、开销统计
"""

from loom.runtime.heartbeat import HeartbeatMonitor

async def experiment_heartbeat_interval():
    strategies = [
        {"name": "fixed", "interval": 5.0},
        {"name": "by_task", "interval_fn": lambda task: 3.0 if task == "code" else 10.0},
        {"name": "by_phase", "interval_fn": lambda phase: 2.0 if phase == "act" else 8.0},
        {"name": "by_volatility", "interval_fn": lambda vol: 1.0 if vol > 0.7 else 5.0}
    ]

    results = {}
    for strategy in strategies:
        monitor = HeartbeatMonitor(strategy=strategy)
        metrics = await monitor.run_experiment(duration=300)

        results[strategy["name"]] = {
            "missed_events": metrics.missed_event_count,
            "false_interrupts": metrics.false_interrupt_count,
            "cpu_overhead": metrics.cpu_usage_pct,
            "completion_rate": metrics.task_completion_rate
        }

    return results
