# Patterns API

**版本**: v0.1.6

Patterns API 参考文档 - 多 Agent 协作模式。

---

## 📋 目录

1. [Crew](#crew)
2. [CrewRole](#crewrole)
3. [智能协调](#智能协调)
4. [并行执行](#并行执行)
5. [容错恢复](#容错恢复)
6. [可观测性](#可观测性)
7. [工厂函数](#工厂函数)
8. [预设配置](#预设配置)

---

## Crew

### 概述

`Crew` 是多 Agent 协作的核心类，支持三种协作模式。

```python
from loom.patterns import Crew

crew = Crew(agents=[agent1, agent2])
result = await crew.run("任务描述")
```

### 构造函数

```python
Crew(
    agents: Optional[List[BaseAgent]] = None,
    roles: Optional[Dict[str, CrewRole]] = None,
    mode: str = "sequential",
    coordinator: Optional[BaseAgent] = None,
    # v0.1.6 增强功能
    use_smart_coordinator: bool = False,
    complexity_analyzer: Optional[ComplexityAnalyzer] = None,
    enable_parallel: bool = False,
    parallel_config: Optional[ParallelConfig] = None,
    artifact_store: Optional[ArtifactStore] = None,
    enable_error_recovery: bool = False,
    recovery_config: Optional[RecoveryConfig] = None,
    enable_checkpoint: bool = False,
    checkpoint_manager: Optional[CheckpointManager] = None,
    enable_tracing: bool = False,
    tracer: Optional[CrewTracer] = None,
    evaluator: Optional[CrewEvaluator] = None
)
```

#### 基础参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `agents` | `List[BaseAgent]` | `None` | Agent 列表 |
| `roles` | `Dict[str, CrewRole]` | `None` | 角色定义 |
| `mode` | `str` | `"sequential"` | 协作模式：sequential/parallel/coordinated |
| `coordinator` | `BaseAgent` | `None` | 协调器 Agent（coordinated 模式） |

#### v0.1.6 增强参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `use_smart_coordinator` | `bool` | `False` | 使用智能协调器 |
| `complexity_analyzer` | `ComplexityAnalyzer` | `None` | 复杂度分析器 |
| `enable_parallel` | `bool` | `False` | 启用并行执行 |
| `parallel_config` | `ParallelConfig` | `None` | 并行配置 |
| `artifact_store` | `ArtifactStore` | `None` | 制品存储 |
| `enable_error_recovery` | `bool` | `False` | 启用容错 |
| `recovery_config` | `RecoveryConfig` | `None` | 恢复配置 |
| `enable_checkpoint` | `bool` | `False` | 启用检查点 |
| `checkpoint_manager` | `CheckpointManager` | `None` | 检查点管理器 |
| `enable_tracing` | `bool` | `False` | 启用追踪 |
| `tracer` | `CrewTracer` | `None` | 追踪器 |
| `evaluator` | `CrewEvaluator` | `None` | 评估器 |

#### 示例

**基础用法**：
```python
import loom
from loom.builtin import OpenAILLM
from loom.patterns import Crew

llm = OpenAILLM(api_key="...")

agent1 = loom.agent(name="researcher", llm=llm)
agent2 = loom.agent(name="writer", llm=llm)

crew = Crew(agents=[agent1, agent2], mode="sequential")
result = await crew.run("写一篇文章")
```

**v0.1.6 完整配置**：
```python
from loom.patterns import (
    Crew, SmartCoordinator, ParallelConfig,
    RecoveryConfig, CrewTracer, CrewEvaluator
)

crew = Crew(
    agents=[agent1, agent2, agent3],
    mode="coordinated",
    coordinator=SmartCoordinator(llm=llm),
    use_smart_coordinator=True,
    enable_parallel=True,
    parallel_config=ParallelConfig(
        max_concurrent_agents=2,
        max_concurrent_tools=5
    ),
    enable_error_recovery=True,
    recovery_config=RecoveryConfig(max_retries=3),
    enable_tracing=True,
    tracer=CrewTracer(),
    evaluator=CrewEvaluator(llm=llm)
)
```

---

### 核心方法

#### `run()`

执行 Crew 任务。

```python
async def run(
    self,
    task: str,
    context: Optional[Dict] = None
) -> str
```

**参数**：
- `task` (`str`): 任务描述
- `context` (`Dict`, 可选): 上下文信息

**返回值**：
- `str`: 任务结果

**示例**：
```python
result = await crew.run(
    task="研究 AI Agent 并写一篇文章",
    context={"deadline": "2024-12-20"}
)
print(result)
```

---

#### `add_agent()`

添加 Agent 到 Crew。

```python
def add_agent(self, agent: BaseAgent) -> None
```

**参数**：
- `agent` (`BaseAgent`): Agent 实例

**示例**：
```python
crew = Crew(agents=[agent1])
crew.add_agent(agent2)  # 动态添加
```

---

#### `get_stats()`

获取 Crew 统计信息。

```python
def get_stats(self) -> dict
```

**返回值**：
```python
{
    "num_agents": int,              # Agent 数量
    "mode": str,                    # 协作模式
    "total_tasks_completed": int,   # 完成的任务数
    "total_cost": float,            # 总成本
    "agents_stats": [...]           # 各 Agent 统计
}
```

**示例**：
```python
stats = crew.get_stats()
print(f"完成任务: {stats['total_tasks_completed']}")
print(f"总成本: ${stats['total_cost']:.2f}")
```

---

### 类方法

#### `from_config()`

从配置创建 Crew。

```python
@classmethod
def from_config(cls, config: Dict) -> Crew
```

**参数**：
- `config` (`Dict`): 配置字典

**示例**：
```python
config = {
    "agents": [
        {"name": "researcher", "llm": llm},
        {"name": "writer", "llm": llm}
    ],
    "mode": "sequential"
}

crew = Crew.from_config(config)
```

---

## CrewRole

### 概述

`CrewRole` 定义 Crew 中 Agent 的角色。

```python
from loom.patterns import CrewRole

role = CrewRole(
    agent=agent,
    can_delegate=True,
    priority=1
)
```

### 数据类定义

```python
@dataclass
class CrewRole:
    agent: BaseAgent
    can_delegate: bool = False
    priority: int = 0
    dependencies: List[str] = field(default_factory=list)
```

#### 字段

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `agent` | `BaseAgent` | 必需 | Agent 实例 |
| `can_delegate` | `bool` | `False` | 是否可以委托任务 |
| `priority` | `int` | `0` | 优先级（越大越高） |
| `dependencies` | `List[str]` | `[]` | 依赖的其他角色名称 |

#### 示例

```python
from loom.patterns import Crew, CrewRole

researcher = CrewRole(
    agent=loom.agent(name="researcher", llm=llm),
    can_delegate=False,
    priority=2
)

writer = CrewRole(
    agent=loom.agent(name="writer", llm=llm),
    can_delegate=False,
    priority=1,
    dependencies=["researcher"]  # 依赖 researcher
)

crew = Crew(
    agents={
        "researcher": researcher,
        "writer": writer
    },
    mode="sequential"
)
```

---

## 智能协调

### SmartCoordinator

智能任务分解和调度。

```python
from loom.patterns import SmartCoordinator

coordinator = SmartCoordinator(
    llm: BaseLLM,
    complexity_threshold: float = 0.5
)
```

#### 参数

- `llm` (`BaseLLM`): LLM 实例
- `complexity_threshold` (`float`): 复杂度阈值（0-1）

#### 示例

```python
from loom.patterns import Crew, SmartCoordinator

crew = Crew(
    agents=[agent1, agent2, agent3],
    mode="coordinated",
    coordinator=SmartCoordinator(llm=llm),
    use_smart_coordinator=True
)

# SmartCoordinator 会：
# 1. 分析任务复杂度
# 2. 分解为子任务
# 3. 智能分配给 Agents
# 4. 协调执行顺序
```

---

### TaskComplexity

任务复杂度分析结果。

```python
@dataclass
class TaskComplexity:
    score: float              # 0-1，越大越复杂
    dimensions: Dict[str, float]  # 各维度得分
    recommendation: str       # 推荐策略
```

#### 示例

```python
complexity = coordinator.analyze_complexity("复杂的研究任务")
print(f"复杂度: {complexity.score}")
print(f"推荐: {complexity.recommendation}")
```

---

### SubTask

子任务定义。

```python
@dataclass
class SubTask:
    id: str
    description: str
    assigned_to: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    status: str = "pending"
```

---

## 并行执行

### ParallelExecutor

并行执行管理器。

```python
from loom.patterns import ParallelExecutor, ParallelConfig

executor = ParallelExecutor(
    config=ParallelConfig(
        max_concurrent_agents=3,
        max_concurrent_tools=5
    )
)
```

### ParallelConfig

并行配置。

```python
@dataclass
class ParallelConfig:
    max_concurrent_agents: int = 3     # 最大并发 Agent 数
    max_concurrent_tools: int = 5      # 最大并发工具数
    timeout_per_agent: float = 300.0   # Agent 超时（秒）
    timeout_per_tool: float = 60.0     # 工具超时（秒）
```

#### 示例

```python
from loom.patterns import Crew, ParallelConfig

crew = Crew(
    agents=[agent1, agent2, agent3],
    mode="parallel",
    enable_parallel=True,
    parallel_config=ParallelConfig(
        max_concurrent_agents=2,
        max_concurrent_tools=10
    )
)

# 性能提升：
# - Agent 级并行：多个 Agent 同时执行
# - 工具级并行：单个 Agent 的多个工具调用并行
```

---

## 容错恢复

### ErrorRecovery

四层容错策略。

```python
from loom.patterns import ErrorRecovery, RecoveryConfig

recovery = ErrorRecovery(
    config=RecoveryConfig(
        max_retries=3,
        backoff_factor=2.0,
        enable_fallback=True
    )
)
```

### RecoveryConfig

恢复配置。

```python
@dataclass
class RecoveryConfig:
    max_retries: int = 3              # 最大重试次数
    backoff_factor: float = 2.0       # 退避因子
    enable_fallback: bool = True      # 启用降级
    enable_partial_success: bool = True  # 允许部分成功
```

#### 四层策略

1. **重试**：自动重试失败的操作
2. **降级**：使用更简单的策略
3. **部分成功**：接受部分结果
4. **优雅失败**：返回有意义的错误信息

#### 示例

```python
from loom.patterns import Crew, RecoveryConfig

crew = Crew(
    agents=[agent1, agent2],
    enable_error_recovery=True,
    recovery_config=RecoveryConfig(
        max_retries=3,
        backoff_factor=2.0,
        enable_fallback=True,
        enable_partial_success=True
    )
)

# 容错行为：
# - Agent 失败 → 自动重试（最多 3 次）
# - 仍失败 → 降级到更简单策略
# - 无法完成 → 返回部分结果
# - 完全失败 → 优雅错误信息
```

---

## 可观测性

### CrewTracer

追踪 Crew 执行。

```python
from loom.patterns import CrewTracer

tracer = CrewTracer()

crew = Crew(
    agents=[agent1, agent2],
    enable_tracing=True,
    tracer=tracer
)

result = await crew.run("任务")

# 查看追踪信息
trace = tracer.get_trace()
print(trace)
```

#### 追踪信息

```python
{
    "task_id": str,
    "start_time": float,
    "end_time": float,
    "duration": float,
    "agents_used": List[str],
    "steps": [
        {
            "agent": str,
            "action": str,
            "timestamp": float,
            "duration": float
        }
    ],
    "metadata": dict
}
```

---

### CrewEvaluator

评估 Crew 结果质量。

```python
from loom.patterns import CrewEvaluator

evaluator = CrewEvaluator(llm=llm)

crew = Crew(
    agents=[agent1, agent2],
    evaluator=evaluator
)

result = await crew.run("任务")

# 自动评估
evaluation = evaluator.get_last_evaluation()
print(f"质量分数: {evaluation['quality_score']}")
print(f"评价: {evaluation['feedback']}")
```

#### 评估维度

- **完整性**：任务是否完全完成
- **准确性**：结果是否准确
- **连贯性**：结果是否逻辑连贯
- **效率**：资源使用是否高效

---

## 工厂函数

### `sequential_crew()`

创建顺序执行 Crew。

```python
from loom.patterns import sequential_crew

crew = sequential_crew(agents=[agent1, agent2])
```

等价于：
```python
crew = Crew(agents=[agent1, agent2], mode="sequential")
```

---

### `parallel_crew()`

创建并行执行 Crew。

```python
from loom.patterns import parallel_crew

crew = parallel_crew(
    agents=[agent1, agent2, agent3],
    max_concurrent=2
)
```

等价于：
```python
crew = Crew(
    agents=[agent1, agent2, agent3],
    mode="parallel",
    enable_parallel=True,
    parallel_config=ParallelConfig(max_concurrent_agents=2)
)
```

---

### `coordinated_crew()`

创建协调执行 Crew。

```python
from loom.patterns import coordinated_crew

crew = coordinated_crew(
    agents=[agent1, agent2],
    coordinator_llm=llm
)
```

等价于：
```python
crew = Crew(
    agents=[agent1, agent2],
    mode="coordinated",
    coordinator=SmartCoordinator(llm=llm),
    use_smart_coordinator=True
)
```

---

## 预设配置

### CrewPresets

预定义的 Crew 配置。

```python
from loom.patterns import CrewPresets

# 生产就绪配置
crew = CrewPresets.production_ready(
    agents=[agent1, agent2],
    llm=llm
)

# 快速原型配置
crew = CrewPresets.fast_prototype(
    agents=[agent1, agent2]
)

# 高可靠性配置
crew = CrewPresets.high_reliability(
    agents=[agent1, agent2],
    llm=llm
)
```

#### production_ready

```python
{
    "enable_parallel": True,
    "enable_error_recovery": True,
    "enable_checkpoint": True,
    "enable_tracing": True,
    "evaluator": CrewEvaluator(llm=llm),
    "parallel_config": ParallelConfig(max_concurrent_agents=3),
    "recovery_config": RecoveryConfig(max_retries=3)
}
```

#### fast_prototype

```python
{
    "mode": "sequential",
    "enable_parallel": False,
    "enable_error_recovery": False
}
```

#### high_reliability

```python
{
    "enable_error_recovery": True,
    "enable_checkpoint": True,
    "recovery_config": RecoveryConfig(
        max_retries=5,
        enable_fallback=True,
        enable_partial_success=True
    )
}
```

---

## 完整示例

### 基础 Sequential Crew

```python
import loom
from loom.builtin import OpenAILLM
from loom.patterns import Crew

llm = OpenAILLM(api_key="...")

researcher = loom.agent(
    name="researcher",
    llm=llm,
    system_prompt="你是研究员，负责收集信息"
)

writer = loom.agent(
    name="writer",
    llm=llm,
    system_prompt="你是撰写员，负责整理成文章"
)

crew = Crew(agents=[researcher, writer], mode="sequential")
result = await crew.run("写一篇关于 AI Agent 的文章")
```

### v0.1.6 完整功能

```python
from loom.patterns import (
    Crew, CrewRole,
    SmartCoordinator, ParallelConfig, RecoveryConfig,
    CrewTracer, CrewEvaluator
)

# 创建 Crew with 全部 v0.1.6 功能
crew = Crew(
    agents={
        "researcher": CrewRole(agent=researcher, priority=2),
        "analyst": CrewRole(agent=analyst, priority=1),
        "writer": CrewRole(agent=writer, dependencies=["researcher", "analyst"])
    },
    mode="coordinated",
    coordinator=SmartCoordinator(llm=llm),
    use_smart_coordinator=True,
    enable_parallel=True,
    parallel_config=ParallelConfig(
        max_concurrent_agents=2,
        max_concurrent_tools=5
    ),
    enable_error_recovery=True,
    recovery_config=RecoveryConfig(
        max_retries=3,
        enable_fallback=True
    ),
    enable_tracing=True,
    tracer=CrewTracer(),
    evaluator=CrewEvaluator(llm=llm)
)

result = await crew.run("完成复杂的研究报告")

# 查看追踪
trace = crew.tracer.get_trace()
print(f"执行时间: {trace['duration']:.2f}s")

# 查看评估
eval_result = crew.evaluator.get_last_evaluation()
print(f"质量分数: {eval_result['quality_score']}")
```

### 使用预设

```python
from loom.patterns import CrewPresets

# 生产环境：完整功能
prod_crew = CrewPresets.production_ready(
    agents=[agent1, agent2, agent3],
    llm=llm
)

# 开发环境：快速原型
dev_crew = CrewPresets.fast_prototype(
    agents=[agent1, agent2]
)

# 高可靠性：强化容错
reliable_crew = CrewPresets.high_reliability(
    agents=[agent1, agent2],
    llm=llm
)
```

---

## 相关文档

- [Crew 完整指南](../guides/patterns/crew.md) - 详细使用指南
- [Agents API](./agents.md) - Agent API 参考
- [架构设计](../architecture/overview.md) - 框架架构

---

**返回**: [API 参考](./README.md) | [文档首页](../README.md)
