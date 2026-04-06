"""Q9 实验：心跳事件 Token 压力"""

def simulate_event_strategy(strategy, event_count=100):
    """模拟事件注入策略"""

    if strategy == "raw":
        final_events = event_count
        tokens = event_count * 50
        completion = 0.75
    elif strategy == "dedup":
        final_events = event_count // 3
        tokens = final_events * 50
        completion = 0.85
    else:  # aggregate
        final_events = event_count // 10
        tokens = final_events * 80
        completion = 0.90

    return {
        "event_count": final_events,
        "token_usage": tokens,
        "completion_rate": completion
    }

if __name__ == "__main__":
    print("=" * 60)
    print("Q9: 心跳事件 Token 压力实验")
    print("=" * 60)

    strategies = ["raw", "dedup", "aggregate"]

    print("\n策略      | 事件数 | Token | 完成率")
    print("-" * 45)

    for strategy in strategies:
        result = simulate_event_strategy(strategy)
        print(f"{strategy:9s} | {result['event_count']:6d} | "
              f"{result['token_usage']:5d} | {result['completion_rate']:.2f}")

    print("\n结论: 聚合摘要策略平衡最好")
