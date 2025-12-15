# 🧵 Loom Agent

<div align="center">

**基于递归状态机的轻量级 AI Agent 框架**

**Simple, Powerful, Production-Ready Agent Framework**

[![PyPI](https://img.shields.io/pypi/v/loom-agent.svg)](https://pypi.org/project/loom-agent/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**中文** | [English](README_EN.md)

[快速开始](#-快速开始) | [核心特性](#-核心特性) | [多 Agent 协作](#-多-agent-协作-crew) | [文档](#-文档)

</div>

---

## 🎯 什么是 Loom Agent？

Loom Agent 是一个**简单、强大、生产就绪**的 AI Agent 框架，基于**递归状态机 (Message → Message)** 架构。

### 🌟 为什么选择 Loom Agent？

| 特性 | LangGraph | AutoGen | CrewAI | **Loom Agent** |
|------|-----------|---------|--------|----------------|
| **核心依赖** | 10+ 包 | OpenAI 必需 | 5+ 包 | **仅 2 个包** |
| **学习曲线** | 陡峭（图定义） | 中等 | 中等 | **平缓（Message → Message）** |
| **代码量** | 需要显式连线 | 配置复杂 | 配置复杂 | ✅ **极简 API** |
| **多 Agent** | ❌ | ✅ | ✅ | ✅ **Crew + 智能协调** |
| **Skills 系统** | ❌ | ❌ | ❌ | ✅ **三层渐进式披露** |
| **并行执行** | 基础 | 基础 | ❌ | ✅ **Agent + Tool 双层并行** |
| **容错恢复** | ❌ | ❌ | ❌ | ✅ **四层容错策略** |
| **可观测性** | 基础 | 基础 | 基础 | ✅ **完整事件系统 + Token 统计** |
| **集成灵活性** | 内置集成 | 绑定 OpenAI | 内置集成 | ✅ **Protocol-based，自由集成** |
| **生产就绪** | ⚠️ | ⚠️ | ⚠️ | ✅ **开箱即用** |

**定位**：Loom Agent = **简单易用** + **功能完整** + **生产就绪**

---

## 📦 安装

```bash
# 核心框架（仅 2 个依赖：Python + Pydantic）
pip install loom-agent
```

**要求**: Python 3.11+

**核心依赖**:
- Python >= 3.11
- Pydantic >= 2.5.0

**集成示例**：框架不包含任何第三方服务集成（如 OpenAI, Anthropic 等），所有集成作为**示例**提供在 `examples/` 目录。你可以：
- 直接使用示例中的集成（需要单独安装对应的 SDK）
- 参考示例实现自己的集成
- 查看 [examples/README.md](examples/README.md) 了解详情

---

## 🚀 快速开始

### 30秒上手

```python
import asyncio
import loom, Message
from examples.integrations.openai_llm import OpenAILLM  # 从 examples 导入

async def main():
    # 安装 OpenAI SDK: pip install openai

    # 创建 Agent
    agent = loom.agent(
        name="assistant",
        llm=OpenAILLM(api_key="...")
    )

    # 运行
    msg = Message(role="user", content="介绍一下 Loom Agent")
    response = await agent.run(msg)
    print(response.content)

asyncio.run(main())
```

### 5分钟进阶：带工具的 Agent

```python
import loom, Message, tool
from examples.integrations.openai_llm import OpenAILLM  # 从 examples 导入

@tool(name="calculator")
async def calculator(expression: str) -> float:
    """计算数学表达式"""
    return eval(expression)

@tool(name="get_weather")
async def get_weather(city: str) -> str:
    """获取城市天气"""
    return f"{city} 的天气是晴天，22°C"

agent = loom.agent(
    name="assistant",
    llm=OpenAILLM(api_key="..."),
    tools=[calculator, get_weather]
)

msg = Message(role="user", content="北京天气如何？顺便算一下 123 * 456")
response = await agent.run(msg)
print(response.content)
# 输出: 北京的天气是晴天，22°C。123 * 456 = 56088
```

### 10分钟高级：启用 Skills 系统

```python
import loom, Message
from examples.integrations.openai_llm import OpenAILLM  # 从 examples 导入

agent = loom.agent(
    name="analyst",
    llm=OpenAILLM(api_key="..."),
    enable_skills=True,             # ✅ 启用 Skills
    skills_dir="./examples/skills"  # 使用示例 Skills
)

# 列出可用 Skills
skills = agent.list_skills()
for skill in skills:
    print(f"- {skill.metadata.name}: {skill.metadata.description}")

# 使用 Skills
msg = Message(role="user", content="分析这个 PDF: report.pdf")
response = await agent.run(msg)
print(response.content)
```

---

## ✨ 核心特性

### 1. 递归状态机架构 🔄

**核心理念**: `Agent = recursive function: Message → Message`

```python
class SimpleAgent:
    async def run(self, message: Message) -> Message:
        """
        递归执行直到任务完成
        """
        # 1. 调用 LLM
        response = await self.llm.generate([message])

        # 2. 如果完成，返回
        if response.finish_reason == "stop":
            return Message(role="assistant", content=response.content)

        # 3. 如果需要工具，执行工具
        tool_results = await execute_tools(response.tool_calls)

        # 4. 递归 🔥
        return await self.run(Message(
            role="user",
            content="",
            tool_results=tool_results
        ))
```

**优势**：
- 🎯 **极简**: 无需复杂的图定义
- 📊 **直观**: 执行流程清晰可见
- 🛡️ **可靠**: 自动循环检测
- 🐛 **易调试**: 执行栈清晰

---

### 2. Skills 系统 - 三层渐进式披露 🎨

**问题**: 传统方式将所有文档塞入系统提示，上下文爆炸

**解决方案**: Skills 采用**三层渐进式披露**，最小化上下文使用

```
第一层（索引）→ 系统提示，~50 tokens/skill
第二层（详细文档）→ SKILL.md，按需加载，~500-2000 tokens
第三层（资源文件）→ resources/，按需访问，任意大小
```

**效果**：
```python
# 传统方式: 3 个能力 = 3000+ tokens in 系统提示
agent = loom.agent(
    name="agent",
    llm=llm,
    system_prompt="""
    你是助手。

    # PDF 分析
    使用 PyPDF2 提取文本...（1000+ tokens）

    # Web 研究
    使用 requests 抓取...（1000+ tokens）

    # 数据处理
    使用 pandas 处理...（1000+ tokens）
    """
)

# ✅ Skills 方式: 3 个能力 = ~150 tokens in 系统提示
agent = loom.agent(
    name="agent",
    llm=llm,
    enable_skills=True  # 索引 ~50 tokens/skill = 150 tokens
)
# Agent 需要时自动读取详细文档（按需）
```

**内置 Skills**：
- 📄 **pdf_analyzer**: PDF 文档分析与提取
- 🌐 **web_research**: Web 研究和信息收集
- 📊 **data_processor**: 结构化数据处理

**创建自定义 Skill**：
```python
agent.create_skill(
    name="my_skill",
    description="自定义能力",
    category="tools",
    quick_guide="快速使用指南",
    detailed_content="""# My Skill

    完整文档...
    """
)
```

---

### 3. 完整事件系统 + Token 统计 📊

**实时监控** Agent 执行的每一步：

```python
from loom.core.events import AgentEventType

def event_handler(event):
    if event.type == AgentEventType.LLM_START:
        print("🤖 LLM 调用开始")
    elif event.type == AgentEventType.LLM_END:
        data = event.data
        print(f"✅ LLM 完成: {data['tokens_input']} + {data['tokens_output']} tokens")
        print(f"💰 成本: ${data['cost']:.4f}")
    elif event.type == AgentEventType.TOOL_START:
        print(f"🔧 工具调用: {event.data['tool_name']}")

agent = loom.agent(
    name="monitored-agent",
    llm=OpenAILLM(api_key="..."),
    tools=[...],
    event_handler=event_handler
)

msg = Message(role="user", content="...")
response = await agent.run(msg)

# 查看完整统计
stats = agent.get_stats()
print(f"LLM 调用: {stats['executor_stats']['total_llm_calls']}")
print(f"工具调用: {stats['executor_stats']['total_tool_calls']}")
print(f"Token 总数: {stats['executor_stats']['total_tokens_input'] + stats['executor_stats']['total_tokens_output']}")
print(f"总成本: ${stats['executor_stats']['total_cost']:.2f}")
```

**支持的事件类型**：
- `AGENT_START` / `AGENT_END` / `AGENT_ERROR`
- `LLM_START` / `LLM_END` / `LLM_ERROR`
- `TOOL_START` / `TOOL_END` / `TOOL_ERROR`
- `CONTEXT_UPDATE` / `CONTEXT_COMPRESS`

---

### 4. 工具并行执行 - 3x 性能提升 ⚡

```python
@tool()
async def search_paper1() -> str:
    await asyncio.sleep(1)  # 模拟 API 调用
    return "Paper 1 content"

@tool()
async def search_paper2() -> str:
    await asyncio.sleep(1)
    return "Paper 2 content"

@tool()
async def search_paper3() -> str:
    await asyncio.sleep(1)
    return "Paper 3 content"

agent = loom.agent(
    name="researcher",
    llm=llm,
    tools=[search_paper1, search_paper2, search_paper3]
)

# LLM 调用 3 个工具 → 自动并行执行 → 1 秒完成（而非 3 秒）
msg = Message(role="user", content="搜索 3 篇论文")
response = await agent.run(msg)
```

**性能对比**：
- 串行执行: 3 个工具 × 1秒 = **3 秒**
- 并行执行: 3 个工具 || = **1 秒** ✅ **3x 提升**

---

## 🤝 多 Agent 协作 (Crew)

### 三种协作模式

#### 1. Sequential - 顺序执行

```python
import loom
from examples.integrations.openai_llm import OpenAILLM  # 从 examples 导入
from loom.patterns import Crew

llm = OpenAILLM(api_key="...")

researcher = loom.agent(
    name="researcher",
    llm=llm,
    system_prompt="你是研究员，负责收集信息"
)

writer = loom.agent(
    name="writer",
    llm=llm,
    system_prompt="你是撰写员，负责整理成文章"
)

crew = Crew(agents=[researcher, writer], mode="sequential")
result = await crew.run("写一篇关于 AI Agent 的文章")
print(result)
```

#### 2. Parallel - 并行执行

```python
crew = Crew(
    agents=[agent1, agent2, agent3],
    mode="parallel",
    enable_parallel=True
)
result = await crew.run("从 3 个来源同时研究这个主题")
```

#### 3. Coordinated - 智能协调

```python
from loom.patterns import Crew, SmartCoordinator

crew = Crew(
    agents=[agent1, agent2, agent3],
    mode="coordinated",
    coordinator=SmartCoordinator(llm=llm),
    use_smart_coordinator=True
)

# SmartCoordinator 会：
# 1. 分析任务复杂度
# 2. 分解为子任务
# 3. 智能分配给 Agents
# 4. 协调执行顺序
result = await crew.run("复杂的多步骤任务")
```

---

### v0.1.6 Crew 增强功能

#### 智能协调 (SmartCoordinator)

```python
from loom.patterns import SmartCoordinator

coordinator = SmartCoordinator(llm=llm)

# 自动分析任务复杂度
complexity = coordinator.analyze_complexity("复杂任务")
print(f"复杂度得分: {complexity.score}")  # 0-1
print(f"推荐策略: {complexity.recommendation}")

# 智能分解为子任务
subtasks = coordinator.decompose_task("大型任务")
for subtask in subtasks:
    print(f"- {subtask.description} → {subtask.assigned_to}")
```

#### 并行执行 (ParallelExecutor)

```python
from loom.patterns import ParallelConfig

crew = Crew(
    agents=[agent1, agent2, agent3],
    enable_parallel=True,
    parallel_config=ParallelConfig(
        max_concurrent_agents=2,    # 最多 2 个 Agent 并行
        max_concurrent_tools=5      # 每个 Agent 最多 5 个工具并行
    )
)

# 双层并行:
# - Agent 级: 2 个 Agent 同时执行
# - Tool 级: 每个 Agent 的 5 个工具并行
```

#### 容错恢复 (ErrorRecovery)

```python
from loom.patterns import RecoveryConfig

crew = Crew(
    agents=[agent1, agent2],
    enable_error_recovery=True,
    recovery_config=RecoveryConfig(
        max_retries=3,              # 最多重试 3 次
        backoff_factor=2.0,         # 指数退避
        enable_fallback=True,       # 启用降级
        enable_partial_success=True # 允许部分成功
    )
)

# 四层容错策略:
# 1. 重试: 自动重试失败的操作
# 2. 降级: 使用更简单的策略
# 3. 部分成功: 接受部分结果
# 4. 优雅失败: 返回有意义的错误信息
```

#### 可观测性 (Tracer & Evaluator)

```python
from loom.patterns import CrewTracer, CrewEvaluator

crew = Crew(
    agents=[agent1, agent2],
    enable_tracing=True,
    tracer=CrewTracer(),
    evaluator=CrewEvaluator(llm=llm)
)

result = await crew.run("任务")

# 查看追踪
trace = crew.tracer.get_trace()
print(f"执行时间: {trace['duration']:.2f}s")
print(f"使用的 Agents: {trace['agents_used']}")

# 查看评估
evaluation = crew.evaluator.get_last_evaluation()
print(f"质量分数: {evaluation['quality_score']}")
print(f"评价: {evaluation['feedback']}")
```

#### 预设配置 (CrewPresets)

```python
from loom.patterns import CrewPresets

# 生产就绪配置（完整功能）
prod_crew = CrewPresets.production_ready(
    agents=[agent1, agent2],
    llm=llm
)

# 快速原型配置（最简单）
dev_crew = CrewPresets.fast_prototype(
    agents=[agent1, agent2]
)

# 高可靠性配置（强化容错）
reliable_crew = CrewPresets.high_reliability(
    agents=[agent1, agent2],
    llm=llm
)
```

---

## 🔌 工具系统

### 使用 @tool 装饰器

```python
from loom.builtin import tool
from typing import List

@tool(name="search")
async def search(query: str, max_results: int = 10) -> List[dict]:
    """
    搜索信息

    Args:
        query: 搜索查询
        max_results: 最大结果数

    Returns:
        搜索结果列表
    """
    # 实现...
    return results

# 使用
agent = loom.agent(
    name="agent",
    llm=llm,
    tools=[search]
)
```

### 错误处理

```python
from loom.core.errors import ToolError

@tool()
async def divide(a: float, b: float) -> float:
    """除法运算"""
    if b == 0:
        raise ToolError("除数不能为零")
    return a / b
```

---

## 📊 与其他框架对比

### vs LangGraph

| 特性 | LangGraph | Loom Agent |
|------|-----------|------------|
| **核心抽象** | 图（节点+边） | Message → Message |
| **学习曲线** | 陡峭 | 平缓 |
| **代码量** | 需要显式连线 | 极简 |
| **Skills 系统** | ❌ | ✅ |
| **并行执行** | 基础 | ✅ Agent + Tool 双层 |
| **容错** | 基础 | ✅ 四层策略 |

### vs AutoGen / CrewAI

| 特性 | AutoGen | CrewAI | Loom Agent |
|------|---------|--------|------------|
| **多 Agent** | ✅ | ✅ | ✅ |
| **智能协调** | ❌ | 基础 | ✅ SmartCoordinator |
| **并行执行** | 基础 | ❌ | ✅ 双层并行 |
| **容错恢复** | ❌ | ❌ | ✅ 四层策略 |
| **Skills 系统** | ❌ | ❌ | ✅ |
| **代码复杂度** | 高 | 中 | 低 |

**总结**: Loom Agent = **简单易用** + **功能最全** + **性能最优**

---

## 📚 文档

### 快速开始
- [5分钟快速开始](docs/getting-started/quickstart.md)
- [创建第一个 Agent](docs/getting-started/first-agent.md)
- [安装指南](docs/getting-started/installation.md)
- [API 快速参考](docs/getting-started/quick-reference.md)

### 使用指南
- [SimpleAgent 完整指南](docs/guides/agents/simple-agent.md)
- [Crew 多 Agent 协作](docs/guides/patterns/crew.md)
- [工具开发指南](docs/guides/tools/development.md)
- [Skills 系统概述](docs/guides/skills/overview.md)
- [创建 Skills](docs/guides/skills/creating-skills.md)
- [内置 Skills](docs/guides/skills/builtin-skills.md)

### API 参考
- [Agents API](docs/api/agents.md)
- [Patterns API](docs/api/patterns.md)
- [Core API](docs/api/core.md)
- [Tools API](docs/api/tools.md)

### 架构
- [架构概述](docs/architecture/overview.md)
- [故障排除](docs/architecture/troubleshooting.md)

---

## 🎯 使用场景

### 1. 简单对话 Agent

```python
agent = loom.agent(
    name="assistant",
    llm=OpenAILLM(api_key="...")
)
response = await agent.run(Message(role="user", content="Hello"))
```

### 2. 带工具的 Agent

```python
@tool()
async def search(query: str) -> str:
    return f"Results for {query}"

agent = loom.agent(
    name="agent",
    llm=llm,
    tools=[search, calculator, ...]
)
```

### 3. 多 Agent 协作

```python
crew = Crew(
    agents=[researcher, analyst, writer],
    mode="sequential"
)
result = await crew.run("写一篇研究报告")
```

### 4. Skills 增强 Agent

```python
agent = loom.agent(
    name="analyst",
    llm=llm,
    enable_skills=True  # 自动加载 pdf_analyzer, web_research, data_processor
)
```

---

## 🗺️ Roadmap

### ✅ v0.1.7 (当前)
- ✅ `loom.agent()` 工厂函数 API
- ✅ ReAct 模式开关 (`react_mode`)
- ✅ 递归控制模式（基于吴恩达四大范式）
  - ReflectionLoop（反思循环）
  - TreeOfThoughts（思维树）
  - PlanExecutor（规划执行）
  - SelfConsistency（自洽性检查）
- ✅ 完整文档（RECURSIVE_CONTROL_GUIDE.md, REACT_MODE_GUIDE.md）

### ✅ v0.1.6
- ✅ Agent 核心实现
- ✅ Crew 多 Agent 协作
- ✅ SmartCoordinator 智能协调
- ✅ ParallelExecutor 并行执行
- ✅ ErrorRecovery 容错恢复
- ✅ Skills 系统（三层渐进式披露）
- ✅ 完整事件系统
- ✅ Token 统计和成本分析
- ✅ 工具并行执行（3x 提升）

### 🔜 v0.2.0 (计划中)
- 📊 Web UI Dashboard
- 🎨 可视化执行流程
- 🧪 更多内置工具
- 📈 性能基准测试
- 🌐 分布式执行
- 💾 多后端存储

### 🎯 v0.3.0 (未来)
- 🔌 更多 LLM 提供商
- 🌍 多语言支持
- 🔐 企业级安全
- 📱 移动端支持

---

## 💡 最佳实践

### 1. 使用类型提示

```python
import loom, Message

agent: SimpleAgent = loom.agent(...)
message: Message = Message(...)
```

### 2. 错误处理

```python
from loom.core.errors import AgentError, ToolError, LLMError

try:
    response = await agent.run(message)
except ToolError as e:
    print(f"工具错误: {e}")
except LLMError as e:
    print(f"LLM 错误: {e}")
except AgentError as e:
    print(f"Agent 错误: {e}")
```

### 3. 监控统计

```python
# 添加事件处理
agent = loom.agent(
    name="agent",
    llm=llm,
    event_handler=lambda e: print(f"Event: {e.type}")
)

# 查看统计
stats = agent.get_stats()
print(f"Token 使用: {stats['executor_stats']['total_tokens_input']}")
```

### 4. 合理使用 Skills

```python
# ✅ 推荐: 按需启用
agent = loom.agent(
    name="agent",
    llm=llm,
    enable_skills=True
)

# 禁用不需要的 Skills
agent.disable_skill("web_research")
```

---

## 🧪 测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/unit/ -v
pytest tests/integration/ -v

# 覆盖率
pytest --cov=loom --cov-report=html
```

---

## 🙏 致谢

- **Anthropic Claude** - 优秀的 LLM 服务
- **OpenAI** - GPT 系列模型
- **LangChain** - 工具生态参考
- **LangGraph** - 架构参考
- **CrewAI** - 多 Agent 协作参考
- 早期用户和贡献者

---

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE)

---

## 🔗 链接

- **GitHub**: https://github.com/kongusen/loom-agent
- **PyPI**: https://pypi.org/project/loom-agent/
- **文档**: [docs/](docs/)
- **Issues**: https://github.com/kongusen/loom-agent/issues
- **Discussions**: https://github.com/kongusen/loom-agent/discussions

---

<div align="center">

**使用 ❤️ 构建，为简单而强大的 AI Agents**

### 🎬 v0.1.6 核心特性

**SimpleAgent** | **Crew 协作** | **Skills 系统** | **并行执行** | **容错恢复** | **完整可观测性**

---

### ⭐ 如果 Loom Agent 对您有帮助，请给我们一个星标！

[⭐ Star on GitHub](https://github.com/kongusen/loom-agent)

---

**v0.1.7 新特性**: 递归控制模式 - [RECURSIVE_CONTROL_GUIDE.md](RECURSIVE_CONTROL_GUIDE.md) | ReAct 模式 - [REACT_MODE_GUIDE.md](REACT_MODE_GUIDE.md)

**现在就开始**: [5分钟快速开始](docs/getting-started/quickstart.md) 🚀

</div>
