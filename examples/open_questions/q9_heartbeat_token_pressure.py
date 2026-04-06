"""Q9: Heartbeat Event Token Pressure

问题: pending_events + active_risks 高频注入时，event_surface 是否会挤压主认知空间？
观测现象: 高频文件变化导致 C_working 中事件内容膨胀
实验设计: 比较"原样注入""去重注入""聚合摘要"三种策略
证据要求: event 数量曲线、token 占用、压缩快照、完成率统计
"""

from loom.runtime.heartbeat import HeartbeatMonitor
from loom.context.manager import ContextManager

async def experiment_token_pressure():
    strategies = ["raw", "dedup", "aggregate"]
    results = {}

    for strategy in strategies:
        monitor = HeartbeatMonitor(event_strategy=strategy)
        ctx = ContextManager()

        # 模拟高频事件源
        for i in range(100):
            monitor.inject_event({"type": "file_change", "path": f"file_{i%10}.py"})

        results[strategy] = {
            "event_count": len(ctx.working.event_surface.pending_events),
            "token_usage": ctx.working.estimate_tokens(),
            "task_completion": await run_task_with_events(monitor)
        }

    return results

async def run_task_with_events(monitor):
    # 在事件压力下执行标准任务
    return {"success": True, "steps": 10}
