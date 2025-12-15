# Agents API

**版本**: v0.1.6

Agents API 参考文档。

---

## 📋 目录

1. [SimpleAgent](#simpleagent)
2. [BaseAgent](#baseagent)
3. [工具函数](#工具函数)

---

## SimpleAgent

### 概述

`SimpleAgent` 是 Loom 的核心 Agent 实现，基于递归状态机架构。

```python
import loom
from loom.builtin import OpenAILLM

agent = loom.agent(
    name="assistant",
    llm=OpenAILLM(api_key="...")
)
```

### 构造函数

```python
loom.agent(
    name: str,
    llm: BaseLLM,
    tools: Optional[List[BaseTool]] = None,
    system_prompt: Optional[str] = None,
    context_manager: Optional[ContextManager] = None,
    max_recursion_depth: int = 20,
    enable_skills: bool = True,
    skills_dir: Optional[str] = "./skills",
    event_handler: Optional[Callable] = None
)
```

#### 参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `name` | `str` | 必需 | Agent 名称，唯一标识 |
| `llm` | `BaseLLM` | 必需 | LLM 实例 |
| `tools` | `List[BaseTool]` | `None` | 工具列表 |
| `system_prompt` | `str` | `None` | 系统提示（自动生成如果未提供） |
| `context_manager` | `ContextManager` | `None` | 上下文管理器 |
| `max_recursion_depth` | `int` | `20` | 最大递归深度 |
| `enable_skills` | `bool` | `True` | 启用 Skills 系统 |
| `skills_dir` | `str` | `"./skills"` | Skills 目录路径 |
| `event_handler` | `Callable` | `None` | 事件处理函数 |

#### 返回值

`SimpleAgent` 实例

#### 示例

```python
import loom, Message
from loom.builtin import OpenAILLM, tool

@tool(name="calculator")
async def calculator(expression: str) -> float:
    """计算数学表达式"""
    return eval(expression)

agent = loom.agent(
    name="math-assistant",
    llm=OpenAILLM(api_key="..."),
    tools=[calculator],
    system_prompt="你是一个数学助手",
    max_recursion_depth=10,
    enable_skills=True
)
```

---

### 核心方法

#### `run()`

执行 Agent 任务（主要方法）。

```python
async def run(self, message: Message) -> Message
```

**参数**：
- `message` (`Message`): 输入消息

**返回值**：
- `Message`: 输出消息

**示例**：
```python
msg = Message(role="user", content="计算 123 * 456")
response = await agent.run(msg)
print(response.content)  # "56088"
```

---

#### `reply()`

回复消息（`run()` 的别名）。

```python
async def reply(self, message: Message) -> Message
```

**参数**：
- `message` (`Message`): 输入消息

**返回值**：
- `Message`: 输出消息

**示例**：
```python
response = await agent.reply(msg)
```

---

#### `reset()`

重置 Agent 状态。

```python
def reset(self) -> None
```

**用途**：
- 清除对话历史
- 重置统计信息
- 开始新的对话会话

**示例**：
```python
agent.reset()  # 清除历史，开始新对话
```

---

#### `get_stats()`

获取 Agent 统计信息。

```python
def get_stats(self) -> dict
```

**返回值**：
```python
{
    "name": str,              # Agent 名称
    "num_tools": int,         # 工具数量
    "executor_stats": {       # 执行器统计
        "total_llm_calls": int,
        "total_tool_calls": int,
        "total_tokens_input": int,
        "total_tokens_output": int,
        "total_cost": float
    },
    "skills": {               # Skills 统计（如果启用）
        "total_skills": int,
        "enabled_skills": int,
        "disabled_skills": int,
        "categories": int
    }
}
```

**示例**：
```python
stats = agent.get_stats()
print(f"LLM 调用次数: {stats['executor_stats']['total_llm_calls']}")
print(f"Token 总数: {stats['executor_stats']['total_tokens_input']}")
```

---

### Skills 管理方法

#### `list_skills()`

列出可用的 Skills。

```python
def list_skills(self, category: Optional[str] = None) -> List[Skill]
```

**参数**：
- `category` (`str`, 可选): 筛选分类

**返回值**：
- `List[Skill]`: Skills 列表

**示例**：
```python
# 列出所有 Skills
skills = agent.list_skills()
for skill in skills:
    print(f"{skill.metadata.name}: {skill.metadata.description}")

# 按分类筛选
analysis_skills = agent.list_skills(category="analysis")
```

---

#### `get_skill()`

获取特定 Skill。

```python
def get_skill(self, name: str) -> Optional[Skill]
```

**参数**：
- `name` (`str`): Skill 名称

**返回值**：
- `Skill` 或 `None`: Skill 实例

**示例**：
```python
skill = agent.get_skill("pdf_analyzer")
if skill:
    print(f"Found: {skill.metadata.name}")
```

---

#### `enable_skill()`

启用 Skill。

```python
def enable_skill(self, name: str) -> bool
```

**参数**：
- `name` (`str`): Skill 名称

**返回值**：
- `bool`: 是否成功

**示例**：
```python
if agent.enable_skill("web_research"):
    print("Skill enabled")
```

---

#### `disable_skill()`

禁用 Skill。

```python
def disable_skill(self, name: str) -> bool
```

**参数**：
- `name` (`str`): Skill 名称

**返回值**：
- `bool`: 是否成功

**示例**：
```python
agent.disable_skill("web_research")
```

---

#### `reload_skills()`

重新加载所有 Skills。

```python
def reload_skills(self) -> None
```

**用途**：从磁盘重新加载 Skills（文件变更后）

**示例**：
```python
agent.reload_skills()  # 重新扫描 skills/ 目录
```

---

#### `create_skill()`

创建新 Skill。

```python
def create_skill(
    self,
    name: str,
    description: str,
    category: str = "general",
    quick_guide: Optional[str] = None,
    detailed_content: Optional[str] = None,
    **kwargs
) -> Skill
```

**参数**：
- `name` (`str`): Skill 名称
- `description` (`str`): 描述
- `category` (`str`): 分类
- `quick_guide` (`str`, 可选): 快速指南
- `detailed_content` (`str`, 可选): 详细文档
- `**kwargs`: 其他元数据（version, author, tags, etc.）

**返回值**：
- `Skill`: 创建的 Skill 实例

**示例**：
```python
skill = agent.create_skill(
    name="my_skill",
    description="Custom skill",
    category="tools",
    quick_guide="Usage hint",
    tags=["custom", "example"]
)
```

---

### 属性

#### `name`

```python
agent.name: str
```

Agent 名称。

---

#### `llm`

```python
agent.llm: BaseLLM
```

LLM 实例。

---

#### `tools`

```python
agent.tools: List[BaseTool]
```

工具列表。

---

#### `system_prompt`

```python
agent.system_prompt: str
```

系统提示。

---

#### `enable_skills`

```python
agent.enable_skills: bool
```

是否启用 Skills。

---

#### `skill_manager`

```python
agent.skill_manager: Optional[SkillManager]
```

Skills 管理器实例。

---

## BaseAgent

### 概述

`BaseAgent` 是 Agent 的协议定义（Protocol）。

```python
from loom.core import BaseAgent
```

### 协议定义

```python
class BaseAgent(Protocol):
    """Agent 协议"""

    name: str
    llm: BaseLLM
    tools: List[BaseTool]

    async def run(self, message: Message) -> Message:
        """核心方法：执行 Agent 任务"""
        ...
```

### 自定义 Agent

实现 `BaseAgent` 协议创建自定义 Agent：

```python
from loom.core import BaseAgent, Message
from loom.builtin import OpenAILLM

class MyCustomAgent:
    """自定义 Agent"""

    def __init__(self, name: str, llm: BaseLLM):
        self.name = name
        self.llm = llm
        self.tools = []

    async def run(self, message: Message) -> Message:
        """实现核心逻辑"""
        # 自定义实现
        response = await self.llm.generate(
            messages=[message],
            tools=self.tools
        )
        return Message(
            role="assistant",
            content=response["content"]
        )

# 使用
agent = MyCustomAgent(
    name="custom",
    llm=OpenAILLM(api_key="...")
)
```

---

## 工具函数

### `create_agent()`

工厂函数，创建 Agent 实例。

```python
from loom import create_agent

def create_agent(
    agent_type: str = "simple",
    **kwargs
) -> BaseAgent
```

**参数**：
- `agent_type` (`str`): Agent 类型（"simple"）
- `**kwargs`: Agent 构造参数

**返回值**：
- `BaseAgent`: Agent 实例

**示例**：
```python
agent = create_agent(
    agent_type="simple",
    name="assistant",
    llm=OpenAILLM(api_key="...")
)
```

---

## 完整示例

### 基础使用

```python
import asyncio
import loom, Message
from loom.builtin import OpenAILLM

async def main():
    agent = loom.agent(
        name="assistant",
        llm=OpenAILLM(api_key="...")
    )

    msg = Message(role="user", content="Hello!")
    response = await agent.run(msg)
    print(response.content)

asyncio.run(main())
```

### 带工具的 Agent

```python
from loom.builtin import tool

@tool(name="get_weather")
async def get_weather(city: str) -> str:
    """获取天气"""
    return f"{city} 的天气是晴天"

agent = loom.agent(
    name="weather-assistant",
    llm=OpenAILLM(api_key="..."),
    tools=[get_weather]
)

msg = Message(role="user", content="北京天气如何？")
response = await agent.run(msg)
```

### 带 Skills 的 Agent

```python
agent = loom.agent(
    name="analyst",
    llm=OpenAILLM(api_key="..."),
    enable_skills=True,
    skills_dir="./skills"
)

# Skills 自动加载
skills = agent.list_skills()
print(f"Available skills: {[s.metadata.name for s in skills]}")

# 使用 Skill
msg = Message(role="user", content="分析这个 PDF: report.pdf")
response = await agent.run(msg)
```

### 事件监控

```python
from loom.core.events import AgentEventType

def event_handler(event):
    if event.type == AgentEventType.LLM_START:
        print("🤖 LLM 调用开始")
    elif event.type == AgentEventType.TOOL_START:
        print(f"🔧 工具调用: {event.data['tool_name']}")

agent = loom.agent(
    name="monitored-agent",
    llm=OpenAILLM(api_key="..."),
    event_handler=event_handler
)

msg = Message(role="user", content="...")
response = await agent.run(msg)

# 查看统计
stats = agent.get_stats()
print(f"LLM 调用: {stats['executor_stats']['total_llm_calls']}")
```

---

## 相关文档

- [SimpleAgent 指南](../guides/agents/simple-agent.md) - 完整使用指南
- [创建第一个 Agent](../getting-started/first-agent.md) - 快速入门
- [Core API](./core.md) - 核心组件 API
- [Tools API](./tools.md) - 工具 API

---

**返回**: [API 参考](./README.md) | [文档首页](../README.md)
