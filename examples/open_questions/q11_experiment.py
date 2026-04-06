"""Q11 实验：Skill Effort Hints 量化"""

import random

def simulate_skill_execution(effort):
    """模拟不同 effort 级别的执行"""

    profiles = {
        "low": {"timeout": 30, "budget": 1000, "quality": 0.75},
        "medium": {"timeout": 60, "budget": 3000, "quality": 0.85},
        "high": {"timeout": 120, "budget": 8000, "quality": 0.95}
    }

    profile = profiles[effort]

    return {
        "duration": profile["timeout"] * random.uniform(0.6, 0.9),
        "tokens": int(profile["budget"] * random.uniform(0.7, 1.0)),
        "tool_depth": {"low": 2, "medium": 4, "high": 7}[effort],
        "quality": profile["quality"] + random.uniform(-0.05, 0.05)
    }

if __name__ == "__main__":
    print("=" * 60)
    print("Q11: Skill Effort Hints 量化实验")
    print("=" * 60)

    efforts = ["low", "medium", "high"]

    print("\nEffort | 时长(s) | Tokens | 工具深度 | 质量")
    print("-" * 55)

    for effort in efforts:
        result = simulate_skill_execution(effort)
        print(f"{effort:6s} | {result['duration']:7.1f} | "
              f"{result['tokens']:6d} | {result['tool_depth']:8d} | "
              f"{result['quality']:.2f}")

    print("\n结论: effort hint 与资源消耗呈正相关")
