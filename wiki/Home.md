# Loom v0.6.0 — 自组织多智能体框架

Loom 是一个极简的自组织多智能体（Multi-Agent）框架，采用组合优于继承的设计，通过可插拔模块构建从单 Agent 到集群协作的完整 AI 应用。

## 核心特性

| 模块 | 说明 |
|------|------|
| [Agent](Agent) | 核心执行循环，组合 provider + memory + tools + context |
| [Tools](Tools) | 工具注册与 LLM 自主调用 |
| [Events](Events) | 类型化事件总线，父子传播 |
| [Interceptors](Interceptors) | 中间件管道，LLM 调用前注入/变换 |
| [Memory](Memory) | 三层记忆：L1 滑动窗口 / L2 工作记忆 / L3 持久化 |
| [Knowledge](Knowledge) | RAG 知识库：文档摄入 + 混合检索 |
| [Context](Context) | 上下文编排器，自动注入知识到 LLM |
| [Skills](Skills) | 技能系统，关键词/模式触发自动激活 |
| [Cluster](Cluster) | 集群拍卖，能力评分竞标选择最佳 Agent |
| [Providers](Providers) | 弹性 LLM 提供者：重试 + 熔断器 |
| [Runtime](Runtime) | 运行时编排 + AmoebaLoop 自组织循环 |
| [Architecture](Architecture) | 全栈架构：多 Agent 委派 + 完整流水线 |

## 快速开始

### 安装

```bash
pip install loom-agent
```

### 环境配置

```bash
# .env
OPENAI_API_KEY=sk-xxx
OPENAI_MODEL=gpt-4o-mini
OPENAI_BASE_URL=https://api.openai.com/v1
```

### 最小示例

```python
import asyncio
from loom import Agent, AgentConfig
from loom.providers.openai import OpenAIProvider

provider = OpenAIProvider(AgentConfig(
    api_key="sk-xxx", model="gpt-4o-mini"
))

agent = Agent(
    provider=provider,
    config=AgentConfig(system_prompt="你是助手", max_steps=3),
)

async def main():
    result = await agent.run("你好")
    print(result.content)

asyncio.run(main())
```

### 流式输出

```python
from loom import TextDeltaEvent, DoneEvent

async for event in agent.stream("你好"):
    if isinstance(event, TextDeltaEvent):
        print(event.text, end="", flush=True)
    elif isinstance(event, DoneEvent):
        print(f"\n完成, steps={event.steps}")
```

## Agent 组合模式

Loom Agent 通过组合注入各模块能力：

```python
agent = Agent(
    provider=provider,          # LLM 提供者
    config=config,              # 配置
    memory=memory,              # 记忆管理
    tools=tool_registry,        # 工具注册表
    context=context_orch,       # 上下文编排
    event_bus=bus,              # 事件总线
    interceptors=chain,         # 拦截器链
)
```

## Demo 索引

所有 demo 位于 `examples/demo/`，使用真实 OpenAI API：

```bash
PYTHONPATH=. python examples/demo/01_hello_agent.py
```

| # | Demo | 对应文档 |
|---|------|---------|
| 01 | 基础 Agent：run + stream | [Agent](Agent) |
| 02 | 工具：LLM 自主调用 | [Tools](Tools) |
| 03 | 事件总线：实时监控 | [Events](Events) |
| 04 | 拦截器：注入专家身份 | [Interceptors](Interceptors) |
| 05 | 记忆：多轮对话上下文 | [Memory](Memory) |
| 06 | 知识库：混合检索 RAG | [Knowledge](Knowledge) |
| 07 | 上下文编排：知识注入 | [Context](Context) |
| 08 | 技能：自动激活增强 | [Skills](Skills) |
| 09 | 集群拍卖：最佳选择 | [Cluster](Cluster) |
| 10 | 奖励：EMA 能力评估 | [Cluster](Cluster) |
| 11 | 弹性 Provider：重试+熔断 | [Providers](Providers) |
| 12 | Runtime：集群编排 | [Runtime](Runtime) |
| 13 | AmoebaLoop：自组织循环 | [Runtime](Runtime) |
| 14 | 多 Agent 委派 | [Architecture](Architecture) |
| 15 | 全栈流水线 | [Architecture](Architecture) |
