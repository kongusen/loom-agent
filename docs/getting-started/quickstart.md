# 快速开始

> 5 分钟创建你的第一个 Agent

## 第一步：安装

```bash
pip install loom-agent
```

## 第二步：创建你的第一个 Agent

创建一个新文件 `my_agent.py`：

```python
from loom.weave import create_agent, run

# 创建 Agent
agent = create_agent("助手", role="通用助手")

# 运行任务
result = run(agent, "你好，请介绍一下自己")
print(result)
```

运行：

```bash
python my_agent.py
```

## 第三步：添加技能

让 Agent 具备计算能力：

```python
from loom.weave import create_agent, run
from loom.stdlib.skills import CalculatorSkill

# 创建 Agent
agent = create_agent("计算助手", role="数学助手")

# 添加计算技能
calc_skill = CalculatorSkill()
calc_skill.register(agent)

# 运行任务
result = run(agent, "计算 123 * 456")
print(result)
```

## 第四步：使用预构建 Agent

更简单的方式：

```python
from loom.stdlib.agents import AnalystAgent
from loom.weave import run

# 使用预构建的分析师 Agent
analyst = AnalystAgent("my-analyst")

# 运行任务
result = run(analyst, "计算 2024 * 365")
print(result)
```

## 下一步

🎉 恭喜！你已经创建了第一个 Agent。

**继续学习：**
- 📖 [教程：创建你的第一个 Agent](../tutorials/01-your-first-agent.md)
- 🛠️ [操作指南：创建 Agent](../guides/agents/)
- 💡 [概念：架构设计](../concepts/architecture.md)
