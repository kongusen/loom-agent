<div align="center">

<img src="loom.svg" alt="Loom Agent" width="300"/>

# loom-agent

**Agent Runtime Framework for complex, long-running work**
*Structure for agents when tasks stop fitting in a single prompt.*

[![PyPI](https://img.shields.io/pypi/v/loom-agent.svg)](https://pypi.org/project/loom-agent/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/kongusen/loom-agent)
[![License: Apache 2.0 + Commons Clause](https://img.shields.io/badge/License-Apache_2.0_with_Commons_Clause-red.svg)](LICENSE)

**English** | [中文](README_CN.md)

[Wiki](wiki/Home.md) | [Docs Index](wiki/README.md) | [Package](https://pypi.org/project/loom-agent/)

</div>

---

## Positioning

Loom is not a prompt wrapper, and not a thin workflow shell around tools.

It is a runtime-oriented framework for teams building agents that need to stay coherent across longer tasks, multiple steps, external actions, and controlled collaboration.

The project is organized around one core idea:

> Do not force complex agent systems into a single loop.
> Give them a runtime with objects, boundaries, observability, and room to evolve.

---

## Why Loom

Most agent projects break in the same places:

- context grows until quality drops
- tool use increases but governance disappears
- retries, approvals, artifacts, and multi-step state turn into ad hoc scripts
- collaboration logic becomes hard to reason about

Loom addresses that by giving agent systems a clearer runtime structure:

- **Runtime object model**: organize execution as `AgentRuntime -> Session -> Task -> Run`
- **Context control**: separate context management, partitioning, compression, and renewal
- **Execution loop**: keep loop, state machine, decision, and heartbeat as first-class modules
- **Tooling and governance**: register tools, execute them, and put constraints around them
- **Collaboration**: prepare for sub-agents, event-driven coordination, and cluster-style expansion
- **Safety boundaries**: keep permissions, constraints, hooks, and veto points in explicit modules

This makes Loom a better fit for systems that need runtime structure, not just model access.

---

## What You Get Today

The current repository already contains a real framework skeleton with a stable direction.

| Area | Status | Code Fact |
|---|---|---|
| Runtime API and object model | Implemented | `loom/api/` |
| Session / Task / Run handles | Implemented, base version | `loom/api/handles.py` |
| Context and memory modules | Implemented, base version | `loom/context/`, `loom/memory/` |
| Execution loop and state modules | Implemented, base version | `loom/execution/` |
| Tool registry and execution layers | Implemented, base version | `loom/tools/` |
| Collaboration and sub-agent modules | Partially implemented | `loom/orchestration/`, `loom/cluster/` |
| Ecosystem: skills / plugins / MCP | Partially implemented | `loom/ecosystem/`, `loom/capabilities/` |
| Safety, permissions, constraints | Implemented, base version | `loom/safety/` |

The important distinction is deliberate: Loom already has a strong runtime shape, while some deeper execution integration is still converging.

---

## Quick Start

### Install

```bash
pip install loom-agent
```

### Start with the Runtime API

If you are integrating Loom into an application, this is the cleanest entry point.

```python
import asyncio

from loom.api import AgentProfile, AgentRuntime


async def main():
    profile = AgentProfile.from_preset("default")
    runtime = AgentRuntime(profile=profile)

    session = runtime.create_session(metadata={"project": "demo"})
    task = session.create_task(
        goal="Review the current repository structure",
        context={"repo": "loom-agent"},
    )

    run = task.start()
    result = await run.wait()

    print(result.state.value)
    print(result.summary)


asyncio.run(main())
```

### Then go deeper when needed

Loom exposes multiple layers depending on how much control you want:

- `loom/api/`: runtime-facing objects and handles for application integration
- `loom/agent/`: lower-level agent core and runtime skeleton
- `loom/context/`, `loom/execution/`, `loom/memory/`: execution internals
- `loom/tools/`, `loom/orchestration/`, `loom/safety/`: extension and control layers

---

## Architecture At A Glance

```text
Interface Layer     -> loom/api
Core Runtime        -> loom/agent, loom/context, loom/execution, loom/memory
Capability Layer    -> loom/tools, loom/orchestration, loom/ecosystem, loom/capabilities
Safety Layer        -> loom/safety
Support Layer       -> loom/providers, loom/evolution, loom/utils
```

From a repository shape perspective, Loom is already closer to a runtime system than to a single-file SDK.

---

## Best-Fit Use Cases

Loom is a strong fit when a task is not finished in one prompt:

- coding and refactoring workflows that need persistent context and tool use
- research and analysis loops that need evidence, memory, and structured continuation
- agent backends that need sessions, tasks, runs, events, and artifacts
- extensible products that need skills, plugins, or MCP-style capability integration

If all you need is one-shot chat or a thin model wrapper, Loom is probably more framework than you need.

---

## Why Teams Use It

- **Clear runtime entry point** instead of scattered helper functions
- **Explicit lifecycle objects** instead of hidden internal state
- **Better control surfaces** for approvals, events, artifacts, and policies
- **Separation of concerns** across context, execution, tooling, collaboration, and safety
- **A credible path to advanced agent systems** without pretending every capability is already fully finished

This is the practical value proposition: Loom helps teams move from demo-style agents to runtime-shaped agent systems.

---

## Documentation

- [Wiki Home](wiki/Home.md)
- [Quick Start](wiki/04-开发说明/快速开始.md)
- [Agent and Run](wiki/04-开发说明/Agent与Run.md)
- [Architecture Overview](wiki/03-架构说明/总体架构.md)
- [Capability Matrix](wiki/05-参考资料/代码能力矩阵.md)
- [Strategic Positioning](wiki/02-战略表达/产品定位.md)

---

## Current State

The most accurate way to describe Loom today is:

> a runtime framework with a real public object model, clear module boundaries, and a strong foundation for controlled agent systems, while deeper execution integration and some advanced collaboration capabilities are still maturing.

That precision matters. The architecture is real, the direction is clear, and the repo is already useful for teams that care about runtime structure early.
