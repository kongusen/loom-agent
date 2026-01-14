<div align="center">

<img src="loom.svg" alt="Loom Agent" width="300"/>


**受控分形架构的 AI Agent 框架**
**Protocol-First • Metabolic Memory • Fractal Nodes**

[![PyPI](https://img.shields.io/pypi/v/loom-agent.svg)](https://pypi.org/project/loom-agent/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: Apache 2.0 + Commons Clause](https://img.shields.io/badge/License-Apache_2.0_with_Commons_Clause-red.svg)](LICENSE)

[English](docs/en/README.md) | **中文**

[📖 文档](docs/README.md) | [🚀 快速开始](docs/getting-started/quickstart.md) | [🧩 核心概念](docs/concepts/architecture.md)

</div>

---

## 🎯 什么是 Loom?

Loom 是一个**高可靠 (High-Assurance)** 的 AI Agent 框架，专为构建生产级系统而设计。与其他专注于"快速原型"的框架不同，Loom 关注**控制 (Control)、持久化 (Persistence) 和分形扩展 (Fractal Scalability)**。

### 核心特性 (v0.3.7)

1.  **🧬 受控分形架构 (Controlled Fractal)**:
    *   Agent、Tool、Crew 都是**节点 (Node)**。节点可以无限递归包含。
    *   即便是最复杂的 Agent 集群，对外也表现为一个简单的函数调用。

2.  **🎯 认知动力学系统 (Cognitive Dynamics)**:
    *   **双系统思维**：System 1（快速直觉）与 System 2（深度推理）的智能协作。
    *   **置信度评估**：System 1 响应低置信度时自动回退到 System 2。
    *   **统一配置**：通过 `CognitiveConfig` 统一管理认知、上下文和记忆配置。
    *   **预设模式**：fast/balanced/deep 三种开箱即用的配置模式。

3.  **🧠 复合记忆系统 (Composite Memory)**:
    *   **L1-L4 分层存储**：从瞬间反应(L1)到语义知识(L4)的完整记忆谱系。
    *   **多种向量存储**：支持 Qdrant、Chroma、PostgreSQL (pgvector) 等多种向量数据库后端。
    *   **BGE Embedding**：集成 ONNX 优化的 BGE 模型，支持高性能语义检索。
    *   **智能压缩**：L4 知识库自动聚类压缩，保持最优规模（<150 facts）。
    *   **记忆代谢**：自动化的 `Ingest` -> `Digest` -> `Assimilate` 记忆巩固流程。
    *   **上下文投影**：智能投影父 Agent 上下文到子 Agent，支持 5 种投影模式。

4.  **🎨 模式系统 (Pattern System)**:
    *   **5 种内置模式**：Analytical、Creative、Collaborative、Iterative、Execution。
    *   **配置组合**：每种模式预设最佳的认知、记忆和执行配置。
    *   **灵活扩展**：支持自定义模式以适应特定场景。

5.  **🛡️ 协议优先与递归 (Protocol-First & Recursion)**:
    *   **无限递归**：基于统一协议，支持无限层级的子任务代理（Delegation）。
    *   **统一执行**：`FractalOrchestrator` 统一了工具调用和子 Agent 编排。
    *   **标准契约**：基于 CloudEvents 和 MCP 定义所有交互。

6.  **⚡ 通用事件总线 (Universal Event Bus)**:
    *   基于 CloudEvents 标准。
    *   支持全链路追踪 (Tracing) 和 审计 (Auditing)。

7.  **🌐 多 LLM 支持 (Multi-LLM Support)**:
    *   **10+ 提供商**：OpenAI、Anthropic、Gemini、DeepSeek、Qwen、Kimi、Doubao 等。
    *   **统一接口**：一致的 API 设计，轻松切换不同模型。
    *   **流式输出**：原生支持流式响应和结构化输出。

---

## 📦 安装

```bash
pip install loom-agent
```

## 🚀 快速上手

### 基础示例

使用新的统一配置，5分钟构建你的第一个 Agent：

```python
import asyncio
from loom.kernel.core.bus import UniversalEventBus
from loom.kernel.core import Dispatcher
from loom.node.agent import AgentNode
from loom.config.cognitive import CognitiveConfig
from loom.llm import OpenAIProvider

async def main():
    # 1. 创建基础设施
    bus = UniversalEventBus()
    dispatcher = Dispatcher(bus=bus)
    provider = OpenAIProvider(api_key="your-api-key")

    # 2. 创建 Agent（使用平衡模式）
    agent = AgentNode(
        node_id="assistant",
        dispatcher=dispatcher,
        provider=provider,
        cognitive_config=CognitiveConfig.balanced_mode()
    )

    # 3. 运行任务
    from loom.protocol import CloudEvent
    event = CloudEvent(
        type="node.request",
        source="user",
        subject="assistant",
        data={"content": "你好，请介绍一下自己"}
    )
    result = await agent.process(event)
    print(result)

asyncio.run(main())
```

### 使用预设模式

```python
# 快速模式 - 适合简单对话
fast_agent = AgentNode(
    node_id="chatbot",
    dispatcher=dispatcher,
    provider=provider,
    cognitive_config=CognitiveConfig.fast_mode()
)

# 深度模式 - 适合复杂分析
deep_agent = AgentNode(
    node_id="analyst",
    dispatcher=dispatcher,
    provider=provider,
    cognitive_config=CognitiveConfig.deep_mode()
)
```

> **注意**: 默认情况下 Loom 使用 Mock LLM 方便测试。要接入真实模型（如 OpenAI/Claude），请参阅[文档](docs/getting-started/quickstart.md)。

## 📚 文档索引

我们提供了完整的双语文档：

*   **[用户指南 (中文)](docs/README.md)**
    *   [安装指南](docs/getting-started/installation.md)
    *   [快速开始](docs/getting-started/quickstart.md)
    *   [构建 Agent](docs/tutorials/01-your-first-agent.md)
*   **[English Documentation](docs/en/README.md)**
    *   [Installation](docs/en/getting-started/installation.md)
    *   [Quick Start](docs/en/getting-started/quickstart.md)
    *   [Architecture](docs/en/concepts/architecture.md)
*   **[核心概念](docs/concepts/architecture.md)**
    *   [架构设计](docs/concepts/architecture.md)
    *   [认知动力学](docs/concepts/cognitive-dynamics.md)
    *   [记忆系统](docs/concepts/memory_system.md)
    *   [双系统思维](docs/concepts/dual-system.md)
*   **[高级特性](docs/guides/memory-optimization.md)**
    *   [记忆优化](docs/guides/memory-optimization.md)
    *   [分形节点](docs/guides/fractal-nodes.md)
    *   [LLM 流式输出](docs/guides/llm-streaming.md)
    *   [结构化输出](docs/guides/structured-output.md)
*   **[技术文档](docs/)**
    *   [BGE Embedding 优化](docs/bge_embedding_optimization.md)
    *   [L4 压缩设计](docs/l4_compression_design.md)
    *   [投影策略设计](docs/projection_strategy_design.md)
    *   [投影优化分析](docs/projection_optimization_analysis.md)

## 🤝 贡献

欢迎提交 PR 或 Issue！查看 [CONTRIBUTING.md](CONTRIBUTING.md) 了解更多。

## 📄 许可证

**Apache License 2.0 with Commons Clause**.

本软件允许免费用于学术研究、个人学习和内部商业使用。
**严禁未经授权的商业销售**（包括但不限于将本软件打包收费、提供托管服务等）。
详情请见 [LICENSE](LICENSE)。
