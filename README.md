<div align="center">

<img src="loom.svg" alt="Loom Agent" width="300"/>

# loom-agent

**Long Horizon Agents Framework**
*Agents that don't collapse when problems get long.*

[![PyPI](https://img.shields.io/pypi/v/loom-agent.svg)](https://pypi.org/project/loom-agent/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: Apache 2.0 + Commons Clause](https://img.shields.io/badge/License-Apache_2.0_with_Commons_Clause-red.svg)](LICENSE)

**English** | [中文](README_CN.md)

[Wiki](wiki/Home.md) | [Examples](examples/demo/)

</div>

---

## A short story

We built many agents.

They could write code.
They could plan tasks.
They could use tools.

And they all failed the same way.

Not at step one.
Not at step five.

They failed quietly —
around step twenty.

The plan was still there.
The tools were still available.

But no one remembered:

* why this task was started
* what had already been tried
* which decisions mattered
* or who was supposed to act next

The agent didn't crash.

It simply **forgot who it was**.

That was the moment we realized:

> The problem wasn't intelligence.
> It was time.

---

## The Long Horizon Collapse

Real-world tasks are not prompts.

They span dozens of steps, days of time, constantly changing goals.
Plans expire, context explodes, memory fragments.

This is the **Long Horizon Problem**.

Most agent frameworks assume tasks are short, goals are stable, failures are one-time events.
They rely on single planners, global memory, linear execution flows.

This looks great in demos.

But after step 20, agents start endlessly re-planning, contradicting themselves, repeating failed actions.
Adding more tools only accelerates the collapse.

**The problem is not reasoning capability.**

Most agents fail because they lack structure that can remain stable over time.

> More tokens won't fix this.
> Better prompts won't fix this.
> **Only structure can.**

---

## loom-agent: The Answer Through Structural Recursion

Humans never solved complexity by being smarter.

We use **repeating structure**: teams resemble departments, departments resemble companies, companies resemble ecosystems.
Even as scale grows, structure remains stable. This is fractal organization.

**loom-agent makes agents work the same way.**

Instead of building "super agents", we build **self-similar agents**.
Each agent contains the same core structure:

```
Observe → Decide → Act → Reflect → Evolve
```

An agent can create sub-agents, and sub-agents behave exactly the same way.
Tasks become worlds, worlds contain smaller worlds.

**Complexity grows, structure doesn't.**

This means systems can scale infinitely — without redesigning architecture, without prompt inflation, without centralized planners.

---

## The Loom Metaphor

A loom doesn't create fabric through intelligence.

It creates fabric through **structure**.

* threads interweave
* patterns repeat
* tension stays balanced

Agents in loom-agent are threads.

The framework is the loom.

What emerges is not a workflow —
but a living structure that persists over time.

---

## Core Principles

loom-agent's design revolves around four core beliefs:

**Structure over intelligence** — Smarter reasoning doesn't prevent collapse, stable structure does.

**Built for long horizons** — Designed for tasks that last hours or days, require retries and recovery, involve evolving goals.

**Fractal by default** — Every agent can become a system, every system behaves like an agent. Scale without rewriting architecture.

**Identity before memory** — Agents must always know who they are, what role they serve, which phase they belong to, what they're responsible for. Without identity, memory is noise.

---

## Use Cases

loom-agent is not a prompt collection, not a tool orchestration wrapper, not a workflow engine.

It's designed for systems that need to **remain stable over time**:

Long-running autonomous workflows · Research agents · Multi-day task execution · Complex RAG systems · Agent-based SaaS backends · AI operators and copilots

---

## Installation

```bash
# Core install (pydantic + numpy + tiktoken)
pip install loom-agent

# With OpenAI-compatible LLMs (DeepSeek, Qwen, Kimi, etc.)
pip install loom-agent[llm]

# With Anthropic Claude
pip install loom-agent[anthropic]

# All optional dependencies
pip install loom-agent[all]
```

## Quick Start

### Create Your First Agent

```python
import os
import asyncio
from loom.agent import Agent
from loom.providers.llm import OpenAIProvider
from loom.config.llm import LLMConfig

async def main():
    # 1. Configure model service
    config = LLMConfig(
        provider="openai",
        model="gpt-4o-mini",
        api_key=os.environ["OPENAI_API_KEY"],
        base_url=os.environ.get("OPENAI_BASE_URL"),  # Optional
    )
    llm = OpenAIProvider(config)

    # 2. Create Agent
    agent = Agent.create(
        llm=llm,
        system_prompt="You are a helpful assistant.",
        max_iterations=5,
    )

    # 3. Run task
    result = await agent.run("Introduce Python in one sentence.")
    print(f"Result: {result}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Using Other LLMs

```python
from loom.providers.llm import DeepSeekProvider, AnthropicProvider
from loom.config.llm import LLMConfig

# DeepSeek
llm = DeepSeekProvider(LLMConfig(api_key="sk-..."))

# Anthropic Claude
llm = AnthropicProvider(LLMConfig(
    provider="anthropic",
    model="claude-3-5-sonnet-20241022",
    api_key="sk-ant-...",
))

# Any OpenAI-compatible API
from loom.providers.llm import OpenAICompatibleProvider
llm = OpenAICompatibleProvider(LLMConfig(
    api_key="sk-...",
    base_url="http://localhost:8000/v1",
    model="my-model",
))
```

### Fractal Composition: Multi-Agent Collaboration

Agents can automatically create sub-agents via the `delegate_task` meta-tool, or you can compose manually with `NodeContainer`:

```python
from loom.fractal.container import NodeContainer
from loom.agent.card import AgentCard

# Wrap an agent in a container node
container = NodeContainer(
    node_id="research_team",
    agent_card=AgentCard(
        agent_id="research_team",
        name="Research Team",
        description="A research team",
        capabilities=["research", "writing"],
    ),
    child=researcher_agent,
)

# To the caller, the container behaves just like a regular Agent
await container.execute_task(task)
```

> For more examples, see [Examples](examples/demo/).

---

## Core Features

### Axiom-Driven Design
Built on 4 formal axioms: A2 Event Sovereignty, A3 Fractal Self-Similarity, A4 Memory Hierarchy, A6 Four-Paradigm Autonomy. Every module traces back to these axioms.

### Fractal Architecture
Recursive composition via `NodeContainer` and `ParallelExecutor`. Whether a single agent or a complex collaboration team, they are consistent nodes within Loom. Agents natively support `create_plan` (planning) and `delegate_task` (delegation) fractal modes.

### Token-First Memory System
L1 (8K) → L2 (16K) → L3 (32K) → L4 (100K) four-layer memory with token budgets at the core. Automatic migration, intelligent compression, key fact extraction, semantic vector retrieval.

### Unified Event Bus
All communication flows through Task objects routed by EventBus. Supports memory transport (single-machine) and NATS transport (distributed), hierarchical event propagation, multi-agent parallel SSE output.

### Four-Paradigm Autonomy
Agents autonomously choose execution strategies: Reflection (LLM streaming), Tool Use (ReAct loop), Planning (create_plan), Collaboration (delegate_task).

### Context Orchestration
ContextOrchestrator based on Anthropic Context Engineering principles. Multi-source collection, adaptive budget allocation, unified retrieval (memory + RAG knowledge bases).

### Multi-LLM Support
OpenAI · Anthropic · DeepSeek · Qwen · Gemini · Ollama · Kimi · Doubao · Zhipu · vLLM · GPUStack, plus any OpenAI-compatible API.

### Progressive Disclosure Configuration
Three-tier configuration from zero-config to fully customized. Skill system follows Anthropic standard format with discovery, activation, and instantiation stages.

---

## Documentation

See the [Wiki](wiki/Home.md) for detailed documentation:

| Document | Description |
| ---- | ---- |
| [Architecture](wiki/Architecture.md) | Axiom system, four-paradigm model, data flow |
| [Agent](wiki/Agent.md) | Mixin architecture, creation patterns, execution API |
| [Events](wiki/Events.md) | EventBus, action enums, transport layer |
| [Memory](wiki/Memory.md) | L1-L4 four-layer memory, compression & migration |
| [Context](wiki/Context.md) | ContextOrchestrator, budget management |
| [Runtime](wiki/Runtime.md) | Task model, interceptors, session isolation |
| [Tools](wiki/Tools.md) | SandboxToolManager, built-in tools |
| [Skills](wiki/Skills.md) | Skill definitions, progressive disclosure, activation |
| [Providers](wiki/Providers.md) | LLM, Knowledge, MCP, Embedding |
| [Config](wiki/Config.md) | Progressive disclosure configuration |
| [Fractal](wiki/Fractal.md) | Recursive composition, inheritance rules |
| [Observability](wiki/Observability.md) | Tracing, Metrics, OTLP export |

---

## Project Status

loom-agent is under active development. Current version: **v0.5.7**.

The framework focuses on:

* Agent identity modeling
* Fractal agent composition
* Long-horizon execution loops
* Structured memory layering
* Failure-aware task evolution

APIs may evolve rapidly.

Structure will not.

---

## Philosophy

> Intelligence solves problems.
> Structure survives time.

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

---

**Welcome to Long Horizon Agents.**
