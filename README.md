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

### 核心特性 (v0.3.x)

1.  **🧬 受控分形架构 (Controlled Fractal)**:
    *   Agent、Tool、Crew 都是**节点 (Node)**。节点可以无限递归包含。
    *   即便是最复杂的 Agent 集群，对外也表现为一个简单的函数调用。

2.  **🧠 新陈代谢记忆 (Metabolic Memory)**:
    *   拒绝无限追加的上下文窗口。Loom 模拟生物代谢：**摄入 (Validate) -> 消化 (Sanitize) -> 同化 (PSO)**。
    *   长期保持 Agent 的"思维清醒"，防止上下文中毒。

3.  **🛡️ 协议优先 (Protocol-First)**:
    *   基于 Python `typing.Protocol` 定义行为契约。
    *   零依赖核心：你可以轻松替换 LLM Provider (OpenAI/Anthropic) 或 传输层 (Memory/Redis)。

4.  **⚡ 通用事件总线 (Universal Event Bus)**:
    *   基于 CloudEvents 标准。
    *   支持全链路追踪 (Tracing) 和 审计 (Auditing)。

---

## 📦 安装

```bash
pip install loom-agent
```

## 🚀 快速上手

使用新的 `loom.weave` API，5分钟构建你的第一个 Agent：

```python
import asyncio
from loom.weave import create_agent, run

# 1. 创建 Agent
agent = create_agent("Assistant", role="General Assistant")

# 2. 运行任务
result = run(agent, "你好，请介绍一下自己")
print(result)
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
