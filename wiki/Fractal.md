# 分形架构

`loom/fractal/` 实现了基于公理 A3（分形自相似）的递归组合能力。

## 公理 A3

```
∀node ∈ System: structure(node) ≅ structure(System)
```

每个节点的结构与整个系统同构 — 节点可以包含子节点，子节点拥有与父节点相同的能力。

## 文件结构

```
loom/fractal/
├── container.py         # NodeContainer - 单子节点容器
├── parallel_executor.py # ParallelExecutor - 并行执行器
├── synthesizer.py       # Synthesizer - 结果聚合器
├── resolvers.py         # 依赖解析器
├── memory.py            # 分形记忆管理
├── sync.py              # 同步工具
└── utils.py             # 工具函数
```

## NodeContainer

最基础的分形组合单元，包装单个子节点：

```python
from loom.fractal import NodeContainer

container = NodeContainer(
    node_id="container-1",
    agent_card=AgentCard(...),
    child=agent,           # 子节点
    max_depth=100,         # 最大递归深度
)

# 执行时委派给子节点
result = await container.execute_task(task)
```

设计原则：
- 组合模式 — 容器本身也是节点
- 透明性 — 容器和叶子节点实现相同接口（NodeProtocol）
- 最简原则 — 只支持单子节点，多节点编排使用 ParallelExecutor

## ParallelExecutor

并行执行多个子节点：

```python
from loom.fractal import ParallelExecutor

executor = ParallelExecutor(
    node_id="parallel-1",
    children=[agent_1, agent_2, agent_3],
)

# 并行执行，收集所有结果
results = await executor.execute_all(tasks)
```

## Synthesizer

聚合多个子节点的执行结果：

```python
from loom.fractal import Synthesizer

synthesizer = Synthesizer(
    strategy="merge",  # merge / vote / best
)

final_result = await synthesizer.synthesize(results)
```

## Agent 中的分形实现

Agent 内置了分形能力，通过 `_create_child_node` 创建子节点：

### 规划分形

`create_plan` 元工具触发时，为每个步骤创建子 Agent：

```
Parent Agent
  ├─ create_plan(goal, steps=[s1, s2, s3])
  │
  ├─ Child Agent (step 1) → 执行 s1
  ├─ Child Agent (step 2) → 执行 s2
  └─ Child Agent (step 3) → 执行 s3
      │
      └─ LLM 综合生成最终答案
```

### 委派分形

`delegate_task` 元工具触发时，创建子 Agent 执行子任务：

```
Parent Agent
  └─ delegate_task(subtask="分析数据")
      └─ Child Agent → 执行子任务 → 返回结果
```

### 继承规则

| 类型 | 资源 | 行为 |
|------|------|------|
| 共享 | `skill_registry`, `tool_registry`, `event_bus`, `sandbox_manager` | 父子共用同一实例 |
| 继承 | `config` (AgentConfig) | 子节点继承并可增量覆盖 |
| 继承 | `system_prompt` | 子节点继承，计划步骤会追加上下文 |
| 继承 | `llm_provider`, `tools` | 子节点使用相同的 LLM 和工具 |
| 独立 | `memory` (MemoryManager) | 子节点独立实例，通过 `parent_memory` 关联 |
| 独立 | `active_skills` | 子节点独立的激活状态 |

### 递归深度

每个子节点的 `recursive_depth` 自动递增，框架通过此值防止无限递归。

```python
parent._recursive_depth = 0
child._recursive_depth = 1   # 自动 +1
grandchild._recursive_depth = 2
```

### 记忆继承

子节点的 MemoryManager 通过 `parent` 参数关联父节点：

```python
child_memory = MemoryManager(
    node_id="child-1",
    parent=parent_memory,  # 自动继承 SHARED/GLOBAL 记忆
)
```

父节点将任务内容写入 SHARED 作用域，子节点自动可见。
