# 创建你的第一个 Agent

**版本**: v0.1.9 
**预计时间**: 10 分钟

本教程将带你一步步创建你的第一个 Loom Agent，从最简单的对话 Agent 到带工具调用的实用 Agent。

---

## 📝 前置准备

1. 已安装 Loom Agent (参见 [安装指南](./installation.md))
2. 拥有 OpenAI API Key
3. 基础的 Python async/await 知识

---

## 🎯 第一步：最简单的对话 Agent

创建文件 `hello_agent.py`：

```python
import asyncio
from loom import Message, SimpleAgent
from loom.builtin import OpenAILLM

async def main():
    # 1. 创建 LLM
    llm = OpenAILLM(
        model="gpt-4",
        api_key="your-api-key-here"  # 或使用环境变量 OPENAI_API_KEY
    )

    # 2. 创建 Agent
    agent = loom.agent(
        name="assistant",
        llm=llm
    )

    # 3. 创建消息并运行
    message = Message(role="user", content="你好！介绍一下你自己。")
    response = await agent.run(message)

    # 4. 打印响应
    print(f"Agent: {response.content}")

if __name__ == "__main__":
    asyncio.run(main())
```

运行：

```bash
python hello_agent.py
```

**输出示例**：
```
Agent: 你好！我是一个 AI 助手，使用 Loom Agent 框架构建...
```

---

## 🔧 第二步：添加工具能力

让 Agent 能够执行计算：

```python
import asyncio
from loom import Message, SimpleAgent
from loom.builtin import OpenAILLM, tool

# 1. 定义工具
@tool(name="calculator", description="计算数学表达式")
async def calculator(expression: str) -> float:
    """
    计算数学表达式的结果

    Args:
        expression: 数学表达式，如 "2 + 2" 或 "10 * 5"

    Returns:
        计算结果
    """
    try:
        # 警告：生产环境请使用更安全的方法
        result = eval(expression)
        return float(result)
    except Exception as e:
        return f"错误: {str(e)}"

async def main():
    # 2. 创建带工具的 Agent
    agent = loom.agent(
        name="calculator-agent",
        llm=OpenAILLM(api_key="your-api-key-here"),
        tools=[calculator]  # 传递工具列表
    )

    # 3. 测试工具调用
    message = Message(role="user", content="计算 123 * 456 的结果")
    response = await agent.run(message)

    print(f"Agent: {response.content}")
    # 输出: Agent: 123 * 456 的结果是 56088

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 💬 第三步：多轮对话

Loom 的 Agent 自动管理对话历史：

```python
import asyncio
from loom import Message, SimpleAgent
from loom.builtin import OpenAILLM

async def main():
    agent = loom.agent(
        name="chat-agent",
        llm=OpenAILLM(api_key="your-api-key-here")
    )

    # 第一轮对话
    msg1 = Message(role="user", content="我叫张三")
    res1 = await agent.run(msg1)
    print(f"User: 我叫张三")
    print(f"Agent: {res1.content}\n")

    # 第二轮对话 - Agent 会记住你的名字
    msg2 = Message(role="user", content="我叫什么名字？")
    res2 = await agent.run(msg2)
    print(f"User: 我叫什么名字？")
    print(f"Agent: {res2.content}")
    # 输出: Agent: 你叫张三

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 🎨 第四步：自定义系统提示

给 Agent 一个专属的身份：

```python
import asyncio
from loom import Message, SimpleAgent
from loom.builtin import OpenAILLM

async def main():
    # 自定义系统提示
    system_prompt = """
你是一个专业的 Python 编程助手。

你的特点：
- 专注于 Python 编程问题
- 提供清晰、简洁的代码示例
- 遵循 PEP 8 规范
- 友好且乐于助人

当用户询问非 Python 问题时，礼貌地引导他们回到 Python 主题。
"""

    agent = loom.agent(
        name="python-tutor",
        llm=OpenAILLM(api_key="your-api-key-here"),
        system_prompt=system_prompt
    )

    message = Message(role="user", content="如何在 Python 中读取文件？")
    response = await agent.run(message)

    print(f"Agent: {response.content}")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 🔍 第五步：观测和调试

了解 Agent 的执行过程：

```python
import asyncio
from loom import Message, SimpleAgent
from loom.builtin import OpenAILLM, tool
from loom.core.events import AgentEventType

