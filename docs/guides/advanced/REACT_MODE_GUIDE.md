# ReAct 模式使用指南

## 概述

Loom Agent 通过 `react_mode` 开关支持 ReAct (Reasoning + Acting) 推理模式，无需单独的 ReActAgent 类。

### 设计理念

- **统一 API**：只有 `loom.agent()` 一个入口
- **开关控制**：通过 `react_mode=True` 启用 ReAct 模式
- **灵活编排**：Crew 可以混合使用不同模式的 Agent

---

## 快速开始

### 标准模式（默认）

```python
import loom

# 标准模式：直接响应
agent = loom.agent(
    name="assistant",
    llm="openai",
    api_key="sk-..."
)
```

### ReAct 模式

```python
import loom
from loom import tool

# 定义工具
@tool(name="search")
async def search(query: str) -> str:
    return f"Search results for: {query}"

@tool(name="calculator")
async def calculator(expression: str) -> float:
    return eval(expression)

# 启用 ReAct 模式
agent = loom.agent(
    name="researcher",
    llm="openai",
    api_key="sk-...",
    tools=[search, calculator],
    react_mode=True  # 启用推理-行动循环
)

# 使用
from loom import Message
msg = Message(role="user", content="What's the GDP of China in 2023?")
response = await agent.run(msg)
print(response.content)
```

---

## ReAct 模式特性

### 1. 推理-行动循环

ReAct 模式下，Agent 会：
1. **Thought**（思考）：分析任务，决定下一步行动
2. **Action**（行动）：使用工具获取信息
3. **Observation**（观察）：审查结果
4. **Repeat**（重复）：继续循环直到得出最终答案

### 2. 系统提示

ReAct 模式使用专门的系统提示，引导 Agent：
- 将复杂任务分解为小步骤
- 战略性使用工具
- 反思结果并调整策略
- 追踪学习到的信息

### 3. 适用场景

**适合 ReAct 模式**：
- ✅ 需要多步推理的任务
- ✅ 需要使用多个工具的场景
- ✅ 需要验证和交叉检查信息
- ✅ 研究、分析类任务

**适合标准模式**：
- ✅ 简单对话
- ✅ 单步任务
- ✅ 直接响应
- ✅ 创意写作

---

## 使用示例

### 示例 1：研究 Agent

```python
import loom
from loom import tool

@tool(name="web_search")
async def web_search(query: str) -> str:
    # 调用搜索 API
    return search_api(query)

@tool(name="fetch_url")
async def fetch_url(url: str) -> str:
    # 获取网页内容
    return fetch(url)

# ReAct 模式：适合需要多步研究的任务
researcher = loom.agent(
    name="researcher",
    llm="openai",
    api_key="sk-...",
    tools=[web_search, fetch_url],
    react_mode=True
)

# 使用
result = await researcher.run(
    Message(role="user", content="Research the latest AI trends in 2025")
)
```

### 示例 2：数据分析 Agent

```python
import loom
from loom import tool

@tool(name="load_data")
async def load_data(path: str) -> dict:
    # 加载数据
    return {...}

@tool(name="analyze")
async def analyze(data: dict, method: str) -> dict:
    # 分析数据
    return {...}

@tool(name="visualize")
async def visualize(data: dict, chart_type: str) -> str:
    # 生成图表
    return "chart.png"

# ReAct 模式：适合需要多步数据处理的任务
analyst = loom.agent(
    name="analyst",
    llm="deepseek",
    api_key="sk-...",
    tools=[load_data, analyze, visualize],
    react_mode=True
)

# 使用
result = await analyst.run(
    Message(role="user", content="Analyze sales data and create a report")
)
```

### 示例 3：Crew 中混合使用

```python
import loom
from loom.patterns import Crew

# 研究员：ReAct 模式（需要多步推理）
researcher = loom.agent(
    name="researcher",
    llm="openai",
    api_key="sk-...",
    tools=[search_tool],
    react_mode=True  # 启用 ReAct
)

# 撰写员：标准模式（直接写作）
writer = loom.agent(
    name="writer",
    llm="deepseek",
    api_key="sk-...",
    react_mode=False  # 标准模式（默认）
)

# 审阅员：标准模式
reviewer = loom.agent(
    name="reviewer",
    llm="qwen",
    api_key="sk-...",
    react_mode=False
)

# 创建 Crew
crew = Crew(
    agents=[researcher, writer, reviewer],
    mode="sequential"
)

# 执行
result = await crew.run(
    Message(role="user", content="Write an article about quantum computing")
)
```

---

## CrewRole 自动启用

在 `CrewRole` 中，如果角色配置了工具，会**自动启用 ReAct 模式**：

```python
from loom.patterns import CrewRole, Crew

# 定义角色（有工具时自动启用 ReAct）
researcher_role = CrewRole(
    name="researcher",
    goal="Research and gather information",
    tools=[search_tool, read_tool]  # 有工具 → 自动启用 ReAct
)

writer_role = CrewRole(
    name="writer",
    goal="Write content",
    tools=[]  # 无工具 → 使用标准模式
)

# 创建 Crew
crew = Crew(
    roles=[researcher_role, writer_role],
    mode="sequential",
    llm="openai",
    api_key="sk-..."
)
```

