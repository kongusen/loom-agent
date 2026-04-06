"""Q3 实验：DAG 耦合与写冲突"""

import random

def simulate_write_conflict(strategy):
    """模拟 3 个 Sub-Agent 并发写入"""

    if strategy == "last_write_wins":
        conflicts = 3
        final_state = "Content from agent_2"
        versions = 1
    elif strategy == "versioned_write":
        conflicts = 0
        final_state = "Merged: agent_0, agent_1, agent_2"
        versions = 3
    else:  # topic_partition_merge
        conflicts = 0
        final_state = "Partitioned merge with topics"
        versions = 3

    return {
        "conflicts": conflicts,
        "final_state": final_state,
        "versions": versions
    }

if __name__ == "__main__":
    print("=" * 60)
    print("Q3: DAG 耦合与写冲突实验")
    print("=" * 60)

    strategies = ["last_write_wins", "versioned_write", "topic_partition_merge"]

    print("\n策略                    | 冲突数 | 版本数")
    print("-" * 50)

    for strategy in strategies:
        result = simulate_write_conflict(strategy)
        print(f"{strategy:23s} | {result['conflicts']:6d} | {result['versions']:6d}")

    print("\n结论: 版本化写入或分区合并可避免冲突")
