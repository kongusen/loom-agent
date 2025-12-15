# ⚡ 5分钟快速开始

**版本**: v0.1.6
**预计时间**: 5 分钟

快速体验 Loom Agent 的核心功能。

---

## 🚀 安装

```bash
pip install "loom-agent[openai]"
```

---

## 💬 示例 1: 简单对话 (1 分钟)

```python
import asyncio
from loom import Message, SimpleAgent
from loom.builtin import OpenAILLM

async def main():
    agent = loom.agent(
        name="assistant",
        llm=OpenAILLM(api_key="your-api-key")
    )

    msg = Message(role="user", content="介绍一下 Loom Agent")
    response = await agent.run(msg)
    print(response.content)

asyncio.run(main())
```

---

## 🔧 示例 2: 带工具的 Agent (2 分钟)

```python
import asyncio
from loom import Message, SimpleAgent
from loom.builtin import OpenAILLM, tool

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

    msg = Message(role="user", content="计算 123 * 456")
    response = await agent.run(msg)
    print(response.content)  # 输出: 56088

asyncio.run(main())
```

---

## 🤝 示例 3: 多代理协作 (3 分钟)

```python
import asyncio
from loom.patterns import Crew, CrewRole
import loom
from loom.builtin import OpenAILLM

async def main():
    llm = OpenAILLM(api_key="your-api-key")

    # 创建研究员
    researcher = loom.agent(
        name="researcher",
        llm=llm,
        system_prompt="你是一个研究员，负责收集信息"
    )

    # 创建撰写员
    writer = loom.agent(
        name="writer",
        llm=llm,
        system_prompt="你是一个撰写员，负责整理成文章"
    )

    # 创建 Crew
    crew = Crew(
        agents={
            "researcher": CrewRole(agent=researcher, can_delegate=False),
            "writer": CrewRole(agent=writer, can_delegate=False)
        },
        coordinator_llm=llm
    )

    # 执行任务
    result = await crew.run("写一篇关于 AI Agent 的文章")
    print(result)

asyncio.run(main())
```

---

## 📊 示例 4: 启用 Skills (4 分钟)

```python
import asyncio
from loom import Message, SimpleAgent
from loom.builtin import OpenAILLM

async def main():
    agent = loom.agent(
        name="skilled-agent",
        llm=OpenAILLM(api_key="your-api-key"),
        enable_skills=True,        # 启用 Skills
        skills_dir="./skills"      # Skills 目录
    )

    # 列出可用 Skills
    skills = agent.list_skills()
    print(f"可用技能: {[s.metadata.name for s in skills]}")

    # 使用 Skills
    msg = Message(role="user", content="分析这个 PDF: report.pdf")
    response = await agent.run(msg)
    print(response.content)

asyncio.run(main())
```

---

## 📈 示例 5: 监控和统计 (5 分钟)

```python
import asyncio
from loom import Message, SimpleAgent
from loom.builtin import OpenAILLM, tool
from loom.core.events import AgentEventType

@tool(name="search")
async def search(query: str) -> str:
    """搜索信息（模拟）"""
    return f"关于 {query} 的搜索结果..."

def event_handler(event):
    """监控 Agent 事件"""
    if event.type == AgentEventType.TOOL_START:
        print(f"🔧 调用工具: {event.data['tool_name']}")
    elif event.type == AgentEventType.LLM_START:
        print(f"🤖 调用 LLM...")

async def main():
    agent = loom.agent(
        name="monitored-agent",
        llm=OpenAILLM(api_key="your-api-key"),
        tools=[search],
        event_handler=event_handler  # 监控事件
    )

    msg = Message(role="user", content="搜索 Loom Agent 框架")
    response = await agent.run(msg)
    print(f"\n响应: {response.content}")

    # 查看统计
    stats = agent.get_stats()
    print(f"\n📊 统计:")
    print(f"  LLM 调用: {stats['total_llm_calls']}")
    print(f"  工具调用: {stats['total_tool_calls']}")
    print(f"  Token 数: {stats['total_tokens_input'] + stats['total_tokens_output']}")

asyncio.run(main())
```

---

## 🎯 核心概念速览

| 概念 | 说明 | 代码示例 |
|------|------|----------|
| **Message** | 统一消息格式 | `Message(role="user", content="...")` |
| **SimpleAgent** | 基础 Agent | `loom.agent(name="...", llm=...)` |
| **Tool** | 工具定义 | `@tool(name="...")\nasync def ...` |
| **Crew** | 多 Agent 协作 | `Crew(agents={...})` |
| **Skills** | 模块化能力 | `enable_skills=True` |
| **Events** | 事件监控 | `event_handler=func` |

---

## 📚 下一步

### 深入学习
- [详细安装指南](./installation.md) - 所有安装选项
- [创建第一个 Agent](./first-agent.md) - 10分钟完整教程
- [API 快速参考](./quick-reference.md) - 常用 API 速查

### 核心功能
- [SimpleAgent 指南](../guides/agents/simple-agent.md) - Agent 完整功能
- [工具开发](../guides/tools/development.md) - 自定义工具
- [Skills 系统](../guides/skills/overview.md) - 模块化能力

### 高级主题
- [Crew 协作](../guides/patterns/crew.md) - 多 Agent 系统
- [事件系统](../guides/advanced/events.md) - 深度监控
- [架构设计](../architecture/overview.md) - 框架原理

---

## 💡 快速提示

### 使用环境变量管理 API Key

```bash
export OPENAI_API_KEY="sk-..."
```

```python
# 自动从环境变量读取
llm = OpenAILLM()  # 无需传递 api_key
```

### 完整的错误处理

```python
try:
    response = await agent.run(message)
except Exception as e:
    print(f"错误: {e}")
```

### 调试模式

```python
# 打印详细日志
agent = loom.agent(
    name="debug-agent",
    llm=llm,
    event_handler=lambda e: print(f"[{e.type.value}] {e.data}")
)
```

---

## ❓ 遇到问题？

- **安装问题**: 查看 [安装指南](./installation.md#常见问题)
- **API 问题**: 查看 [API 参考](../api/)
- **示例代码**: 查看 [示例库](../examples/)
- **提交 Bug**: [GitHub Issues](https://github.com/kongusen/loom-agent/issues)

---

## 🌟 v0.1.6 新特性

- ✅ **工具并行执行**: 多工具调用 3x 性能提升
- ✅ **完整事件系统**: agent/llm/tool 全生命周期追踪
- ✅ **Token 统计**: 完整的成本和性能分析
- ✅ **Skills 系统**: 模块化能力扩展
- ✅ **智能去重**: Crew 任务自动去重
- ✅ **四层容错**: 自动重试和降级策略

详见 [CHANGELOG](../../CHANGELOG.md)

---

**开始构建你的 AI Agent 吧！** 🚀
