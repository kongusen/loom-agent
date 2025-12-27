# 创建 Agent

> **问题导向** - 学会使用不同方式创建和配置 Agent

## 概述

loom-agent 提供了多种创建 Agent 的方式：
- **简化 API**：使用 `loom.weave` 快速创建
- **底层 API**：使用 `AgentNode` 进行精细控制
- **预构建 Agent**：使用 `loom.stdlib` 中的现成 Agent

## 方式 1：使用 loom.weave（推荐）

最简单的创建方式，适合快速开发：

```python
from loom.weave import create_agent, run

# 创建最简单的 Agent
agent = create_agent("my-agent", role="通用助手")

# 运行任务
result = run(agent, "你好，请介绍一下自己")
print(result)
```

**特点**：
- 3 行代码即可创建
- 自动管理 LoomApp
- 适合快速原型开发

### 添加工具和技能

```python
from loom.weave import create_agent, create_tool, run
from loom.stdlib.skills import CalculatorSkill

# 创建带工具的 Agent
def search(query: str) -> str:
    """搜索工具"""
    return f"搜索结果: {query}"

tool = create_tool("search", search)
agent = create_agent("assistant", role="助手", tools=[tool])

# 或添加技能
agent = create_agent("analyst", role="分析师")
calc_skill = CalculatorSkill()
calc_skill.register(agent)
```

## 方式 2：使用底层 API

使用 `AgentNode` 进行精细控制：

```python
from loom.node.agent import AgentNode, ThinkingPolicy
from loom.api.main import LoomApp
from loom.infra.llm import MockLLMProvider

# 创建 LoomApp
app = LoomApp()

# 创建 Agent（完全控制）
agent = AgentNode(
    node_id="my-agent",
    dispatcher=app.dispatcher,
    role="高级助手",
    system_prompt="你是一个专业的AI助手",
    provider=MockLLMProvider(),
    thinking_policy=ThinkingPolicy(enabled=True)
)

# 运行任务
result = await app.run(agent, "分析这个问题")
```

**特点**：
- 完全控制所有参数
- 支持高级配置
- 适合生产环境

## 方式 3：使用预构建 Agent

使用 `loom.stdlib` 中的现成 Agent：

```python
from loom.stdlib.agents import CoderAgent, AnalystAgent
from loom.weave import run

# 使用预构建的编码 Agent
coder = CoderAgent("my-coder", base_dir="./src")
result = run(coder, "创建一个 hello.py 文件")

# 使用预构建的分析 Agent
analyst = AnalystAgent("my-analyst")
result = run(analyst, "计算 123 * 456")
```

**可用的预构建 Agent**：
- `CoderAgent`：具有文件操作能力
- `AnalystAgent`：具有计算能力

**特点**：
- 开箱即用
- 预配置了常用技能
- 适合快速开发

## 相关文档

- [配置 Agent](configuring-agents.md) - Agent 配置选项详解
- [配置 LLM](../configuration/llm-providers.md) - 配置 LLM 提供商
- [创建自定义技能](../skills/creating-custom-skills.md) - 为 Agent 添加能力
