# 教程 1：创建你的第一个 Agent

> **学习目标**：理解 Agent 的基本概念，创建并运行一个简单的 Agent

## 什么是 Agent？

Agent 是 loom-agent 中的基本计算单元，它可以：
- 接收任务
- 使用工具
- 返回结果

## 创建最简单的 Agent

```python
from loom.weave import create_agent, run

# 创建 Agent
agent = create_agent(
    name="助手",           # Agent 的名称
    role="通用助手"        # Agent 的角色描述
)

# 运行任务
result = run(agent, "你好，请介绍一下自己")
print(result)
```

## 理解代码

1. **导入模块**：`loom.weave` 提供了简化的 API
2. **create_agent()**：创建一个 Agent 实例
3. **run()**：同步运行 Agent（自动处理异步）

## 下一步

→ [教程 2：添加技能](02-adding-skills.md)
