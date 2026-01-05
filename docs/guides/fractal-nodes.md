# 分形节点 (Fractal Nodes) 指南

## 概述

分形节点（Fractal Nodes）支持**自组织的 Agent 结构**，能够根据任务复杂度动态调整。系统提供三种使用模式：

1.  **自动模式 (Automatic Mode)**：自动分解复杂任务（由 System 2 触发）
2.  **手动模式 (Manual Mode)**：构建具有完全控制权的自定义流水线
3.  **混合模式 (Hybrid Mode)**：结合手动结构与自动增长

---

## 快速开始

### 1. 自动分形模式 (最简单)

让 Agent 自动分解复杂任务：

```python
import asyncio
from loom.node import create_fractal_agent
from loom.config.fractal import GrowthTrigger

async def main():
    # 创建自动分形 Agent
    agent = await create_fractal_agent(
        node_id="auto_agent",
        enable_fractal=True,
        fractal_trigger=GrowthTrigger.SYSTEM2,  # 在 System 2 激活时触发
        max_depth=3,
        max_children=5
    )

    # 简单任务 - 直接执行
    result1 = await agent.execute("2+2 等于几？")

    # 复杂任务 - 自动分解
    result2 = await agent.execute("""
        研究量子计算，分析其对密码学、机器学习和药物发现的影响，
        并创建一份综合报告。
    """)
    
    # 查看生成的结构
    print(agent.visualize_structure())

asyncio.run(main())
```

### 2. 手动构建流水线

构建自定义的 Agent 流水线：

```python
from loom.node import build_pipeline

pipeline = (
    build_pipeline("research", llm)
    .coordinator("orchestrator")
    .parallel([
        ("ai_research", "specialist"),
        ("market_research", "specialist")
    ])
    .aggregator("synthesizer")
    .build()
)
```

### 3. 使用模板

使用预置模板快速创建：

```python
from loom.node import PipelineTemplate

# 顺序处理
pipeline = PipelineTemplate.sequential_pipeline(
    name="analysis",
    steps=["collect", "analyze", "report"]
)
```

---

## 配置选项

### FractalConfig

```python
from loom.config.fractal import FractalConfig, GrowthTrigger

config = FractalConfig(
    # 启用/禁用分形模式
    enabled=True,

    # 何时触发自动增长
    growth_trigger=GrowthTrigger.SYSTEM2,  # SYSTEM2 | ALWAYS | MANUAL | NEVER

    # 结构限制
    max_depth=3,              # 最大深度
    max_children=5,           # 每个节点的最大子节点数
    max_total_nodes=20,       # 最大节点总数

    # 增长阈值
    complexity_threshold=0.7, # 触发增长的任务复杂度 (0-1)
    confidence_threshold=0.6, # 不增长的最小置信度

    # 自动剪枝
    enable_auto_pruning=True,
    pruning_threshold=0.3,    # 适应度低于此值将被剪枝
)
```

### YAML 配置

你可以在 `agent.yaml` 中直接配置：

```yaml
agents:
  - name: "deep-researcher"
    role: "Researcher"
    fractal:
      enabled: true
      growth_trigger: "system2"
      max_depth: 3
      complexity_threshold: 0.7
```

---

## 高级用法

### 运行时增强

为现有的 Agent 添加分形能力：

```python
from loom.node import add_fractal_to_agent

agent = AgentNode(...)

add_fractal_to_agent(
    agent,
    enable=True,
    growth_trigger=GrowthTrigger.SYSTEM2
)
```

---

## 监控与调试

### 结构可视化

```python
# 树状视图
print(agent.visualize_structure(format="tree"))
```

### 性能指标

```python
metrics = agent.metrics.to_dict()
print(f"任务数: {metrics['task_count']}")
print(f"成功率: {metrics['success_rate']}")
print(f"适应度: {metrics['fitness_score']}")
```

---

## 最佳实践

1.  **选择正确的触发器**：推荐使用 `SYSTEM2`，让系统根据复杂度自动适应。
2.  **设置合理的限制**：生产环境建议 `max_depth=2` 或 `3`，避免过度递归。
3.  **监控适应度**：如果 `fitness_score` 较低，考虑调整提示词或结构。
4.  **从简单开始**：先从手动流水线开始，逐步引入自动增长。