---

## 工厂函数支持

`loom.agent()` 工厂函数完全支持 `react_mode`：

```python
import loom

# 方式 1：显式指定
agent = loom.agent(
    name="assistant",
    llm="openai",
    api_key="sk-...",
    tools=[...],
    react_mode=True
)

# 方式 2：通过字典配置
agent = loom.agent(
    name="assistant",
    llm={
        "provider": "openai",
        "api_key": "sk-...",
        "model": "gpt-4"
    },
    tools=[...],
    react_mode=True
)

# 方式 3：create_agent 工厂函数
from loom.core import create_agent
from loom.builtin import UnifiedLLM

llm = UnifiedLLM(api_key="sk-...", provider="openai")
agent = create_agent(
    name="assistant",
    llm=llm,
    tools=[...],
    agent_type="react"  # 使用 "react" 类型自动启用 react_mode
)
```

---

## 对比：标准模式 vs ReAct 模式

| 特性 | 标准模式 | ReAct 模式 |
|------|---------|-----------|
| **系统提示** | 工具使用指南 | ReAct 推理框架 |
| **推理方式** | 直接响应 | 思考-行动循环 |
| **适用场景** | 简单任务、对话 | 复杂推理、研究 |
| **工具使用** | 正常使用 | 战略性使用 |
| **性能** | 快速 | 略慢（多步推理） |
| **输出质量** | 标准 | 更深思熟虑 |

---

## 最佳实践

### 1. 何时使用 ReAct 模式

**推荐使用**：
```python
# ✅ 多步推理任务
agent = loom.agent(..., tools=[search, calculate, verify], react_mode=True)

# ✅ 需要验证的场景
agent = loom.agent(..., tools=[check_facts, cross_reference], react_mode=True)

# ✅ 研究和分析
agent = loom.agent(..., tools=[gather, analyze, synthesize], react_mode=True)
```

**不推荐使用**：
```python
# ❌ 简单对话（不需要 ReAct 开销）
agent = loom.agent(..., react_mode=False)  # 或省略

# ❌ 创意写作（ReAct 可能限制创造力）
agent = loom.agent(..., react_mode=False)

# ❌ 无工具场景（ReAct 主要用于工具使用）
agent = loom.agent(..., tools=[], react_mode=False)
```

### 2. 与 Crew 配合

```python
# 混合使用不同模式
crew = Crew(
    agents=[
        loom.agent(..., react_mode=True),   # 研究
        loom.agent(..., react_mode=False),  # 写作
        loom.agent(..., react_mode=False),  # 审阅
    ],
    mode="sequential"
)
```

### 3. 自定义系统提示

如果需要自定义系统提示，`react_mode` 仍然有效：

```python
agent = loom.agent(
    name="assistant",
    llm="openai",
    api_key="sk-...",
    tools=[...],
    react_mode=True,
    system_prompt="Custom prompt that incorporates ReAct principles..."
)
```

**注意**：提供 `system_prompt` 会覆盖自动生成的 ReAct 提示。

---

## 迁移指南

### 从 ReActAgent（如果存在）迁移

**旧代码（假设）**：
```python
from loom.agents import ReActAgent

agent = ReActAgent(
    name="researcher",
    llm=llm,
    tools=[search, calculator]
)
```

**新代码**：
```python
import loom

agent = loom.agent(
    name="researcher",
    llm="openai",
    api_key="sk-...",
    tools=[search, calculator],
    react_mode=True  # 使用开关启用
)
```

### 优势

1. **API 简洁**：只有 `loom.agent()` 一个入口
2. **灵活切换**：通过参数轻松切换模式
3. **代码统一**：所有 Agent 使用相同的类
4. **易于维护**：不需要维护多个 Agent 类

---

## 技术实现

### Agent 类支持

```python
class Agent:
    def __init__(
        self,
        name: str,
        llm: Union[str, Dict, BaseLLM],
        ...
        react_mode: bool = False,  # ReAct 模式开关
        **llm_kwargs
    ):
        self.react_mode = react_mode
        ...

    def _generate_default_system_prompt(self) -> str:
        if self.react_mode:
            return self._generate_react_system_prompt()
        else:
            return self._generate_standard_system_prompt()
```

### create_agent 工厂函数

```python
from loom.core import create_agent

# agent_type="react" 自动设置 react_mode=True
agent = create_agent(
    name="assistant",
    llm=llm,
    tools=[...],
    agent_type="react"
)
```

---

## 总结

✅ **统一 API**：只有 `loom.agent()` 一个入口
✅ **开关控制**：`react_mode=True` 启用 ReAct
✅ **灵活编排**：Crew 支持混合模式
✅ **自动启用**：CrewRole 有工具时自动启用
✅ **易于切换**：通过参数控制行为

---

**版本**: v0.1.9 
**日期**: 2025-12-15
