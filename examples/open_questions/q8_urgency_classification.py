"""Q8: Urgency Classification Reliability

问题: 低/高/临界分类应完全由规则承担，还是需要"规则优先 + 分类器兜底"？
观测现象: 纯规则简单稳定但覆盖不足；分类器表达力强但延迟增加
实验设计: 比较"纯规则""纯分类器""规则优先+分类器兜底"三种方案
证据要求: 标注数据集、分类准确率、时延统计、误分案例、资源消耗
"""

import time
from loom.runtime.heartbeat import UrgencyClassifier

async def experiment_urgency_classification():
    approaches = ["rule_only", "classifier_only", "rule_first_classifier_fallback"]

    results = {}
    test_events = load_labeled_events()  # 标注数据集

    for approach in approaches:
        classifier = UrgencyClassifier(approach=approach)
        metrics = {"correct": 0, "total": 0, "latencies": [], "misclassified": []}

        for event in test_events:
            start = time.time()
            predicted = await classifier.classify(event)
            latency = time.time() - start

            metrics["latencies"].append(latency)
            metrics["total"] += 1

            if predicted == event.true_urgency:
                metrics["correct"] += 1
            else:
                metrics["misclassified"].append(event)

        results[approach] = {
            "accuracy": metrics["correct"] / metrics["total"],
            "avg_latency_ms": sum(metrics["latencies"]) / len(metrics["latencies"]) * 1000,
            "misclassified_count": len(metrics["misclassified"])
        }

    return results

def load_labeled_events():
    return []  # 加载标注数据
