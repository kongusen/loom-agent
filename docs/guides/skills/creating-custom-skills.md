# 创建自定义技能

> **问题导向** - 学会创建和使用自定义 Skill

## 什么是 Skill？

Skill（技能）= Tool（工具）+ Prompt（提示词）+ Memory Config（记忆配置）

**核心组件**：
- **Tool**：Agent 可以调用的函数
- **Prompt**：指导 Agent 如何使用工具
- **Memory Config**：可选的记忆管理配置

## 创建步骤

### 步骤 1：继承 Skill 基类

```python
from loom.stdlib.skills.base import Skill
from loom.node.tool import ToolNode
from loom.weave import create_tool
from typing import List

class WeatherSkill(Skill):
    """天气查询技能"""

    def __init__(self, api_key: str = None):
        super().__init__(
            name="weather",
            description="查询天气信息"
        )
        self.api_key = api_key

    def get_tools(self) -> List[ToolNode]:
        """实现工具列表"""
        def get_weather(city: str) -> str:
            """查询城市天气"""
            # 实际应该调用天气 API
            return f"{city}的天气：晴天，25°C"

        return [create_tool("get_weather", get_weather, "查询城市天气")]

    def get_system_prompt(self) -> str:
        """可选：返回系统提示词"""
        return "你可以使用 get_weather 工具查询天气。"
```

### 步骤 2：注册到 Agent

```python
from loom.weave import create_agent, run

# 创建 Agent
agent = create_agent("assistant", role="天气助手")

# 注册技能
weather_skill = WeatherSkill(api_key="your-key")
weather_skill.register(agent)

# 使用
result = run(agent, "北京的天气怎么样？")
```

## 相关文档

- [添加技能](../../tutorials/02-adding-skills.md) - 教程：为 Agent 添加技能
- [创建 Agent](../agents/creating-agents.md) - 如何创建 Agent
