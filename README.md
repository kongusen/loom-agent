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

### 核心特性 (v0.3.6)

1.  **🧬 受控分形架构 (Controlled Fractal)**:
    *   Agent、Tool、Crew 都是**节点 (Node)**。节点可以无限递归包含。
    *   即便是最复杂的 Agent 集群，对外也表现为一个简单的函数调用。

2.  **🎯 智能路由系统 (Intelligent Routing)**:
    *   **自动路由**：基于查询特征自动选择 System 1（快速）或 System 2（深度）。
    *   **置信度评估**：System 1 响应低置信度时自动回退到 System 2。
    *   **统一配置**：通过 `CognitiveConfig` 统一管理路由、上下文和记忆配置。
    *   **预设模式**：fast/balanced/deep 三种开箱即用的配置模式。

3.  **🧠 复合记忆系统 (Composite Memory)**:
    *   **L1-L4 分层存储**：从瞬间反应(L1)到语义知识(L4)的完整记忆谱系。
    *   **语义持久化**：集成 Qdrant 向量数据库，支持跨会话记忆和知识积累。
    *   **记忆代谢**：自动化的 `Ingest` -> `Digest` -> `Assimilate` 记忆巩固流程。
    *   **上下文压缩**：智能压缩历史记录，保留关键事实，大幅降低 Token 消耗。

4.  **🛡️ 协议优先与递归 (Protocol-First & Recursion)**:
    *   **无限递归**：基于统一协议，支持无限层级的子任务代理（Delegation）。
    *   **统一执行**：`FractalOrchestrator` 统一了工具调用和子 Agent 编排。
    *   **标准契约**：基于 CloudEvents 和 MCP 定义所有交互。

5.  **⚡ 通用事件总线 (Universal Event Bus)**:
    *   基于 CloudEvents 标准。
    *   支持全链路追踪 (Tracing) 和 审计 (Auditing)。

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
*   **[核心原理](docs/concepts/architecture.md)**
    *   [架构设计](docs/concepts/architecture.md)
    *   [认知动力学](docs/concepts/cognitive-dynamics.md)

## 🤝 贡献

欢迎提交 PR 或 Issue！查看 [CONTRIBUTING.md](CONTRIBUTING.md) 了解更多。

## 📄 许可证

**Apache License 2.0 with Commons Clause**.

本软件允许免费用于学术研究、个人学习和内部商业使用。
**严禁未经授权的商业销售**（包括但不限于将本软件打包收费、提供托管服务等）。
详情请见 [LICENSE](LICENSE)。
