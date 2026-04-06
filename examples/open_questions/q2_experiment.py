"""Q2 实验：d_max 设定依据

测试不同任务类型的最优深度限制
"""

import random

def simulate_task(task_type, d_max, n_runs=10):
    """模拟任务在给定 d_max 下的表现"""

    # 不同任务类型的特性
    task_profiles = {
        "code": {"optimal_depth": 3, "cost_per_depth": 100},
        "research": {"optimal_depth": 5, "cost_per_depth": 80},
        "planning": {"optimal_depth": 4, "cost_per_depth": 90},
        "debugging": {"optimal_depth": 6, "cost_per_depth": 70},
    }

    profile = task_profiles[task_type]
    results = []

    for _ in range(n_runs):
        actual_depth = min(d_max, profile["optimal_depth"] + random.randint(-1, 1))

        # 成功率：接近最优深度时高
        depth_diff = abs(actual_depth - profile["optimal_depth"])
        success = depth_diff <= 1 or random.random() > depth_diff * 0.2

        # 成本
        cost = actual_depth * profile["cost_per_depth"] * random.uniform(0.9, 1.1)

        results.append({
            "success": success,
            "depth": actual_depth,
            "cost": int(cost)
        })

    return {
        "success_rate": sum(r["success"] for r in results) / n_runs,
        "avg_depth": sum(r["depth"] for r in results) / n_runs,
        "avg_cost": int(sum(r["cost"] for r in results) / n_runs)
    }

if __name__ == "__main__":
    print("=" * 60)
    print("Q2: d_max 设定依据实验")
    print("=" * 60)

    task_types = ["code", "research", "planning", "debugging"]
    dmax_values = [2, 3, 5, 8]

    for task_type in task_types:
        print(f"\n任务类型: {task_type}")
        print("d_max | 成功率 | 平均深度 | 平均成本")
        print("-" * 45)

        best_config = None
        best_score = 0

        for dmax in dmax_values:
            result = simulate_task(task_type, dmax)
            score = result["success_rate"] - (result["avg_cost"] / 10000)

            print(f"{dmax:5d} | {result['success_rate']:.2f}   | "
                  f"{result['avg_depth']:.1f}      | {result['avg_cost']}")

            if score > best_score:
                best_score = score
                best_config = dmax

        print(f"→ 最优 d_max: {best_config}")

    print("\n结论: d_max 应根据任务类型动态调整")
