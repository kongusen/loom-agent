# SimpleAgent 完整指南

**版本**: v0.1.6
**最后更新**: 2025-12-14

SimpleAgent 是 Loom 中最常用的 Agent 实现，基于递归状态机架构，提供简洁而强大的 Agent 能力。

---

## 目录

1. [概述](#概述)
2. [快速开始](#快速开始)
3. [初始化参数](#初始化参数)
4. [核心方法](#核心方法)
5. [工具集成](#工具集成)
6. [Skills 系统](#skills-系统)
7. [系统提示](#系统提示)
8. [事件处理](#事件处理)
9. [统计和监控](#统计和监控)
10. [高级用法](#高级用法)
11. [最佳实践](#最佳实践)
12. [常见问题](#常见问题)

---

## 概述

### 什么是 SimpleAgent？

SimpleAgent 是基于**递归状态机 (Recursive State Machine)** 的基础 Agent 实现，核心思想是：

```
Agent = recursive function
```

**执行流程**：
```
用户输入 → LLM 推理 → 工具调用 → 递归调用 run() → 最终结果
```

### 核心特性

- ✅ **纯递归调用**: 自动处理多轮工具调用
- ✅ **自动工具调用**: 智能选择和执行工具
- ✅ **Context 自动管理**: 对话历史自动维护
- ✅ **Skills 系统**: 模块化能力扩展（v0.1.6）
- ✅ **事件追踪**: 完整的执行生命周期事件
- ✅ **工具并行执行**: 多工具并发调用（v0.1.6）

### 适用场景

- 单一职责的 Agent
- 简单的对话应用
- 作为 Crew 的成员
- 快速原型开发
- 工具调用密集型任务

---

## 快速开始

### 最简示例

```python
import asyncio
from loom import Message, SimpleAgent
from loom.builtin import OpenAILLM

async def main():
    # 创建 Agent
    agent = loom.agent(
        name="assistant",
        llm=OpenAILLM(api_key="your-api-key")
    )

    # 发送消息
    message = Message(role="user", content="介绍一下你自己")
    response = await agent.run(message)

    print(response.content)

asyncio.run(main())
```

### 带工具的示例

```python
import asyncio
from loom import Message, SimpleAgent
from loom.builtin import OpenAILLM, tool

# 定义工具
@tool(name="calculator")
async def calculator(expression: str) -> float:
    """计算数学表达式"""
    return eval(expression)

async def main():
    agent = loom.agent(
        name="math-agent",
        llm=OpenAILLM(api_key="your-api-key"),
        tools=[calculator]
    )

    message = Message(role="user", content="计算 123 * 456")
    response = await agent.run(message)
    print(response.content)  # 输出: 56088

asyncio.run(main())
```

---

## 初始化参数

### 构造函数签名

```python
loom.agent(
    name: str,
    llm: BaseLLM,
    tools: Optional[List[BaseTool]] = None,
    system_prompt: Optional[str] = None,
    context_manager: Optional[ContextManager] = None,
    max_recursion_depth: int = 20,
    skills_dir: Optional[str] = None,
    enable_skills: bool = True,
)
```

### 参数详解

#### `name` (必需)

Agent 的名称，用于日志、追踪和识别。

```python
agent = loom.agent(
    name="customer-service",  # 清晰的名称
    llm=llm
)
```

#### `llm` (必需)

语言模型实例，必须实现 `BaseLLM` 接口。

```python
from loom.builtin import OpenAILLM

# OpenAI
llm = OpenAILLM(
    api_key="sk-...",
    model="gpt-4",
    temperature=0.7
)

agent = loom.agent(name="assistant", llm=llm)
```

#### `tools` (可选)

Agent 可以调用的工具列表。

```python
from loom.builtin import tool

@tool(name="search")
async def search(query: str) -> str:
    """搜索信息"""
    return f"搜索结果: {query}"

agent = loom.agent(
    name="agent",
    llm=llm,
    tools=[search]  # 传递工具列表
)
```

#### `system_prompt` (可选)

自定义系统提示。如果不提供，会自动生成包含工具使用指南和 Skills 索引的默认提示。

```python
system_prompt = """
你是一个专业的 Python 编程助手。

职责：
- 回答 Python 编程问题
- 提供代码示例
- 遵循 PEP 8 规范

回答风格：
- 简洁明了
- 代码优先
- 包含注释
"""

agent = loom.agent(
    name="python-tutor",
    llm=llm,
    system_prompt=system_prompt
)
```

#### `context_manager` (可选)

自定义 Context 管理器。默认使用内置的 `ContextManager`。

```python
from loom.core import ContextManager

# 自定义配置
context_mgr = ContextManager(
    max_context_tokens=8000,  # 限制上下文大小
    # 其他配置...
)

agent = loom.agent(
    name="agent",
    llm=llm,
    context_manager=context_mgr
)
```

#### `max_recursion_depth` (可选)

最大递归深度，防止无限循环。默认 20。

```python
agent = loom.agent(
    name="agent",
    llm=llm,
    max_recursion_depth=30  # 允许更多工具调用轮次
)
```

#### `skills_dir` (可选)

Skills 目录路径。默认 `"./skills"`。

```python
agent = loom.agent(
    name="agent",
    llm=llm,
    enable_skills=True,
    skills_dir="/path/to/skills"  # 自定义路径
)
```

#### `enable_skills` (可选)

是否启用 Skills 系统。默认 `True`。

```python
# 禁用 Skills
agent = loom.agent(
    name="agent",
    llm=llm,
    enable_skills=False
)
```

---

## 核心方法

### `run(message: Message) -> Message`

核心递归方法，执行 Agent 任务。

```python
message = Message(role="user", content="你好")
response = await agent.run(message)
print(response.content)
```

**特点**：
- 异步方法
- 自动处理多轮工具调用
- 返回 Message 对象

**异常**：
- `AgentError`: Agent 执行错误
- `RecursionError`: 递归深度超限

### `reply(message: Message) -> Message`

`run()` 的别名，更语义化。

```python
response = await agent.reply(message)
```

### `reset() -> None`

重置 Agent 状态，清除对话历史和统计。

```python
# 多轮对话
await agent.run(Message(role="user", content="我叫张三"))
await agent.run(Message(role="user", content="我叫什么"))  # Agent 记得

# 重置
agent.reset()

await agent.run(Message(role="user", content="我叫什么"))  # Agent 不记得了
```

### `get_stats() -> dict`

获取 Agent 统计信息。

```python
stats = agent.get_stats()
print(stats)
# {
#   "name": "assistant",
#   "num_tools": 2,
#   "executor_stats": {
#     "total_llm_calls": 5,
#     "total_tool_calls": 3,
#     "total_tokens_input": 1234,
#     "total_tokens_output": 567,
#     ...
#   },
#   "skills": {
#     "total_skills": 3,
#     "enabled_skills": 2,
#     ...
#   }
# }
```

---

## 工具集成

### 定义工具

使用 `@tool` 装饰器：

```python
from loom.builtin import tool

@tool(name="get_weather", description="获取城市天气")
async def get_weather(city: str) -> str:
    """
    获取指定城市的天气信息

    Args:
        city: 城市名称

    Returns:
        天气描述
    """
    # 模拟天气API
    return f"{city}的天气：晴天，25°C"
```

### 工具最佳实践

#### 1. 详细的文档字符串

```python
@tool(name="search")
async def search(query: str, max_results: int = 10) -> str:
    """
    搜索网络信息

    Args:
        query: 搜索关键词或问题
        max_results: 最大结果数量，默认10

    Returns:
        搜索结果的摘要

    Examples:
        search("Python 教程", max_results=5)
        search("今天的新闻")
    """
    ...
```

#### 2. 清晰的参数类型

```python
from typing import List, Optional

@tool(name="analyze_data")
async def analyze_data(
    data: List[float],
    method: str = "mean",
    threshold: Optional[float] = None
) -> dict:
    """数据分析工具"""
    ...
```

#### 3. 错误处理

```python
@tool(name="api_call")
async def api_call(endpoint: str) -> str:
    """调用外部API"""
    try:
        # API 调用逻辑
        result = await make_request(endpoint)
        return result
    except Exception as e:
        return f"API调用失败: {str(e)}"
```

### 并行工具执行

v0.1.6 默认启用工具并行执行：

```python
# Agent 会自动并行执行不相关的工具
message = Message(
    role="user",
    content="查询北京和上海的天气，以及今天的新闻"
)
# get_weather("北京"), get_weather("上海"), get_news() 并行执行
response = await agent.run(message)
```

---

## Skills 系统

v0.1.6 引入的 Skills 系统允许模块化扩展 Agent 能力。

### 启用 Skills

```python
agent = loom.agent(
    name="agent",
    llm=llm,
    enable_skills=True,  # 默认启用
    skills_dir="./skills"  # Skills 目录
)
```

### Skills 管理方法

#### `list_skills(category: Optional[str] = None) -> List[Skill]`

列出可用的 Skills：

```python
# 列出所有 Skills
all_skills = agent.list_skills()
for skill in all_skills:
    print(f"{skill.metadata.name}: {skill.metadata.description}")

# 按分类筛选
analysis_skills = agent.list_skills(category="analysis")
```

#### `get_skill(name: str) -> Optional[Skill]`

获取特定 Skill：

```python
pdf_skill = agent.get_skill("pdf_analyzer")
if pdf_skill:
    print(f"Quick Guide: {pdf_skill.quick_guide}")
    # 加载详细文档
    detailed_doc = pdf_skill.load_detailed_doc()
```

#### `enable_skill(name: str) -> bool`

启用 Skill：

```python
success = agent.enable_skill("web_research")
if success:
    print("Skill enabled")
```

#### `disable_skill(name: str) -> bool`

禁用 Skill：

```python
agent.disable_skill("pdf_analyzer")
```

#### `reload_skills() -> None`

重新加载所有 Skills：

```python
# 修改 Skills 文件后
agent.reload_skills()
```

#### `create_skill(name, description, category, **kwargs) -> Skill`

编程创建 Skill：

```python
new_skill = agent.create_skill(
    name="custom_skill",
    description="我的自定义技能",
    category="tools",
    quick_guide="使用方法...",
    tags=["custom", "test"]
)
```

### Skills 示例

```python
import asyncio
from loom import Message, SimpleAgent
from loom.builtin import OpenAILLM

async def main():
    agent = loom.agent(
        name="analyst",
        llm=OpenAILLM(api_key="..."),
        enable_skills=True
    )

    # 列出 Skills
    skills = agent.list_skills()
    print(f"可用技能: {[s.metadata.name for s in skills]}")

    # 使用 Skill（通过自然语言）
    message = Message(
        role="user",
        content="分析这个 PDF 文档: report.pdf"
    )
    response = await agent.run(message)
    print(response.content)

asyncio.run(main())
```

详见 [Skills 系统指南](../skills/overview.md)。

---

## 系统提示

### 默认系统提示

如果不提供 `system_prompt`，SimpleAgent 会自动生成包含：

1. 基础角色描述
2. Skills 索引（如果启用）
3. 工具使用指南（如果有工具）

**示例生成的提示**：

```
You are assistant, a helpful assistant.

# Available Skills

Below is a catalog of specialized skills you can reference:

1. **pdf_analyzer** (analysis)
   📄 Details: Use PyPDF2 or pdfplumber to extract text...

2. **web_research** (tools)
   📄 Details: Use search APIs...

# Tool Usage Guidelines

1. **Understand Available Tools**: Always check...
2. **Match Tools to Intent**: Choose tools...
...
```

### 自定义系统提示

```python
custom_prompt = """
你是一个专业的数据分析师 Agent。

核心能力：
- 数据清洗和预处理
- 统计分析
- 数据可视化
- 洞察提取

工作流程：
1. 理解用户数据需求
2. 选择合适的分析方法
3. 使用工具执行分析
4. 提供清晰的结论和建议

注意事项：
- 确保数据质量
- 解释统计指标
- 提供可操作的建议
"""

agent = loom.agent(
    name="data-analyst",
    llm=llm,
    system_prompt=custom_prompt
)
```

### 动态更新提示

```python
# 修改系统提示
agent.system_prompt = "新的系统提示"
agent.executor.system_prompt = agent.system_prompt  # 同步到执行器
```

---

## 事件处理

v0.1.6 提供完整的事件系统，追踪 Agent 执行的全生命周期。

### 事件类型

- `AGENT_START` / `AGENT_END` / `AGENT_ERROR`
- `LLM_START` / `LLM_END` / `LLM_STREAM_CHUNK`
- `TOOL_START` / `TOOL_END` / `TOOL_ERROR`

### 设置事件处理器

```python
from loom.core.events import AgentEventType

def event_handler(event):
    """处理事件"""
    event_type = event.type
    event_data = event.data
    agent_name = event.agent_name

    if event_type == AgentEventType.AGENT_START:
        print(f"🚀 {agent_name} 开始执行")

    elif event_type == AgentEventType.LLM_START:
        print(f"🤖 调用 LLM...")

    elif event_type == AgentEventType.TOOL_START:
        tool_name = event_data.get("tool_name")
        args = event_data.get("args")
        print(f"🔧 调用工具: {tool_name}({args})")

    elif event_type == AgentEventType.TOOL_END:
        tool_name = event_data.get("tool_name")
        result = event_data.get("result")
        print(f"✓ 工具完成: {tool_name} → {result}")

    elif event_type == AgentEventType.AGENT_END:
        print(f"✅ {agent_name} 完成执行")

# 创建 Agent 时传递
agent = loom.agent(
    name="agent",
    llm=llm,
    event_handler=event_handler  # ⚠️ 注意：这个参数需要传递给 AgentExecutor
)

# 或者直接设置到 executor
agent.executor.event_handler = event_handler
```

### 实时监控示例

```python
import asyncio
from loom import Message, SimpleAgent
from loom.builtin import OpenAILLM, tool
from loom.core.events import AgentEventType

@tool(name="search")
async def search(query: str) -> str:
    """搜索信息"""
    await asyncio.sleep(1)  # 模拟搜索延迟
    return f"搜索结果: {query}"

def monitor(event):
    """监控函数"""
    if event.type == AgentEventType.TOOL_START:
        print(f"⏱️ 开始: {event.data['tool_name']}")
    elif event.type == AgentEventType.TOOL_END:
        print(f"✅ 完成: {event.data['tool_name']}")

async def main():
    agent = loom.agent(
        name="agent",
        llm=OpenAILLM(api_key="..."),
        tools=[search]
    )
    agent.executor.event_handler = monitor

    message = Message(role="user", content="搜索 Loom Agent")
    response = await agent.run(message)
    print(f"\n结果: {response.content}")

asyncio.run(main())
```

---

## 统计和监控

### 获取统计信息

```python
stats = agent.get_stats()
```

**返回示例**：

```python
{
    "name": "assistant",
    "num_tools": 3,
    "executor_stats": {
        "total_llm_calls": 10,      # LLM 调用次数
        "total_tool_calls": 5,       # 工具调用次数
        "total_tokens_input": 2345,  # 输入 tokens
        "total_tokens_output": 678,  # 输出 tokens
        "total_errors": 0,           # 错误次数
        "max_iterations": 20
    },
    "skills": {
        "total_skills": 3,
        "enabled_skills": 2,
        "categories": 2
    }
}
```

### 实时统计示例

```python
async def main():
    agent = loom.agent(name="agent", llm=llm, tools=[...])

    # 执行任务
    message = Message(role="user", content="...")
    response = await agent.run(message)

    # 查看统计
    stats = agent.get_stats()
    executor_stats = stats["executor_stats"]

    print(f"📊 统计信息:")
    print(f"  LLM 调用: {executor_stats['total_llm_calls']}")
    print(f"  工具调用: {executor_stats['total_tool_calls']}")
    print(f"  总 Tokens: {executor_stats['total_tokens_input'] + executor_stats['total_tokens_output']}")

    # 计算成本（假设 GPT-4 价格）
    input_cost = executor_stats['total_tokens_input'] * 0.03 / 1000
    output_cost = executor_stats['total_tokens_output'] * 0.06 / 1000
    total_cost = input_cost + output_cost
    print(f"  预估成本: ${total_cost:.4f}")
```

---

## 高级用法

### 多轮对话

SimpleAgent 自动管理对话历史：

```python
async def chat_loop():
    agent = loom.agent(name="chatbot", llm=llm)

    conversations = [
        "我叫张三，我是一名工程师",
        "我的职业是什么？",
        "我叫什么名字？"
    ]

    for user_input in conversations:
        print(f"\n👤 用户: {user_input}")
        message = Message(role="user", content=user_input)
        response = await agent.run(message)
        print(f"🤖 Agent: {response.content}")

asyncio.run(chat_loop())
```

**输出**：
```
👤 用户: 我叫张三，我是一名工程师
🤖 Agent: 你好张三！很高兴认识你这位工程师...

👤 用户: 我的职业是什么？
🤖 Agent: 你是一名工程师

👤 用户: 我叫什么名字？
🤖 Agent: 你叫张三
```

### 条件工具使用

```python
from loom.builtin import tool

@tool(name="vip_service")
async def vip_service(request: str) -> str:
    """VIP专属服务（仅VIP用户可用）"""
    return f"VIP服务: {request}"

async def main():
    # 普通用户
    normal_agent = loom.agent(
        name="normal-agent",
        llm=llm,
        tools=[],  # 无VIP工具
        system_prompt="你是普通客服"
    )

    # VIP用户
    vip_agent = loom.agent(
        name="vip-agent",
        llm=llm,
        tools=[vip_service],  # 有VIP工具
        system_prompt="你是VIP客服，可以提供专属服务"
    )
```

### 嵌套 Agent（Agent 调用 Agent）

```python
# 专家 Agent
expert_agent = loom.agent(
    name="expert",
    llm=llm,
    system_prompt="你是技术专家"
)

# 协调 Agent
async def main():
    coordinator = loom.agent(
        name="coordinator",
        llm=llm,
        system_prompt="你是协调员，遇到技术问题请咨询专家"
    )

    user_message = Message(role="user", content="如何优化数据库？")

    # 协调员判断需要专家
    if "数据库" in user_message.content:
        # 转发给专家
        expert_response = await expert_agent.run(user_message)
        print(f"专家回答: {expert_response.content}")
```

---

## 最佳实践

### 1. 明确的 Agent 命名

```python
# ✅ 好的命名
agent = loom.agent(name="customer-service-bot", llm=llm)
agent = loom.agent(name="data-analyzer", llm=llm)

# ❌ 不好的命名
agent = loom.agent(name="agent", llm=llm)
agent = loom.agent(name="bot1", llm=llm)
```

### 2. 工具文档完善

```python
# ✅ 详细的文档
@tool(name="calculate", description="执行数学计算")
async def calculate(expression: str) -> float:
    """
    计算数学表达式

    Args:
        expression: 数学表达式，支持 +, -, *, /, **
                   例如: "2 + 3", "10 * 5", "2 ** 8"

    Returns:
        计算结果（浮点数）

    Raises:
        ValueError: 表达式无效时
    """
    return eval(expression)

# ❌ 缺乏文档
@tool(name="calc")
async def calc(expr: str) -> float:
    return eval(expr)
```

### 3. 合理的递归深度

```python
# 简单任务
agent = loom.agent(
    name="simple-agent",
    llm=llm,
    max_recursion_depth=10  # 足够
)

# 复杂任务（多步骤）
agent = loom.agent(
    name="complex-agent",
    llm=llm,
    tools=[...],  # 多个工具
    max_recursion_depth=30  # 更多轮次
)
```

### 4. 定期重置状态

```python
async def process_requests(requests):
    agent = loom.agent(name="processor", llm=llm)

    for request in requests:
        # 处理请求
        response = await agent.run(Message(role="user", content=request))
        print(response.content)

        # 重置状态（避免上下文污染）
        agent.reset()
```

### 5. 监控和日志

```python
def comprehensive_logger(event):
    """完整的日志记录"""
    timestamp = event.timestamp
    event_type = event.type.value
    agent_name = event.agent_name

    log_message = f"[{timestamp}] {agent_name} - {event_type}"

    if event.data:
        log_message += f": {event.data}"

    print(log_message)

    # 可选：写入文件
    with open("agent.log", "a") as f:
        f.write(log_message + "\n")

agent = loom.agent(name="agent", llm=llm)
agent.executor.event_handler = comprehensive_logger
```

### 6. 错误处理

```python
from loom.core import AgentError, RecursionError

async def safe_run(agent, message):
    """安全执行 Agent"""
    try:
        response = await agent.run(message)
        return response.content
    except RecursionError:
        return "任务太复杂，请简化您的请求"
    except AgentError as e:
        return f"执行出错: {str(e)}"
    except Exception as e:
        return f"未知错误: {str(e)}"
```

---

## 常见问题

### Q1: Agent 不调用工具怎么办？

**可能原因**：
1. 工具描述不清晰
2. 系统提示过于限制
3. LLM 判断不需要工具

**解决方案**：
```python
# 1. 改进工具描述
@tool(
    name="search",
    description="在网络上搜索信息。当用户询问实时信息、新闻、或你不知道的内容时使用"
)
async def search(query: str) -> str:
    """详细的文档字符串..."""
    ...

# 2. 在系统提示中强调工具使用
system_prompt = """
你是助手。重要：当用户需要实时信息时，必须使用 search 工具。
"""

# 3. 使用更智能的模型（如 GPT-4）
llm = OpenAILLM(model="gpt-4", api_key="...")
```

### Q2: 如何限制 Token 使用？

```python
# 方法1: 限制LLM的max_tokens
llm = OpenAILLM(
    api_key="...",
    max_tokens=500  # 限制每次响应
)

# 方法2: 限制上下文大小
from loom.core import ContextManager

context_mgr = ContextManager(
    max_context_tokens=4000  # 限制上下文
)

agent = loom.agent(
    name="agent",
    llm=llm,
    context_manager=context_mgr
)

# 方法3: 定期重置（清除历史）
agent.reset()
```

### Q3: 如何加速 Agent 执行？

**优化策略**：

1. **使用更快的模型**
```python
llm = OpenAILLM(model="gpt-3.5-turbo")  # 比 GPT-4 快
```

2. **减少工具调用**
```python
# 优化工具逻辑，一次返回更多信息
@tool(name="get_info")
async def get_info(topic: str) -> dict:
    """一次返回完整信息"""
    return {
        "summary": "...",
        "details": "...",
        "related": [...]
    }
```

3. **启用并行执行**（v0.1.6默认开启）
```python
# 已自动并行，无需配置
```

4. **减少递归深度**
```python
agent = loom.agent(
    name="agent",
    llm=llm,
    max_recursion_depth=10  # 减少最大轮次
)
```

### Q4: 如何保存对话历史？

```python
# 获取对话历史
context = agent.executor.context_manager
messages = context.messages

# 保存到文件
import json

def save_history(messages, filepath):
    history = [
        {
            "role": msg.role,
            "content": msg.content,
            "timestamp": msg.timestamp if hasattr(msg, 'timestamp') else None
        }
        for msg in messages
    ]

    with open(filepath, "w") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)

save_history(messages, "chat_history.json")
```

### Q5: 如何调试 Agent？

```python
# 1. 启用详细日志
def debug_handler(event):
    print(f"[DEBUG] {event.type.value}")
    print(f"  Data: {event.data}")
    print(f"  Agent: {event.agent_name}")
    print()

agent.executor.event_handler = debug_handler

# 2. 打印系统提示
print("System Prompt:")
print(agent.system_prompt)
print()

# 3. 检查工具列表
print("Available Tools:")
for tool in agent.tools:
    print(f"  - {tool.name}: {tool.description}")
print()

# 4. 查看统计
stats = agent.get_stats()
print(f"Stats: {stats}")
```

---

## 相关资源

- [创建第一个 Agent](../../getting-started/first-agent.md)
- [工具开发指南](../tools/development.md)
- [Skills 系统](../skills/overview.md)
- [Crew 多代理协作](../patterns/crew.md)
- [事件系统](../advanced/events.md)
- [API 参考](../../api/agents.md)

---

## 下一步

- 学习 [ReActAgent](./react-agent.md)（推理+行动模式）
- 探索 [自定义 Agent](./custom-agent.md)
- 了解 [Crew 协作](../patterns/crew.md)

---

**祝你构建强大的 Agent！** 🚀
