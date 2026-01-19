<div align="center">

<img src="loom.svg" alt="Loom Agent" width="300"/>


**受控分形架构的 AI Agent 框架**
**Protocol-First • Metabolic Memory • Fractal Nodes**

[![PyPI](https://img.shields.io/pypi/v/loom-agent.svg)](https://pypi.org/project/loom-agent/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: Apache 2.0 + Commons Clause](https://img.shields.io/badge/License-Apache_2.0_with_Commons_Clause-red.svg)](LICENSE)

[English](README_EN.md) | **中文**

[📖 文档索引](docs/README.md) | [🧩 公理框架](docs/concepts/axiomatic-framework.md) | [🚀 快速开始](docs/usage/getting-started.md)

</div>

---

## 🎯 什么是 Loom?

Loom 是一个**高可靠 (High-Assurance)** 的 AI Agent 框架，专为构建**认知生命体 (Cognitive Organisms)** 而设计。与其他专注于"快速原型"的框架不同，Loom 从**公理系统 (Axiomatic Framework)** 出发，通过**分形架构 (Fractal Architecture)** 和**代谢记忆 (Metabolic Memory)** 对抗认知熵增，实现无限复杂度和无限时间的可靠运行。

### 核心特性 (v0.4.0-alpha)

1.  **🧩 公理系统 (Axiomatic Framework)**:
    *   从 5 个基础公理出发，构建形式化的理论框架。
    *   **公理 A1**：统一接口公理 - 所有节点实现 `NodeProtocol`。
    *   **公理 A2**：事件主权公理 - 所有通信通过标准化任务模型。
    *   **公理 A3**：分形组合公理 - 节点可以递归组合，复杂度保持 O(1)。
    *   **公理 A4**：记忆代谢公理 - 信息通过代谢转化为知识。
    *   **公理 A5**：认知涌现公理 - 认知是编排交互的涌现属性。

2.  **🧬 分形架构 (Fractal Architecture)**:
    *   **无限递归**：Agent、Tool、Crew 都是节点，可无限嵌套。
    *   **复杂度守恒**：任意层级的局部上下文复杂度恒定为 O(1)。
    *   **统一接口**：所有节点通过 `NodeProtocol` 通信，实现接口透明性。
    *   **对抗空间熵增**：通过递归封装实现无限语义深度。

3.  **🧠 代谢记忆系统 (Metabolic Memory)**:
    *   **L1-L4 分层存储**：从瞬间反应到语义知识的完整记忆谱系。
    *   **记忆代谢**：`Ingest` -> `Digest` -> `Assimilate` 自动巩固流程。
    *   **智能压缩**：L4 知识库自动聚类压缩，保持最优规模。
    *   **对抗时间熵增**：将流动的经验转化为固定的知识。
    *   **多种向量存储**：支持 Qdrant、Chroma、PostgreSQL (pgvector)。

4.  **🎯 FastAPI 风格 API (FastAPI-Style API)**:
    *   **类型安全**：基于 Pydantic 的配置模型，自动验证。
    *   **简洁优雅**：`LoomApp` + `AgentConfig` 快速创建 Agent。
    *   **统一管理**：集中管理事件总线、调度器和 LLM 提供商。

5.  **🛡️ 协议优先 (Protocol-First)**:
    *   **标准契约**：基于 Google A2A 协议和 SSE 传输。
    *   **事件驱动**：所有通信通过标准化的任务模型。
    *   **可观测性**：支持全链路追踪和审计。

6.  **🌐 多 LLM 支持 (Multi-LLM Support)**:
    *   **10+ 提供商**：OpenAI、Anthropic、Gemini、DeepSeek、Qwen、Kimi、Doubao 等。
    *   **统一接口**：一致的 API 设计，轻松切换不同模型。
    *   **流式输出**：原生支持流式响应和结构化输出。

---

## 📦 安装

```bash
pip install loom-agent
```

## 🚀 快速上手

### 基础使用

使用 FastAPI 风格的 API 创建 Agent：

```python
from loom.api import LoomApp, AgentConfig
from loom.providers.llm import OpenAIProvider

# 1. 创建应用
app = LoomApp()

# 2. 配置 LLM Provider
llm = OpenAIProvider(api_key="your-api-key")
app.set_llm_provider(llm)

# 3. 创建 Agent（使用 Pydantic 配置）
config = AgentConfig(
    agent_id="assistant",
    name="我的助手",
    system_prompt="你是一个友好的 AI 助手",
    capabilities=["tool_use", "reflection"],
    max_iterations=10,
)

agent = app.create_agent(config)
print(f"Agent 创建成功: {agent.node_id}")
```

### 创建多个 Agent

```python
from loom.api import LoomApp, AgentConfig

app = LoomApp()
app.set_llm_provider(llm)

# 创建多个 Agent（共享事件总线和调度器）
agent1 = app.create_agent(AgentConfig(
    agent_id="chatbot",
    name="聊天机器人",
    system_prompt="你是一个友好的对话助手",
))

agent2 = app.create_agent(AgentConfig(
    agent_id="analyst",
    name="数据分析师",
    system_prompt="你是一个专业的数据分析专家",
))

# 列出所有 Agent
print(f"已创建 {len(app.list_agents())} 个 Agent")
```

> **注意**: 要接入真实 LLM（如 OpenAI/Claude），请参阅[快速开始文档](docs/usage/getting-started.md)。

## 📚 文档索引

完整的文档体系，从理论到实践：

### 核心概念
*   **[文档主页](docs/README.md)**: 文档导航入口
*   **[公理框架](docs/concepts/axiomatic-framework.md)**: 5 个基础公理与理论基础

### 快速上手
*   **[快速开始](docs/usage/getting-started.md)**: 5 分钟上手指南
*   **[API 参考](docs/usage/api-reference.md)**: 完整的 API 文档

### 框架架构
*   **[分形架构](docs/framework/fractal-architecture.md)**: 对抗空间熵增的核心设计
*   **[上下文管理](docs/framework/context-management.md)**: 智能上下文构建与优化
*   **[事件总线](docs/framework/event-bus.md)**: 事件驱动的神经系统

### 核心功能
*   **[记忆系统](docs/features/memory-system.md)**: L1-L4 代谢记忆机制
*   **[工具系统](docs/features/tool-system.md)**: 工具集成与执行
*   **[编排模式](docs/features/orchestration.md)**: 多 Agent 协作模式
*   **[搜索检索](docs/features/search-and-retrieval.md)**: 语义搜索与知识检索

### 设计模式
*   **[解决复杂性](docs/patterns/solving-complexity.md)**: 如何分解"不可能的任务"

## 🤝 贡献

欢迎提交 PR 或 Issue！查看 [CONTRIBUTING.md](CONTRIBUTING.md) 了解更多。

## 📄 许可证

**Apache License 2.0 with Commons Clause**.

本软件允许免费用于学术研究、个人学习和内部商业使用。
**严禁未经授权的商业销售**（包括但不限于将本软件打包收费、提供托管服务等）。
详情请见 [LICENSE](LICENSE)。
