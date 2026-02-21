# Runtime

Runtime 提供集群级编排能力，AmoebaLoop 实现 6 阶段自组织循环。

## Runtime — 集群编排

```python
from loom import Runtime, AgentConfig
from loom.types import TaskAd, CapabilityProfile

rt = Runtime(
    provider=provider,
    config=AgentConfig(system_prompt="你是助手", max_steps=3),
)

# 添加不同能力的节点
rt.add_agent(capabilities=CapabilityProfile(scores={"code": 0.9}))
rt.add_agent(capabilities=CapabilityProfile(scores={"data": 0.8}))
```

## 提交任务

Runtime 自动通过拍卖选择最佳节点执行：

```python
result = await rt.submit(TaskAd(domain="code", description="实现排序算法"))
print(result[:60])

result2 = await rt.submit(TaskAd(domain="data", description="分析销售数据"))
print(result2[:60])
```

## 健康检查

```python
reports = rt.health_check()
for r in reports:
    print(f"{r.node_id}: {r.status}")

rt.dispose()
```

## AmoebaLoop — 6 阶段自组织循环

AmoebaLoop 实现完整的自组织执行流程：

```
SENSE → MATCH → SCALE + EXECUTE → EVALUATE + ADAPT
```

| 阶段 | 说明 |
|------|------|
| SENSE | 分析任务复杂度和领域 |
| MATCH | 拍卖匹配最佳节点 |
| SCALE | 按需扩缩节点 |
| EXECUTE | 执行任务 |
| EVALUATE | 评估执行结果 |
| ADAPT | 更新能力评分 |

```python
from loom import ClusterManager, RewardBus, LifecycleManager, ClusterConfig
from loom.cluster.planner import TaskPlanner
from loom.cluster.skill_registry import SkillNodeRegistry
from loom.cluster.amoeba_loop import AmoebaLoop
from loom.types import AgentNode, CapabilityProfile

cluster = ClusterManager()
cluster.add_node(AgentNode(
    id="coder",
    capabilities=CapabilityProfile(scores={"code": 0.9}),
    agent=agent,
))

loop = AmoebaLoop(
    cluster=cluster,
    reward_bus=RewardBus(),
    lifecycle=LifecycleManager(ClusterConfig(max_depth=3)),
    planner=TaskPlanner(provider),
    skill_registry=SkillNodeRegistry(),
    llm=provider,
)

async for event in loop.execute(ctx):
    if event.type == "text_delta":
        print(event.text, end="")
    elif event.type == "done":
        print(f"\n完成: steps={event.steps}")
```

## API 参考

```python
# Runtime
rt = Runtime(provider, config)
rt.add_agent(capabilities=...)
await rt.submit(task: TaskAd) -> str
rt.health_check() -> list[HealthReport]
rt.dispose()

# AmoebaLoop
loop = AmoebaLoop(cluster, reward_bus, lifecycle, planner, skill_registry, llm)
async for event in loop.execute(ctx): ...
```

> 完整示例：[`examples/demo/12_runtime.py`](../examples/demo/12_runtime.py) | [`examples/demo/13_amoeba.py`](../examples/demo/13_amoeba.py)
