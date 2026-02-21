# Cluster

集群系统通过能力评分拍卖机制，自动选择最佳 Agent 执行任务，并通过 RewardBus 持续优化能力评估。

## 集群拍卖

### 注册节点

```python
from loom import Agent, AgentConfig, ClusterManager, ClusterConfig
from loom.types import AgentNode, CapabilityProfile, TaskAd

cm = ClusterManager(ClusterConfig())

coder = AgentNode(
    id="coder",
    capabilities=CapabilityProfile(scores={"code": 0.9, "data": 0.3}),
    agent=Agent(provider=provider, config=AgentConfig(
        system_prompt="你是编程专家", max_steps=3
    )),
)
analyst = AgentNode(
    id="analyst",
    capabilities=CapabilityProfile(scores={"code": 0.3, "data": 0.9}),
    agent=Agent(provider=provider, config=AgentConfig(
        system_prompt="你是数据分析师", max_steps=3
    )),
)
cm.add_node(coder)
cm.add_node(analyst)
```

### 竞标选择

```python
task = TaskAd(domain="code", description="实现快速排序")
winner = cm.select_winner(task)
print(winner.id)  # "coder"

task2 = TaskAd(domain="data", description="分析销售趋势")
winner2 = cm.select_winner(task2)
print(winner2.id)  # "analyst"
```

### 胜出节点执行

```python
result = await winner.agent.run("用Python实现快速排序")
print(result.content)
```

## RewardBus — EMA 能力评估

执行结果驱动能力评分的指数移动平均（EMA）更新：

```python
from loom import RewardBus
from loom.types import RewardRecord

rb = RewardBus(alpha=0.3)

# 真实执行后评估
result = await node.agent.run("用一行Python代码实现列表反转")
success = len(result.content) > 10
rb.evaluate(node, task, success=success, token_cost=100)
print(node.capabilities.scores["code"])  # 0.596

# 连续成功 → EMA 收敛到高分
for _ in range(5):
    rb.evaluate(node, task, success=True, token_cost=100)
print(node.capabilities.scores["code"])  # 0.782
```

## LifecycleManager — 健康检查

```python
from loom import LifecycleManager, ClusterConfig
from loom.types import RewardRecord

lm = LifecycleManager(ClusterConfig(max_depth=3, mitosis_threshold=0.6))
node.reward_history = [RewardRecord(reward=0.8, domain="code")]
report = lm.check_health(node)
print(report.status)  # "healthy"
```

## API 参考

```python
# ClusterManager
cm = ClusterManager(ClusterConfig())
cm.add_node(node: AgentNode)
cm.select_winner(task: TaskAd) -> AgentNode
cm.get_node(id: str) -> AgentNode

# RewardBus
rb = RewardBus(alpha=0.3)
rb.evaluate(node, task, success, token_cost)

# LifecycleManager
lm = LifecycleManager(config)
lm.check_health(node) -> HealthReport
```

> 完整示例：[`examples/demo/09_cluster.py`](../examples/demo/09_cluster.py) | [`examples/demo/10_reward.py`](../examples/demo/10_reward.py)
