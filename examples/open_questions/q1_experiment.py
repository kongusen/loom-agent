"""Q1 实验：LLM 自我感知可靠性

简化版本 - 模拟实验运行
"""

import random

def simulate_task_execution():
    """模拟多阶段任务执行"""
    milestones = [
        {"id": 1, "desc": "读取配置", "complete": False},
        {"id": 2, "desc": "解析数据", "complete": False},
        {"id": 3, "desc": "生成输出", "complete": False},
        {"id": 4, "desc": "验证结果", "complete": False},
    ]

    evidence = []

    for step in range(10):
        # 模拟客观完成度
        completed = min(step / 10, 1.0)
        for i, m in enumerate(milestones):
            if i < step / 2.5:
                m["complete"] = True

        objective = sum(m["complete"] for m in milestones) / len(milestones)

        # 模拟 LLM 自评（后期倾向高估）
        if objective > 0.7:
            self_reported = objective + random.uniform(0.1, 0.25)
        else:
            self_reported = objective + random.uniform(-0.05, 0.1)

        self_reported = min(self_reported, 1.0)

        evidence.append({
            "step": step,
            "self_reported": round(self_reported, 2),
            "objective": round(objective, 2),
            "bias": round(self_reported - objective, 2)
        })

    return evidence

def analyze_bias(evidence):
    """分析后期偏差"""
    late_stage = [e for e in evidence if e["objective"] > 0.7]
    if not late_stage:
        return 0
    return round(sum(e["bias"] for e in late_stage) / len(late_stage), 3)

if __name__ == "__main__":
    print("=" * 60)
    print("Q1: LLM 自我感知可靠性实验")
    print("=" * 60)

    evidence = simulate_task_execution()

    print("\n步骤 | 自评 | 客观 | 偏差")
    print("-" * 40)
    for e in evidence:
        print(f"{e['step']:4d} | {e['self_reported']:.2f} | {e['objective']:.2f} | {e['bias']:+.2f}")

    bias = analyze_bias(evidence)
    print(f"\n后期平均偏差: {bias:+.3f}")
    print(f"结论: {'存在系统性高估' if bias > 0.1 else '自评较准确'}")
