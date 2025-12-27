# 教程 2：为 Agent 添加技能

> **学习目标**：理解 Skill 的概念，学会为 Agent 添加预构建和自定义技能

## 什么是 Skill？

Skill（技能）是 loom-agent 中的能力封装单元，它包含：

- **Tool（工具）**：Agent 可以调用的函数
- **Prompt（提示词）**：指导 Agent 如何使用工具
- **Memory Config（记忆配置）**：可选的记忆管理配置

## 使用预构建 Skill

loom-agent 提供了一些开箱即用的技能：

### 示例：添加计算能力

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

### 理解代码

1. **导入 Skill**：从 `loom.stdlib.skills` 导入预构建技能
2. **创建 Skill 实例**：`CalculatorSkill()`
3. **注册到 Agent**：`calc_skill.register(agent)` 将技能添加到 Agent

## 可用的预构建 Skills

| Skill | 功能 | 导入路径 |
|-------|------|----------|
| `CalculatorSkill` | 数学计算 | `loom.stdlib.skills` |
| `FileSystemSkill` | 文件读写 | `loom.stdlib.skills` |

## 创建自定义 Skill

你可以创建自己的技能来扩展 Agent 的能力。

### 步骤 1：继承 Skill 基类

```python
from loom.stdlib.skills.base import Skill
from loom.weave import create_tool
from loom.node.tool import ToolNode
from typing import List

class WeatherSkill(Skill):
    """天气查询技能"""

    def __init__(self):
        super().__init__(
            name="weather",
            description="查询天气信息"
        )
```

### 步骤 2：实现 get_tools() 方法

```python
    def get_tools(self) -> List[ToolNode]:
        """返回天气查询工具"""

        def get_weather(city: str) -> str:
            """
            查询城市天气。

            Args:
                city: 城市名称

            Returns:
                天气信息
            """
            # 这里是模拟实现，实际应该调用天气 API
            return f"{city}的天气：晴天，温度 25°C"

        return [create_tool("get_weather", get_weather, "查询城市天气")]

    def get_system_prompt(self) -> str:
        """返回系统提示词（可选）"""
        return "你可以使用 get_weather 工具查询城市天气信息。"
```

### 步骤 3：使用自定义 Skill

```python
from loom.weave import create_agent, run

# 创建 Agent
agent = create_agent("天气助手", role="天气查询助手")

# 添加自定义技能
weather_skill = WeatherSkill()
weather_skill.register(agent)

# 运行任务
result = run(agent, "北京的天气怎么样？")
print(result)
```

## 组合多个 Skills

一个 Agent 可以拥有多个技能：

```python
from loom.weave import create_agent, run
from loom.stdlib.skills import CalculatorSkill

# 创建 Agent
agent = create_agent("多功能助手", role="通用助手")

# 添加多个技能
calc_skill = CalculatorSkill()
calc_skill.register(agent)

weather_skill = WeatherSkill()
weather_skill.register(agent)

# Agent 现在可以同时处理计算和天气查询
result = run(agent, "计算 100 + 200，然后告诉我上海的天气")
print(result)
```

## 下一步

→ [教程 3：构建 Agent 团队](03-building-teams.md)
