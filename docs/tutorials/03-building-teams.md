# 教程 3：构建 Agent 团队

> **学习目标**：理解 Crew 的概念，学会创建和使用 Agent 团队

## 什么是 Crew？

Crew（团队）是多个 Agent 的协作单元，它可以：

- **组织多个 Agent**：将多个 Agent 组合成一个团队
- **定义协作模式**：控制 Agent 之间的交互方式
- **复杂任务分解**：将复杂任务分配给不同的 Agent

## 创建简单的 Crew

### 示例：顺序执行团队

```python
from loom.weave import create_agent, create_crew, run

# 创建两个 Agent
writer = create_agent("writer", role="内容创作者 - 负责撰写文章")
reviewer = create_agent("reviewer", role="审稿人 - 负责审核和改进文章")

# 创建团队
team = create_crew("writing-team", [writer, reviewer])

# 运行任务
result = run(team, "写一篇关于 AI 的短文")
print(result)
```

### 理解代码

1. **创建 Agent**：分别创建 writer 和 reviewer 两个 Agent
2. **create_crew()**：将 Agent 列表组合成团队
3. **顺序执行**：writer 的输出会作为 reviewer 的输入

### 执行流程

```
任务 → Writer Agent → 文章初稿 → Reviewer Agent → 改进后的文章
```

## 协作模式

Crew 支持不同的协作模式：

### Sequential（顺序模式）

Agent 按顺序执行，每个 Agent 的输出作为下一个 Agent 的输入。

```python
# 默认就是 sequential 模式
team = create_crew("team", [agent1, agent2, agent3], pattern="sequential")
```

**适用场景**：
- 写作 → 审核 → 发布
- 研究 → 分析 → 报告
- 设计 → 开发 → 测试

## 使用预构建 Crew

loom-agent 提供了一些预构建的团队模式：

### 示例：辩论团队

```python
from loom.weave import run
from loom.stdlib.crews import DebateCrew

# 创建辩论团队
debate_team = DebateCrew("debate", topic="AI 是否会取代人类工作")

# 运行辩论
result = run(debate_team, "开始辩论，每方提出 3 个论点")
print(result)
```

**工作原理**：
- 自动创建正方和反方两个 Agent
- 正方先发言，反方回应
- 适合探索问题的多个角度

## 组合 Agent 和 Skills

团队中的 Agent 可以拥有不同的技能：

```python
from loom.weave import create_agent, create_crew, run
from loom.stdlib.skills import CalculatorSkill, FileSystemSkill

# 创建具有不同技能的 Agent
analyst = create_agent("analyst", role="数据分析师")
calc_skill = CalculatorSkill()
calc_skill.register(analyst)

writer = create_agent("writer", role="报告撰写者")
fs_skill = FileSystemSkill(base_dir="./reports")
fs_skill.register(writer)

# 创建团队
team = create_crew("analysis-team", [analyst, writer])

# 运行任务
result = run(team, "分析数据 [100, 200, 300] 的平均值，并写入报告")
print(result)
```

## 下一步

→ [教程 4：使用 YAML 配置](04-yaml-configuration.md)
