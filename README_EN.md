# 🧵 Loom Agent

<div align="center">

**The Controlled Fractal AI Agent Framework**
**Protocol-First • Metabolic Memory • Fractal Nodes**

[![PyPI](https://img.shields.io/pypi/v/loom-agent.svg)](https://pypi.org/project/loom-agent/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: Apache 2.0 + Commons Clause](https://img.shields.io/badge/License-Apache_2.0_with_Commons_Clause-red.svg)](LICENSE)

**English** | [中文](README.md)

[📖 Documentation](docs/index.md) | [🚀 Quickstart](docs/01_getting_started/quickstart.md) | [🧩 Concepts](docs/02_core_concepts/index.md)

</div>

---

## 🎯 What is Loom?

Loom is a **High-Assurance** AI Agent framework designed for building production-grade systems. Unlike frameworks focused on "rapid prototyping," Loom focuses on **Control, Persistence, and Scalability**.

### Core Features (v0.3.0)

1.  **🧬 Controlled Fractal Architecture**:
    *   Agent, Tool, and Crew are all **Nodes**. Nodes can recursively contain other nodes.
    *   Complex swarms expose simple function-like interfaces.

2.  **🧠 Metabolic Memory**:
    *   Rejects infinite context windows. Loom mimics biological metabolism: **Ingest (Validate) -> Digest (Sanitize) -> Assimilate (PSO)**.
    *   Keeps agents sharp and focused over long-running sessions.

3.  **🛡️ Protocol-First Design**:
    *   Built on Python `typing.Protocol`.
    *   Zero core dependencies: Swap LLM Providers (OpenAI/Anthropic) or Transports (Memory/Redis) easily.

4.  **⚡ Universal Event Bus**:
    *   Based on CloudEvents standard.
    *   Supports full-stack Tracing and Auditing.

---

## 📦 Installation

```bash
pip install loom-agent
```

## 🚀 Quickstart

```python
import asyncio
from loom.api.main import LoomApp
from loom.node.agent import AgentNode

async def main():
    app = LoomApp()
    
    # 1. Create Agent
    agent = AgentNode(
        node_id="helper",
        dispatcher=app.dispatcher,
        role="Assistant",
        system_prompt="You are a helpful AI."
    )
    app.add_node(agent)
    
    # 2. Run
    response = await app.run("Hello Loom!", target="helper")
    print(response['response'])

if __name__ == "__main__":
    asyncio.run(main())
```

> **Note**: Loom uses a Mock LLM by default for testing. To use real models, see [Examples](docs/08_examples/index.md).

## 📚 Documentation

We provide comprehensive documentation:

*   **[User Guide](docs/index.md)**
    *   [Installation](docs/01_getting_started/installation.md)
    *   [Building Agents](docs/03_guides/building_agents.md)
*   **[Core Concepts](docs/02_core_concepts/index.md)**
    *   [Metabolic Memory](docs/02_core_concepts/memory_system.md)
    *   [Design Philosophy](docs/05_design_philosophy/index.md)

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md).

## 📄 License

**Apache License 2.0 with Commons Clause**.

Free for academic research, personal use, and internal commercial use.
**Commercial sale is strictly prohibited** (including but not limited to paid packaging, hosting services, etc.) without authorization.
See [LICENSE](LICENSE) for details.