# 定义工具
@tool(name="get_weather")
async def get_weather(city: str) -> str:
    """获取城市天气（模拟）"""
    return f"{city}的天气：晴天，温度 25°C"

# 事件处理器
def event_handler(event):
    """处理 Agent 事件"""
    if event.type == AgentEventType.AGENT_START:
        print(f"🚀 Agent 开始执行")
    elif event.type == AgentEventType.LLM_START:
        print(f"🤖 调用 LLM...")
    elif event.type == AgentEventType.TOOL_START:
        print(f"🔧 调用工具: {event.data.get('tool_name')}")
    elif event.type == AgentEventType.TOOL_END:
        print(f"✓ 工具完成: {event.data.get('tool_name')}")
    elif event.type == AgentEventType.AGENT_END:
        print(f"✅ Agent 完成执行")

async def main():
    agent = loom.agent(
        name="weather-agent",
        llm=OpenAILLM(api_key="your-api-key-here"),
        tools=[get_weather],
        event_handler=event_handler  # 传递事件处理器
    )

    message = Message(role="user", content="北京的天气怎么样？")
    response = await agent.run(message)

    print(f"\nAgent: {response.content}")

    # 查看统计信息
    stats = agent.get_stats()
    print(f"\n统计信息:")
    print(f"- LLM 调用次数: {stats['total_llm_calls']}")
    print(f"- 工具调用次数: {stats['total_tool_calls']}")
    print(f"- 总 Token 数: {stats['total_tokens_input'] + stats['total_tokens_output']}")

if __name__ == "__main__":
    asyncio.run(main())
```

**输出示例**：
```
🚀 Agent 开始执行
🤖 调用 LLM...
🔧 调用工具: get_weather
✓ 工具完成: get_weather
🤖 调用 LLM...
✅ Agent 完成执行

Agent: 北京的天气是晴天，温度 25°C

统计信息:
- LLM 调用次数: 2
- 工具调用次数: 1
- 总 Token 数: 342
```

---

## 📊 第六步：使用 Skills 系统

Skills 是 v0.1.6 的新功能，让 Agent 拥有模块化能力：

```python
import asyncio
from loom import Message, SimpleAgent
from loom.builtin import OpenAILLM

async def main():
    # 启用 Skills 系统
    agent = loom.agent(
        name="skilled-agent",
        llm=OpenAILLM(api_key="your-api-key-here"),
        enable_skills=True,  # 启用 Skills
        skills_dir="./skills"  # Skills 目录
    )

    # 列出可用的 Skills
    skills = agent.list_skills()
    print("可用的 Skills:")
    for skill in skills:
        print(f"- {skill.metadata.name}: {skill.metadata.description}")

    # 使用 Skill
    message = Message(role="user", content="分析这个 PDF 文件: report.pdf")
    response = await agent.run(message)
    print(f"\nAgent: {response.content}")

if __name__ == "__main__":
    asyncio.run(main())
```

更多关于 Skills 的内容，请参阅 [Skills 系统指南](../guides/skills/overview.md)。

---

## 🎯 完整示例：智能客服 Agent

结合以上所有内容的完整示例：

```python
import asyncio
from loom import Message, SimpleAgent
from loom.builtin import OpenAILLM, tool
from datetime import datetime

# 定义工具
@tool(name="get_order_status")
async def get_order_status(order_id: str) -> str:
    """查询订单状态（模拟）"""
    return f"订单 {order_id} 状态：已发货，预计明天到达"

@tool(name="get_current_time")
async def get_current_time() -> str:
    """获取当前时间"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# 事件处理器
def log_event(event):
    """记录关键事件"""
    if event.type.value in ["tool_start", "tool_end"]:
        print(f"[LOG] {event.type.value}: {event.data}")

async def main():
    # 系统提示
    system_prompt = """
