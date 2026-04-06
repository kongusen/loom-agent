"""P0 实施测试"""

import sys
sys.path.insert(0, '/Users/shan/work/uploads/loom-agent')

from loom.cluster.dmax_strategy import get_dmax_for_task
from loom.context.event_aggregator import EventAggregator
from loom.cluster.subagent_result import create_structured_result

print("=" * 60)
print("P0 实施验证")
print("=" * 60)

# 测试 Q2: d_max 策略
print("\n1. Q2 - 任务类型感知的 d_max")
for task_type in ["code", "research", "planning", "debugging"]:
    dmax = get_dmax_for_task(task_type)
    print(f"   {task_type:10s} -> d_max = {dmax}")

# 测试 Q9: 事件聚合
print("\n2. Q9 - 事件聚合策略")
events = [{"type": "file_change", "path": f"file_{i}.py"} for i in range(20)]
aggregator = EventAggregator()
aggregated = aggregator.aggregate(events)
print(f"   原始事件: {len(events)}")
print(f"   聚合后: {len(aggregated)}")
print(f"   压缩率: {(1 - len(aggregated)/len(events))*100:.1f}%")

# 测试 Q10: 结构化回传
print("\n3. Q10 - Sub-Agent 结构化回传")
result = create_structured_result(
    result={"status": "success"},
    result_type="database_analysis",
    tools_used=["db_inspector", "query_analyzer"]
)
print(f"   Schema: {result.schema}")
print(f"   工具上下文: {len(result.tool_context)} 个工具")

print("\n" + "=" * 60)
print("P0 实施完成 ✓")
print("=" * 60)
