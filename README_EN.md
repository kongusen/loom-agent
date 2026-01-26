<div align="center">

<img src="loom.svg" alt="Loom Agent" width="300"/>

**The Controlled Fractal Agent Framework**

Protocol-First • Metabolic Memory • Fractal Nodes

[![PyPI](https://img.shields.io/pypi/v/loom-agent.svg)](https://pypi.org/project/loom-agent/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: Apache 2.0 + Commons Clause](https://img.shields.io/badge/License-Apache_2.0_with_Commons_Clause-red.svg)](LICENSE)

**English** | [中文](README.md)

[Documentation](docs/README.md) | [Axiomatic Framework](docs/concepts/axiomatic-framework.md) | [Getting Started](docs/usage/getting-started.md)

</div>

---

## Overview

Loom is a **High-Assurance** AI Agent framework designed to solve the core challenges of building complex **Cognitive Organisms**.

Unlike experimental frameworks focused on rapid prototyping, Loom is built upon a strict **Axiomatic Framework**. It addresses the infinite growth of spatial complexity through **Fractal Architecture** and counters cognitive entropy over time via **Metabolic Memory**. Loom is not designed for creating simple demos, but for building intelligent systems capable of long-term stable operation and self-evolution in production environments.

### Core Features (v0.4.2)

#### 1. Axiomatic System Design

Built on a formal theoretical framework composed of 5 foundational axioms, ensuring logical consistency and predictability. From uniform interfaces to event sovereignty, every design decision is theoretically grounded.

#### 2. Fractal Architecture & Infinite Composition

Leveraging `CompositeNode` to enable true recursive composition. Whether a single Agent or a complex collaboration team, they are consistent nodes within Loom. This architecture guarantees that the cognitive load of any local part remains constant (O(1)), regardless of system complexity.

#### 3. Metabolic Memory System

Mimicking biological cognitive mechanisms, Loom establishes a complete memory spectrum from L1 (Working Memory) to L4 (Semantic Knowledge Base). The system automatically handles the ingestion, digestion, and assimilation of information, combined with pgvector/Qdrant vector retrieval, allowing Agents to become smarter over time.

#### 4. Type-Safe Event Bus

Rejecting "magic strings" and unreliable implicit calls. Loom employs strict CloudEvents standards, Protocol-based handler definitions, and type-safe Action enums, providing industrial-grade observability and stability for distributed Agent systems.

#### 5. Modern Developer Experience

Featuring a FastAPI-style declarative API with integrated Pydantic full-link data validation. Native support for mainstream models like OpenAI, Anthropic, Gemini, DeepSeek, etc., with out-of-the-box SSE streaming output and structured responses.

---

## Installation

```bash
pip install loom-agent
```

## Quick Start

### Create Your First Agent

Loom provides a minimal declarative API:

```python
from loom.api import LoomApp, AgentConfig
from loom.providers.llm import OpenAIProvider

# 1. Initialize App
app = LoomApp()

# 2. Configure Model Service
llm = OpenAIProvider(api_key="your-api-key")
app.set_llm_provider(llm)

# 3. Define Agent
config = AgentConfig(
    agent_id="assistant",
    name="Smart Assistant",
    system_prompt="You are a professional, rigorous AI assistant.",
    capabilities=["tool_use", "reflection"],
)

agent = app.create_agent(config)
print(f"Agent Ready: {agent.node_id}")
```

### Build a Fractal Team

Using the composition pattern to encapsulate multiple Agents into a single logical node:

```python
from loom.fractal.composite import CompositeNode
from loom.fractal.strategies import ParallelStrategy

# Combine a researcher and a writer into a "Research Team"
team_node = CompositeNode(
    node_id="research_team",
    children=[researcher_agent, writer_agent],
    strategy=ParallelStrategy() # Execute in parallel
)

# To the caller, this team behaves just like a regular Agent
await team_node.execute_task(task)
```

> For more examples, please refer to the [Getting Started Guide](docs/usage/getting-started.md).

---

## Documentation

We provide comprehensive documentation ranging from theoretical foundations to engineering practices:

**Theory**
*   [Axiomatic Framework](docs/concepts/axiomatic-framework.md) - Understanding the 5 core laws behind Loom
*   [Fractal Architecture](docs/framework/fractal-architecture.md) - Countering spatial entropy

**Core Mechanisms**
*   [Context Management](docs/framework/context-management.md) - Intelligent Token optimization strategies
*   [Event Bus](docs/framework/event-bus.md) - The nervous system of the framework
*   [Memory System](docs/features/memory-system.md) - Detailed guide to L1-L4 metabolic memory

**Features & Patterns**
*   [Orchestration Patterns](docs/features/orchestration.md) - Serial, Parallel, and Conditional routing
*   [Tool System](docs/features/tool-system.md) - Safe tool execution mechanisms
*   [Search & Retrieval](docs/features/search-and-retrieval.md) - Semantic knowledge base integration

---

## Community & Contact

Join the Loom developer community to discuss the next generation of Agent architecture.

<img src="QRcode.jpg" width="200" alt="Loom Community WeChat"/>

---

## License

**Apache License 2.0 with Commons Clause**.

Free for academic research, personal use, and internal commercial use.
**Commercial sale is strictly prohibited** (including but not limited to paid packaging, hosting services, etc.) without authorization.
See [LICENSE](LICENSE) for details.