你是一个智能客服 Agent。

职责：
1. 友好、专业地回答客户问题
2. 使用工具查询订单状态和时间
3. 提供准确的信息
4. 遇到无法处理的问题，提示用户联系人工客服

回答要求：
- 简洁明了
- 有同理心
- 积极主动
"""

    # 创建客服 Agent
    agent = loom.agent(
        name="customer-service",
        llm=OpenAILLM(api_key="your-api-key-here", model="gpt-4"),
        tools=[get_order_status, get_current_time],
        system_prompt=system_prompt,
        event_handler=log_event
    )

    # 模拟客户对话
    conversations = [
        "你好，我想查询订单 12345 的状态",
        "什么时候能送到？",
        "现在几点了？",
        "谢谢！"
    ]

    for user_input in conversations:
        print(f"\n👤 用户: {user_input}")
        message = Message(role="user", content=user_input)
        response = await agent.run(message)
        print(f"🤖 客服: {response.content}")

    # 显示统计信息
    print(f"\n" + "="*50)
    stats = agent.get_stats()
    print(f"📊 本次会话统计:")
    print(f"  - LLM 调用: {stats['total_llm_calls']} 次")
    print(f"  - 工具调用: {stats['total_tool_calls']} 次")
    print(f"  - Token 使用: {stats['total_tokens_input'] + stats['total_tokens_output']}")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 🎓 下一步学习

恭喜！你已经创建了你的第一个 Loom Agent。接下来你可以：

### 基础学习
- [5分钟快速开始](./quickstart.md) - 更多快速示例
- [API 快速参考](./quick-reference.md) - 常用 API 速查

### 进阶主题
- [SimpleAgent 详细指南](../guides/agents/simple-agent.md) - Agent 的所有功能
- [工具开发指南](../guides/tools/development.md) - 创建自定义工具
- [Skills 系统](../guides/skills/overview.md) - 模块化能力扩展

### 高级功能
- [Crew 多代理协作](../guides/patterns/crew.md) - 构建多 Agent 系统
- [事件系统](../guides/advanced/events.md) - 深度观测和钩子
- [架构设计](../architecture/overview.md) - 理解 Loom 的设计

### 实践项目
- [基础示例](../examples/basic/) - 更多实用示例
- [高级示例](../examples/advanced/) - 复杂场景实现
- [集成示例](../examples/integrations/) - 与其他框架集成

---

## ❓ 常见问题

### Q: Agent 没有调用工具怎么办？

**A**: 确保：
1. 工具描述清晰（`@tool` 的 `description` 参数）
2. 函数有详细的 docstring
3. 参数类型注解正确
4. 用户输入明确需要使用该工具

### Q: 如何限制 Agent 的响应长度？

**A**: 在创建 LLM 时设置参数：
```python
llm = OpenAILLM(
    api_key="...",
    max_tokens=500  # 限制最大 tokens
)
```

### Q: 如何保存对话历史？

**A**: Loom 自动管理内存中的对话历史。要持久化，请参阅 [Memory 管理指南](../guides/advanced/memory.md)。

### Q: Agent 执行太慢怎么办？

**A**:
1. 使用更快的模型（如 `gpt-3.5-turbo`）
2. 启用工具并行执行（v0.1.6 默认开启）
3. 减少 `max_iterations`
4. 优化工具执行时间

---

## 💡 提示和技巧

1. **环境变量管理 API Keys**：不要在代码中硬编码 API keys
2. **使用事件处理器**：便于调试和监控
3. **详细的工具描述**：帮助 LLM 正确选择工具
4. **系统提示很重要**：明确 Agent 的角色和限制
5. **定期查看统计信息**：优化成本和性能

---

## 📚 相关资源

- [Loom GitHub 仓库](https://github.com/kongusen/loom-agent)
- [完整 API 参考](../api/)
- [示例代码库](../examples/)
- [变更日志](../../CHANGELOG.md)

---

**祝你构建 Agent 顺利！** 🚀

如有问题，欢迎在 [GitHub Issues](https://github.com/kongusen/loom-agent/issues) 提问。
