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

### Core Features (v0.3.7)

1.  **🧬 Controlled Fractal Architecture**:
    *   Agents, Tools, and Crews are all **Nodes**. Nodes can contain other nodes recursively.
    *   Even the most complex Agent cluster behaves like a simple function call externally.

2.  **🎯 Cognitive Dynamics System**:
    *   **Dual-System Thinking**: Intelligent collaboration between System 1 (fast intuition) and System 2 (deep reasoning).
    *   **Confidence Evaluation**: Automatic fallback from System 1 to System 2 on low confidence.
    *   **Unified Configuration**: Manage cognition, context, and memory through `CognitiveConfig`.
    *   **Preset Modes**: Three out-of-the-box modes: fast/balanced/deep.

3.  **🧠 Composite Memory System**:
    *   **L1-L4 Hierarchy**: Complete memory spectrum from instant reaction (L1) to semantic knowledge (L4).
    *   **BGE Embedding**: ONNX-optimized BGE model for high-performance semantic retrieval.
    *   **Smart Compression**: Automatic L4 knowledge base clustering to maintain optimal size (<150 facts).
    *   **Memory Metabolism**: Automated `Ingest` -> `Digest` -> `Assimilate` consolidation flow.
    *   **Context Projection**: Intelligent projection of parent Agent context to child Agents with 5 projection modes.

4.  **🎨 Pattern System**:
    *   **5 Built-in Patterns**: Analytical, Creative, Collaborative, Iterative, Execution.
    *   **Configuration Composition**: Each pattern presets optimal cognitive, memory, and execution configs.
    *   **Flexible Extension**: Support custom patterns for specific scenarios.

5.  **🛡️ Protocol-First & Recursion**:
    *   **Infinite Recursion**: Support unlimited levels of task delegation based on unified protocol.
    *   **Unified Execution**: `FractalOrchestrator` unifies tool calls and sub-Agent orchestration.
    *   **Standard Contract**: All interactions defined via CloudEvents and MCP.

6.  **⚡ Universal Event Bus**:
    *   Based on CloudEvents standard.
    *   Supports full-chain Tracing and Auditing.

7.  **🌐 Multi-LLM Support**:
    *   **10+ Providers**: OpenAI, Anthropic, Gemini, DeepSeek, Qwen, Kimi, Doubao, etc.
    *   **Unified Interface**: Consistent API design for easy model switching.
    *   **Streaming Output**: Native support for streaming responses and structured output.

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
- [Fractal Nodes](guides/fractal-nodes.md) - Build self-organizing agent structures
- [Dual-System Usage](guides/dual-system-usage.md) - System 1/2 configuration guide
- [LLM Streaming](guides/llm-streaming.md) - Handle streaming tool calls
- [Structured Output](guides/structured-output.md) - Enforce JSON output for Claude/Gemini
- [Skills](guides/skills/) - Develop custom skills
- [Configuration](guides/configuration/) - Configuration and deployment
- [Deployment](guides/deployment/) - Production deployment

### 💡 [Concepts](concepts/)
**Understanding-oriented** - Deep dive into core concepts
- [Architecture Design](concepts/architecture.md)
- [Cognitive Dynamics](concepts/cognitive-dynamics.md)
- [Design Philosophy](concepts/design-philosophy.md)
- [Memory System](concepts/memory.md)
- [Dual-System Thinking](concepts/dual-system.md)
- [Agent Node](concepts/agent-node.md)
- [Protocol Design](concepts/protocol.md)

### 📚 [Reference](reference/)
**Information-oriented** - Complete API documentation
- [loom.weave API](reference/api/weave.md)
- [loom.stdlib API](reference/api/stdlib.md)
- [Configuration Reference](reference/api/config.md)

---

## 🤝 Contributing

We welcome Pull Requests and Issues! See [CONTRIBUTING.md](../../CONTRIBUTING.md) for more details.

---

## 🔬 Technical Documentation

In-depth technical design and implementation documents:

- [BGE Embedding Optimization](../bge_embedding_optimization.md) - ONNX + Int8 quantization optimization
- [L4 Compression Design](../l4_compression_design.md) - Automatic knowledge base compression
- [Projection Strategy Design](../projection_strategy_design.md) - Complete context projection solution
- [Projection Optimization Analysis](../projection_optimization_analysis.md) - Projection system analysis
- [General Framework Projection](../projection_for_general_framework.md) - Projection recommendations for general frameworks

---

## 📄 License

**Apache License 2.0 with Commons Clause**.

This software is free for academic research, personal learning, and internal commercial use.
**Unauthorized commercial sale is strictly prohibited** (including but not limited to bundling this software for a fee or providing managed services).
See [LICENSE](../../LICENSE) for details.
