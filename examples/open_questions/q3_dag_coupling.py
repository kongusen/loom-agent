"""Q3: DAG Coupling and Write Conflicts

问题: 阿米巴分裂产生的 Sub-Agent 共享场景包时，DAG 拓扑下 M_f 写冲突如何解决？
观测现象: 多个 Sub-Agent 对共享资源并发写入时，出现覆盖、乱序或不一致
实验设计: 构造多 Agent 同时写共享资源，比较三种策略
证据要求: 冲突日志、版本链、merge 结果、最终状态快照
"""

import asyncio
from loom.cluster.shared_memory import SharedMemoryManager

async def experiment_dag_write_conflicts():
    strategies = ["last_write_wins", "versioned_write", "topic_partition_merge"]

    results = {}
    for strategy in strategies:
        manager = SharedMemoryManager(conflict_strategy=strategy)

        # 启动 3 个 Sub-Agent 同时写共享文件
        agents = [manager.spawn_agent(f"agent_{i}") for i in range(3)]

        await asyncio.gather(*[
            agent.write_shared("summary.md", f"Content from {agent.id}")
            for agent in agents
        ])

        results[strategy] = {
            "conflicts_detected": manager.conflict_count,
            "final_state": manager.read_shared("summary.md"),
            "version_chain": manager.get_version_history("summary.md")
        }

    return results
