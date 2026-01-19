<div align="center">

<img src="loom.svg" alt="Loom Agent" width="300"/>


**The Controlled Fractal AI Agent Framework**
**Protocol-First • Metabolic Memory • Fractal Nodes**

[![PyPI](https://img.shields.io/pypi/v/loom-agent.svg)](https://pypi.org/project/loom-agent/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: Apache 2.0 + Commons Clause](https://img.shields.io/badge/License-Apache_2.0_with_Commons_Clause-red.svg)](LICENSE)

**English** | [中文](README.md)

[📖 Documentation Index](docs/README.md) | [🧩 Axiomatic Framework](docs/concepts/axiomatic-framework.md) | [🚀 Getting Started](docs/usage/getting-started.md)

</div>

---

## 🎯 What is Loom?

Loom is a **High-Assurance** AI Agent framework designed for building **Cognitive Organisms**. Unlike frameworks focused on "rapid prototyping," Loom starts from an **Axiomatic Framework** and uses **Fractal Architecture** and **Metabolic Memory** to counter cognitive entropy, achieving reliable operation at infinite complexity and infinite time.

### Core Features (v0.4.0-alpha)

1.  **🧩 Axiomatic Framework**:
    *   Built from 5 foundational axioms to create a formal theoretical framework.
    *   **Axiom A1**: Uniform Interface - All nodes implement `NodeProtocol`.
    *   **Axiom A2**: Event Sovereignty - All communication through standardized task models.
    *   **Axiom A3**: Fractal Composition - Nodes can recursively compose, complexity remains O(1).
    *   **Axiom A4**: Memory Metabolism - Information transforms into knowledge through metabolism.
    *   **Axiom A5**: Cognitive Emergence - Cognition emerges from orchestration interactions.

2.  **🧬 Fractal Architecture**:
    *   **Infinite Recursion**: Agent, Tool, Crew are all nodes, infinitely nestable.
    *   **Complexity Conservation**: Local context complexity at any level remains constant at O(1).
    *   **Unified Interface**: All nodes communicate through `NodeProtocol`, achieving interface transparency.
    *   **Counter Spatial Entropy**: Achieve infinite semantic depth through recursive encapsulation.

3.  **🧠 Metabolic Memory System**:
    *   **L1-L4 Hierarchy**: Complete memory spectrum from ephemeral reaction to semantic knowledge.
    *   **Memory Metabolism**: Automated `Ingest` -> `Digest` -> `Assimilate` consolidation loop.
    *   **Smart Compression**: L4 knowledge base automatically clusters and compresses to maintain optimal size.
    *   **Counter Temporal Entropy**: Transform flowing experience into fixed knowledge.
    *   **Multiple Vector Stores**: Support for Qdrant, Chroma, PostgreSQL (pgvector).

4.  **🎯 FastAPI-Style API**:
    *   **Type Safety**: Pydantic-based configuration models with automatic validation.
    *   **Simple & Elegant**: `LoomApp` + `AgentConfig` for quick agent creation.
    *   **Unified Management**: Centralized management of event bus, dispatcher, and LLM providers.

5.  **🛡️ Protocol-First**:
    *   **Standard Contracts**: Based on Google A2A protocol and SSE transport.
    *   **Event-Driven**: All communication through standardized task models.
    *   **Observability**: Support for full-stack tracing and auditing.

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

> **Note**: To connect to real LLMs (like OpenAI/Claude), see [Getting Started](docs/usage/getting-started.md).

## 📚 Documentation

Complete documentation system from theory to practice:

### Core Concepts
*   **[Documentation Home](docs/README.md)**: Documentation navigation
*   **[Axiomatic Framework](docs/concepts/axiomatic-framework.md)**: 5 foundational axioms and theoretical foundation

### Getting Started
*   **[Getting Started](docs/usage/getting-started.md)**: 5-minute quickstart guide
*   **[API Reference](docs/usage/api-reference.md)**: Complete API documentation

### Framework Architecture
*   **[Fractal Architecture](docs/framework/fractal-architecture.md)**: Core design for countering spatial entropy
*   **[Context Management](docs/framework/context-management.md)**: Intelligent context building and optimization
*   **[Event Bus](docs/framework/event-bus.md)**: Event-driven nervous system

### Core Features
*   **[Memory System](docs/features/memory-system.md)**: L1-L4 metabolic memory mechanism
*   **[Tool System](docs/features/tool-system.md)**: Tool integration and execution
*   **[Orchestration](docs/features/orchestration.md)**: Multi-agent collaboration patterns
*   **[Search & Retrieval](docs/features/search-and-retrieval.md)**: Semantic search and knowledge retrieval

### Design Patterns
*   **[Solving Complexity](docs/patterns/solving-complexity.md)**: How to break down "impossible tasks"

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md).

## 📄 License

**Apache License 2.0 with Commons Clause**.

Free for academic research, personal use, and internal commercial use.
**Commercial sale is strictly prohibited** (including but not limited to paid packaging, hosting services, etc.) without authorization.
See [LICENSE](LICENSE) for details.
