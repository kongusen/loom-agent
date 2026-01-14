<div align="center">

<img src="loom.svg" alt="Loom Agent" width="300"/>


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

### Core Features (v0.3.7)

1.  **🧬 Controlled Fractal Architecture**:
    *   Agent, Tool, and Crew are all **Nodes**. Nodes can recursively contain other nodes.
    *   Complex swarms expose simple function-like interfaces.

2.  **🎯 Cognitive Dynamics System**:
    *   **Dual-System Thinking**: Intelligent collaboration between System 1 (fast intuition) and System 2 (deep reasoning).
    *   **Confidence Assessment**: System 1 automatically falls back to System 2 on low confidence responses.
    *   **Unified Configuration**: Manage cognitive, context, and memory configurations through `CognitiveConfig`.
    *   **Preset Modes**: Three out-of-the-box configuration modes: fast/balanced/deep.

3.  **🧠 Composite Memory System**:
    *   **L1-L4 Hierarchy**: From ephemeral reaction (L1) to semantic knowledge (L4).
    *   **Multiple Vector Stores**: Support for Qdrant, Chroma, PostgreSQL (pgvector), and more vector database backends.
    *   **BGE Embedding**: Integrated ONNX-optimized BGE model for high-performance semantic retrieval.
    *   **Smart Compression**: L4 knowledge base automatically clusters and compresses to maintain optimal size (<150 facts).
    *   **Memory Metabolism**: Automated `Ingest` -> `Digest` -> `Assimilate` consolidation loop.
    *   **Context Projection**: Smart projection of parent Agent context to child Agents with 5 projection modes.

4.  **🛡️ Protocol-First & Recursion**:
    *   **Infinite Recursion**: Agents can delegate tasks to other nodes recursively with no depth limit.
    *   **Unified Execution**: `FractalOrchestrator` unifies tool execution and sub-agent orchestration.
    *   **Standard Contracts**: All interactions defined by CloudEvents and MCP.

5.  **⚡ Universal Event Bus**:
    *   Based on CloudEvents standard.
    *   Supports full-stack Tracing and Auditing.

6.  **🌐 Multi-LLM Support**:
    *   **10+ Providers**: OpenAI, Anthropic, Gemini, DeepSeek, Qwen, Kimi, Doubao, and more.
    *   **Unified Interface**: Consistent API design for easy model switching.
    *   **Streaming Output**: Native support for streaming responses and structured output.

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
