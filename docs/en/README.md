<div align="center">

<img src="../../loom.svg" alt="Loom Agent" width="300"/>

**AI Agent Framework with Controlled Fractal Architecture**
**Protocol-First • Metabolic Memory • Fractal Nodes**

[![PyPI](https://img.shields.io/pypi/v/loom-agent.svg)](https://pypi.org/project/loom-agent/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: Apache 2.0 + Commons Clause](https://img.shields.io/badge/License-Apache_2.0_with_Commons_Clause-red.svg)](../../LICENSE)

**English** | [中文](../../README.md)

[📖 Documentation](README.md) | [🚀 Quick Start](getting-started/quickstart.md) | [🧩 Core Concepts](concepts/architecture.md)

</div>

---

## 🎯 What is Loom?

Loom is a **High-Assurance** AI Agent framework designed for building production-grade systems. Unlike frameworks focused on "rapid prototyping", Loom prioritizes **Control, Persistence, and Fractal Scalability**.

### Core Features (v0.3.x)

1.  **🧬 Controlled Fractal Architecture**:
    *   Agents, Tools, and Crews are all **Nodes**. Nodes can contain other nodes recursively.
    *   Even the most complex Agent cluster behaves like a simple function call externally.

2.  **🧠 Metabolic Memory**:
    *   Rejects infinite context window appending. Loom simulates biological metabolism: **Ingest (Validate) -> Digest (Sanitize) -> Assimilate (PSO)**.
    *   Keeps the Agent's "mind" clear over long periods, preventing context poisoning.

3.  **🛡️ Protocol-First**:
    *   Behavior contracts defined via Python `typing.Protocol`.
    *   Zero-dependency core: Easily swap LLM Providers (OpenAI/Anthropic) or Transport layers (Memory/Redis).

4.  **⚡ Universal Event Bus**:
    *   Based on CloudEvents standard.
    *   Supports full-chain Tracing and Auditing.

---

## 📦 Installation

```bash
pip install loom-agent
```

## 🚀 Quick Start

Get started in 5 minutes using the `loom.weave` API:

```python
import asyncio
from loom.weave import create_agent, run

# 1. Create an Agent
agent = create_agent("Assistant", role="General Assistant")

# 2. Run a task
result = run(agent, "Hello, please introduce yourself")
print(result)
```

> **Note**: Loom uses a Mock LLM by default for easy testing. To use real models (like OpenAI/Claude), please refer to the [Quick Start Guide](getting-started/quickstart.md).

---

## 📚 Documentation Navigation

This documentation is organized based on the [Diátaxis](https://diataxis.fr/) framework:

### 📖 [Tutorials](tutorials/)
**Learning-oriented** - Learn loom-agent step by step
- [Create Your First Agent](tutorials/your-first-agent.md)
- [Add Skills to Agent](tutorials/adding-skills.md)
- [Build Agent Teams](tutorials/building-teams.md)
- [Use YAML Configuration](tutorials/yaml-configuration.md)

### 🛠️ [How-to Guides](guides/)
**Problem-oriented** - Solve specific problems
- [Agents](guides/agents/) - Create and configure Agents
- [Skills](guides/skills/) - Develop custom skills
- [Configuration](guides/configuration/) - Configuration and deployment
- [Deployment](guides/deployment/) - Production deployment

### 💡 [Concepts](concepts/)
**Understanding-oriented** - Deep dive into core concepts
- [Architecture Design](concepts/architecture.md)
- [Cognitive Dynamics](concepts/cognitive-dynamics.md)
- [Design Philosophy](concepts/design-philosophy.md)

### 📚 [Reference](reference/)
**Information-oriented** - Complete API documentation
- [loom.weave API](reference/api/weave.md)
- [loom.stdlib API](reference/api/stdlib.md)
- [Configuration Reference](reference/api/config.md)

---

## 🤝 Contributing

We welcome Pull Requests and Issues! See [CONTRIBUTING.md](../../CONTRIBUTING.md) for more details.

## 📄 License

**Apache License 2.0 with Commons Clause**.

This software is free for academic research, personal learning, and internal commercial use.
**Unauthorized commercial sale is strictly prohibited** (including but not limited to bundling this software for a fee or providing managed services).
See [LICENSE](../../LICENSE) for details.
