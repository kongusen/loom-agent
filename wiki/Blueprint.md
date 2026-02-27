# Blueprint Forge

Blueprint Forge 是 v0.6.3 引入的自主 Agent 创建机制。当集群中没有合适的 Agent 能处理某个任务时，由 LLM 设计一个专门的 Agent 蓝图，然后基于蓝图孵化 Agent 并让其进入完整的阿米巴生命周期。

## 核心概念

### AgentBlueprint — 蓝图数据结构

蓝图是 Agent 的模板，包含创建专家 Agent 所需的全部信息：

```python
from loom.types import AgentBlueprint

bp = AgentBlueprint(
    name="data-analyst",
    description="Handles data analysis and visualization tasks",
    system_prompt="You are a data analysis specialist...",
    domain="data",
    domain_scores={"data": 0.8, "code": 0.4},
    tools_filter=["calc", "plot"],  # 空列表 = 继承父节点全部工具
)
```

关键字段：

| 字段 | 说明 |
|------|------|
| `name` | 人类可读名称（kebab-case） |
| `description` | 触发描述，用于语义路由匹配 |
| `system_prompt` | 定制的系统提示词 |
| `domain` | 主领域 |
| `domain_scores` | 初始能力分数 |
| `tools_filter` | 允许使用的工具子集 |
| `generation` | 进化代数（从 1 开始） |
| `parent_id` | 进化来源蓝图 ID |
| `avg_reward` | 平均奖励分数 |

## 完整生命周期

```
任务到达
  │
  ▼
SENSE+MATCH（语义路由）
  │
  ├─ 匹配到现有 agent → 正常执行
  ├─ 匹配到已有蓝图 → spawn(blueprint) → 执行
  └─ 无匹配 → forge(task) → spawn → 执行
                                │
                                ▼
                          进入阿米巴生命周期
                          ├─ 参与竞拍（bid）
                          ├─ 执行任务
                          ├─ 接收 reward
                          │   ├─ 高 reward → 蓝图强化
                          │   └─ 低 reward → 蓝图进化（evolve）
                          └─ 健康检查
                              ├─ healthy → 继续
                              └─ dying → apoptosis
                                          └─ 多次失败 → prune（淘汰蓝图）
```

## 使用方式

### 1. 锻造蓝图（Forge）

LLM 分析任务需求，设计专门的 Agent 蓝图：

```python
from loom.cluster.blueprint_forge import BlueprintForge
from loom.cluster.blueprint_store import BlueprintStore
from loom.types import TaskAd

store = BlueprintStore()
forge = BlueprintForge(llm=provider, store=store)

task = TaskAd(domain="data", description="分析销售趋势并生成可视化报告")
blueprint = await forge.forge(task, context="Q4 quarterly review")
print(blueprint.name)           # e.g. "sales-trend-analyst"
print(blueprint.system_prompt)  # LLM 生成的定制提示词
```

Forge 的 prompt 策略借鉴 Anthropic skill-creator：要求 LLM 解释 "why" 而非堆砌 "MUST" 规则，避免过拟合。

### 2. 孵化 Agent（Spawn）

基于蓝图创建 Agent 实例，注入定制配置：

```python
from loom.types import AgentNode, CapabilityProfile

parent = AgentNode(id="root", capabilities=CapabilityProfile(scores={"general": 0.5}))
node = forge.spawn(blueprint, parent)

print(node.id)            # "forged:a1b2c3d4"
print(node.blueprint_id)  # 关联的蓝图 ID
result = await node.agent.run("执行数据分析任务")
```

### 3. 蓝图匹配（Match）

在已有蓝图中语义匹配最适合当前任务的蓝图：

```python
task = TaskAd(domain="data", description="预测下季度用户增长")
matched = await forge.match(task)
if matched:
    node = forge.spawn(matched, parent)
else:
    # 无匹配，需要 forge 新蓝图
    bp = await forge.forge(task)
    node = forge.spawn(bp, parent)
```

### 4. 蓝图进化（Evolve）

当蓝图的平均 reward 低于阈值时，LLM 分析失败模式并优化 description 和 system_prompt：

```python
# 手动触发进化
new_bp = await forge.evolve(blueprint)
print(new_bp.generation)  # 2（parent.generation + 1）
print(new_bp.parent_id)   # 原蓝图 ID
```

在 AmoebaLoop 中，进化会自动触发：当 `avg_reward < evolve_threshold`（默认 0.35）且评估窗口 >= `evolve_window`（默认 5）时。

### 5. 蓝图持久化（BlueprintStore）

内存存储 + 可选 JSON 文件持久化：

```python
from pathlib import Path
from loom.cluster.blueprint_store import BlueprintStore

# 纯内存
store = BlueprintStore()

# 带文件持久化
store = BlueprintStore(persist_path=Path("data/blueprints.json"))

store.save(blueprint)
store.get(blueprint.id)
store.find_by_domain("data")
store.list_all()

# 淘汰低效蓝图
pruned = store.prune(min_reward=0.2, min_tasks=3)
```

## 配置

在 `ClusterConfig` 中控制 Blueprint Forge 行为：

```python
from loom import ClusterConfig

config = ClusterConfig(
    blueprint_forge_enabled=True,       # 启用蓝图锻造
    blueprint_evolve_threshold=0.35,    # 低于此 reward 触发进化
    blueprint_evolve_window=5,          # 评估窗口大小
    blueprint_prune_min_reward=0.2,     # 淘汰阈值
    blueprint_prune_min_tasks=3,        # 最少任务数才能淘汰
    blueprint_max_count=50,             # 蓝图数量上限
)
```

## 与 AmoebaLoop 集成

Blueprint Forge 在阿米巴循环的三个阶段自动介入：

**SENSE+MATCH** — 当拍卖无赢家时，先尝试 `match()` 匹配已有蓝图，再尝试 `forge()` 锻造新蓝图：

```python
from loom.cluster.amoeba_loop import AmoebaLoop

loop = AmoebaLoop(cluster=cm, lifecycle=lm, reward=rb, forge=forge)
result = await loop.run("分析用户行为数据")
# 如果无现有 agent 匹配 → 自动 forge + spawn
```

**EVALUATE** — 执行后 reward 自动传播到蓝图，更新 `avg_reward` 和 `reward_history`。

**ADAPT** — 低 reward 蓝图自动触发 `evolve()`，概率性执行 `prune()` 清理低效蓝图。

## API 参考

```python
# BlueprintForge
forge = BlueprintForge(llm, store, evolve_threshold=0.35, evolve_window=5)
await forge.forge(task, context="") -> AgentBlueprint
forge.spawn(blueprint, parent) -> AgentNode
await forge.evolve(blueprint) -> AgentBlueprint
await forge.match(task) -> AgentBlueprint | None

# BlueprintStore
store = BlueprintStore(persist_path=None)
store.save(bp)
store.get(bp_id) -> AgentBlueprint | None
store.list_all() -> list[AgentBlueprint]
store.list_descriptions() -> list[dict]
store.find_by_domain(domain) -> list[AgentBlueprint]
store.prune(min_reward, min_tasks) -> list[str]
store.count() -> int
```

> 相关文档：[Cluster](Cluster) | [Runtime](Runtime)
