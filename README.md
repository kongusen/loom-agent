<div align="center">

<img src="loom.svg" alt="Loom Agent" width="300"/>

# Loom — Python Agent Runtime Framework

**Build autonomous AI agents that run, observe, and improve themselves.**

[![PyPI](https://img.shields.io/pypi/v/loom-agent.svg)](https://pypi.org/project/loom-agent/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/kongusen/loom-agent)
[![License: Apache 2.0 + Commons Clause](https://img.shields.io/badge/License-Apache_2.0_with_Commons_Clause-red.svg)](LICENSE)

**English** | [中文](README_CN.md)

[Wiki](wiki/Home.md) | [Quick Start](wiki/01-getting-started/README.md) | [API Reference](wiki/07-api-reference/README.md) | [PyPI](https://pypi.org/project/loom-agent/)

</div>

---

Loom is a **production-grade Python framework** for building autonomous AI agents. Unlike prompt wrappers or simple LangChain pipelines, Loom provides a complete agent runtime: structured context management, parallel background sensing, multi-agent orchestration, safety controls, and self-improvement strategies.

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

```bash
pip install loom-agent
```

```python
import asyncio
from loom.api import AgentRuntime, AgentProfile
from loom.providers import AnthropicProvider

async def main():
    runtime = AgentRuntime(
        profile=AgentProfile.from_preset("default"),
        provider=AnthropicProvider(api_key="sk-ant-..."),
    )
    session = runtime.create_session()
    task = session.create_task("Summarize the latest commits in this repo")
    run = task.start()

    result = await run.wait()
    print(result.output)

asyncio.run(main())
```

## How It Works

Every Loom agent is defined by six components:

```
Agent = ⟨C, M, L*, H_b, S, Ψ⟩
```

| Component | What it does | Module |
|---|---|---|
| **C** — Context | Five-partition context window with five compression levels | `loom/context/` |
| **M** — Memory | Session, working, semantic, and persistent memory | `loom/memory/` |
| **L\*** — Loop | Reason → Act → Observe → Δ execution engine | `loom/runtime/loop.py` |
| **H_b** — Heartbeat | Background thread sensing filesystem/process/resources in parallel | `loom/runtime/heartbeat.py` |
| **S** — Skills | Progressively loaded tools, plugins, MCP servers | `loom/ecosystem/` |
| **Ψ** — Harness | Safety layer with veto authority — sets boundaries, never replaces model decisions | `loom/safety/` |

## Key Features

### Context Management
- Five partitions: `system / working / memory / skill / history`
- Five compression levels triggered by context pressure ρ: Snip → Micro → Collapse → Auto → Reactive
- Context renewal (disk paging) when ρ = 1.0 — agent continues without losing working state

### Multi-Agent Orchestration
- `TaskPlanner` builds dependency-ordered task graphs
- `Coordinator` executes plans with timeout and error handling
- `SubAgentManager` spawns specialist agents with depth limit (`d_max`)

### Safety & Control (Harness Ψ)
- Three-tier protection: Speculative Classifier → Hook Policy → Permission Decision
- `VetoAuthority` blocks any tool call — the safety valve
- Modes: `DEFAULT` / `PLAN` / `AUTO`

### Self-Improvement
- **E1** Tool Learning — tracks reliability per tool
- **E2** Policy Optimization — turns blocks into recommendations
- **E3** Constraint Hardening — solidifies failure root causes into permanent constraints
- **E4** Amoeba Split — detects when to spawn a specialist sub-agent

### LLM Providers
All providers include built-in retry and circuit breaker:

```python
from loom.providers import AnthropicProvider, OpenAIProvider, GeminiProvider
```

## Architecture

```
loom/api/           ← Public entry point: AgentRuntime → Session → Task → Run
loom/runtime/       ← L* loop + H_b heartbeat + monitors
loom/context/       ← Context partitions, compression, renewal, dashboard
loom/memory/        ← Session, working, semantic, persistent memory
loom/tools/         ← Tool registry, executor, governance pipeline
loom/orchestration/ ← TaskPlanner, Coordinator, SubAgentManager
loom/safety/        ← PermissionManager, HookManager, VetoAuthority
loom/ecosystem/     ← Skills, plugins, MCP bridge
loom/evolution/     ← Self-improvement strategies E1–E4
loom/providers/     ← Anthropic, OpenAI, Gemini
```

## Use Cases

Loom is the right choice when a task doesn't fit in a single prompt:

- **Coding agents** — multi-step refactoring with persistent context and tool use
- **Research agents** — evidence gathering, memory, and structured continuation
- **Agent backends** — sessions, tasks, runs, events, approvals, and artifacts
- **Extensible products** — skills, plugins, or MCP-style capability integration

## Documentation

| | |
|---|---|
| [Quick Start](wiki/01-getting-started/README.md) | Get running in 5 minutes |
| [Core Concepts](wiki/02-core-concepts/README.md) | How Loom works |
| [Multi-Agent](wiki/04-multi-agent/README.md) | Orchestration patterns |
| [API Reference](wiki/07-api-reference/README.md) | Full API docs |
| [Comparison](wiki/08-reference/comparison.md) | vs LangChain / AutoGen / CrewAI |
| [Design Spec](hernss-agent-framework.md) | Internal architecture reference |

## License

Apache 2.0 with Commons Clause. See [LICENSE](LICENSE).
