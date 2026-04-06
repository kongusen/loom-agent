"""P1 实施测试"""

import sys
sys.path.insert(0, '/Users/shan/work/uploads/loom-agent')

from loom.runtime.heartbeat_strategy import HeartbeatStrategy, Phase
from loom.tools.resource_allocator import allocate_resources
from loom.cluster.cache_scheduler import CacheAwareScheduler

print("=" * 60)
print("P1 实施验证")
print("=" * 60)

# 测试 Q7: 动态心跳间隔
print("\n4. Q7 - 动态心跳间隔")
hb = HeartbeatStrategy("by_phase")
print(f"   ACT 阶段: {hb.get_interval(Phase.ACT)}s")
print(f"   REASON 阶段: {hb.get_interval(Phase.REASON)}s")

hb_vol = HeartbeatStrategy("by_volatility")
print(f"   高波动 (0.8): {hb_vol.get_interval(Phase.ACT, 0.8)}s")
print(f"   低波动 (0.3): {hb_vol.get_interval(Phase.ACT, 0.3)}s")

# 测试 Q11: Effort 资源分配
print("\n5. Q11 - Effort 资源分配")
for effort in ["low", "medium", "high"]:
    res = allocate_resources(effort)
    print(f"   {effort:6s}: {res.timeout}s, {res.token_budget} tokens, 深度 {res.tool_depth}")

# 测试 Q12: Cache-aware 调度
print("\n6. Q12 - Cache-aware 调度")
scheduler = CacheAwareScheduler()
scheduler.cache_hit_rate = 0.65
print(f"   探索任务: {scheduler.select_model('explore', True)}")
print(f"   推理任务 (有cache): {scheduler.select_model('reason', True)}")
print(f"   推理任务 (无cache): {scheduler.select_model('reason', False)}")

print("\n" + "=" * 60)
print("P1 实施完成 ✓")
print("=" * 60)
