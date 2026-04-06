# Loom — Python Agent Runtime Framework

> Build autonomous AI agents that run, observe, and improve themselves.

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](../LICENSE)

Loom is a **production-grade Python framework** for building autonomous AI agents. Unlike prompt wrappers or simple tool chains, Loom provides a full agent runtime: structured context management, parallel background sensing, multi-agent orchestration, safety controls, and self-improvement strategies.

## Why Loom?

| | LangChain | AutoGen | CrewAI | **Loom** |
|---|---|---|---|---|
| Context pressure management | ❌ | ❌ | ❌ | ✅ |
| Background heartbeat sensing | ❌ | ❌ | ❌ | ✅ |
| Structured Reason→Act→Observe→Δ loop | ❌ | partial | ❌ | ✅ |
| Veto authority (Harness) | ❌ | ❌ | ❌ | ✅ |
| Self-improvement strategies (E1–E4) | ❌ | ❌ | ❌ | ✅ |
| Multi-provider (Anthropic/OpenAI/Gemini) | ✅ | ✅ | ✅ | ✅ |

## Quick Start

```python
from loom.api import AgentRuntime, AgentProfile
from loom.providers import AnthropicProvider

provider = AnthropicProvider(api_key="...")
runtime = AgentRuntime(
    profile=AgentProfile.from_preset("default"),
    provider=provider,
)

session = runtime.create_session()
task = session.create_task("Summarize the latest commits in this repo")
run = task.start()

result = await run.wait()
print(result.output)
```

## How Loom Works

Every Loom agent is defined by six components:

```
Agent = ⟨C, M, L*, H_b, S, Ψ⟩
```

| Component | What it does |
|-----------|-------------|
| **C** — Context | The agent's only perception interface. Five partitions, five compression levels. |
| **M** — Memory | Session, working, semantic, and persistent memory layers. |
| **L\*** — Loop | The execution engine: Reason → Act → Observe → Δ, repeated until done. |
| **H_b** — Heartbeat | A background thread that senses filesystem, process, and resource changes in parallel. |
| **S** — Skills | Progressively loaded tools, plugins, and MCP servers — only what the task needs. |
| **Ψ** — Harness | Safety and control layer. Sets boundaries, holds veto power, never replaces model decisions. |

## Navigation

| I want to... | Start here |
|---|---|
| Get up and running fast | [Quick Start](01-getting-started/README.md) |
| Understand how it works | [Core Concepts](02-core-concepts/README.md) |
| Build multi-agent systems | [Multi-Agent](04-multi-agent/README.md) |
| Add skills / MCP / plugins | [Ecosystem](05-ecosystem/README.md) |
| Look up the API | [API Reference](07-api-reference/README.md) |
| Compare with the design spec | [hernss-agent-framework.md](hernss-agent-framework.md) |

## Documentation Sections

| Section | Audience |
|---|---|
| [01 Getting Started](01-getting-started/README.md) | New users |
| [02 Core Concepts](02-core-concepts/README.md) | Everyone |
| [03 Runtime](03-runtime/README.md) | Framework contributors |
| [04 Multi-Agent](04-multi-agent/README.md) | Orchestration users |
| [05 Ecosystem](05-ecosystem/README.md) | Extension developers |
| [06 Self-Improvement](06-self-improvement/README.md) | Advanced users |
| [07 API Reference](07-api-reference/README.md) | Integration developers |
| [08 Reference](08-reference/README.md) | Quick lookup |

## Status Legend

| Badge | Meaning |
|---|---|
| ✅ Implemented | Stable, callable today |
| 🔧 Partial | Structure exists, still converging |
| 📋 Planned | Design defined, not yet built |
