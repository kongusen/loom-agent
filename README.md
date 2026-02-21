<div align="center">

<img src="loom.svg" alt="Loom Agent" width="300"/>

# loom-agent

**Long Horizon Agents Framework**
*Agents that don't collapse when problems get long.*

[![PyPI](https://img.shields.io/pypi/v/loom-agent.svg)](https://pypi.org/project/loom-agent/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: Apache 2.0 + Commons Clause](https://img.shields.io/badge/License-Apache_2.0_with_Commons_Clause-red.svg)](LICENSE)

**English** | [中文](README_CN.md)

[Wiki](wiki/Home.md) | [Examples](examples/demo/) | [v0.6.0](https://pypi.org/project/loom-agent/)

</div>

---

## A short story

We built many agents.

They could write code.
They could plan tasks.
They could use tools.

And they all failed the same way.

Not because they were stupid.
Not because they lacked tools.

They failed because they were **rigid**.

When a task got harder, they couldn't split it.
When a subtask failed, they couldn't adapt.
When the environment changed, they couldn't sense it.

We looked at biology for answers.

An amoeba is one of the simplest organisms on Earth.
Yet it can sense, move, split, and adapt — without a brain.

It doesn't plan. It **responds**.
It doesn't command. It **self-organizes**.

That was the moment we realized:

> The problem wasn't intelligence.
> It was the lack of a living mechanism.

---

## The Amoba Mechanism

Real-world tasks are not prompts.

They shift, branch, fail, and evolve. A coding task spawns debugging. A research task splits into sub-questions. A failed attempt demands a different approach.

Most agent frameworks are **static pipelines**. Fixed plans, fixed agents, fixed flows. When reality deviates, they break.

Biology solved this billions of years ago.

An amoeba **senses** its environment, **matches** the best response, **scales** by splitting when needed, **executes**, **evaluates** the outcome, and **adapts** for next time.

**loom-agent's AmoebaLoop works the same way:**

```
SENSE → MATCH → SCALE → EXECUTE → EVALUATE → ADAPT
```

* **SENSE** — Analyze task complexity and detect domains
* **MATCH** — Auction across capable agents, evolve new skills if needed
* **SCALE** — Split complex tasks via mitosis, create child agents
* **EXECUTE** — Run with enriched context and token budgets
* **EVALUATE** — Score results, update capability via EMA rewards
* **ADAPT** — Recycle unhealthy agents (apoptosis), calibrate complexity estimates, evolve skills

Agents that perform well get stronger. Agents that fail get recycled. New specialists emerge on demand. The system **lives**.

---

## loom-agent: Structure + Life

A loom creates fabric through **structure** — threads interweave, patterns repeat, tension stays balanced.

An amoeba creates life through **adaptation** — sensing, splitting, evolving, recycling.

**loom-agent combines both.**

The framework is the loom — composable modules that weave agents together.
The AmoebaLoop is the life — a self-organizing cycle that makes agents breathe.

```
Structure (Loom)  →  Agent · Memory · Tools · Events · Interceptors · Context · Skills
Life (Amoba)      →  Sense · Match · Scale · Execute · Evaluate · Adapt
```

Complexity grows, structure doesn't. Agents adapt, the framework holds.

---

## Core Principles

**Self-organizing over orchestrating** — No central controller. Agents sense, bid, and adapt autonomously through the AmoebaLoop.

**Composition over inheritance** — Agent = provider + memory + tools + context + events + interceptors. Add only what you need.

**Mitosis over monoliths** — Complex tasks split into subtasks, spawning child agents. Simple tasks run directly.

**Reward over rules** — Capability scores update via EMA after every execution. Good agents get stronger; bad agents get recycled.

---

## Use Cases

loom-agent is not a prompt collection, not a tool orchestration wrapper, not a workflow engine.

It's designed for systems that need to **remain stable over time**:

Long-running autonomous workflows · Research agents · Multi-day task execution · Complex RAG systems · Agent-based SaaS backends · AI operators and copilots

---

## Installation

```bash
pip install loom-agent
```

## Quick Start

```python
import asyncio
from loom import Agent, AgentConfig
from loom.providers.openai import OpenAIProvider

provider = OpenAIProvider(AgentConfig(
    api_key="sk-...",
    model="gpt-4o-mini",
))

agent = Agent(
    provider=provider,
    config=AgentConfig(system_prompt="You are a helpful assistant.", max_steps=3),
)

async def main():
    result = await agent.run("Introduce Python in one sentence.")
    print(result.content)

asyncio.run(main())
```

### Streaming

```python
from loom import TextDeltaEvent, DoneEvent

async for event in agent.stream("Introduce Rust in one sentence."):
    if isinstance(event, TextDeltaEvent):
        print(event.text, end="", flush=True)
    elif isinstance(event, DoneEvent):
        print(f"\nDone, steps={event.steps}")
```

### Tools

```python
from pydantic import BaseModel
from loom import ToolRegistry, define_tool, ToolContext

class CalcParams(BaseModel):
    expression: str

async def calc_fn(params: CalcParams, ctx: ToolContext) -> str:
    return str(eval(params.expression))

tools = ToolRegistry()
tools.register(define_tool("calc", "Evaluate math expression", CalcParams, calc_fn))

agent = Agent(provider=provider, config=AgentConfig(max_steps=5), tools=tools)
result = await agent.run("What is 2**20?")
```

### Multi-Agent Delegation

```python
from loom import EventBus

bus = EventBus(node_id="root")

researcher = Agent(
    provider=provider, name="researcher",
    config=AgentConfig(system_prompt="You are a researcher.", max_steps=2),
    event_bus=bus.create_child("researcher"),
)
writer = Agent(
    provider=provider, name="writer",
    config=AgentConfig(system_prompt="You are a writer.", max_steps=2),
    event_bus=bus.create_child("writer"),
)

r1 = await researcher.run("Research AI memory systems")
r2 = await writer.run("Write a technical article")
```

> See all 15 demos in [examples/demo/](examples/demo/).

---

## Core Features

### Composition-Based Architecture
Agent is assembled from orthogonal modules — provider, memory, tools, context, event bus, interceptors, skills. Add only what you need; every module is optional.

### Three-Layer Memory
L1 `SlidingWindow` (recent turns) → L2 `WorkingMemory` (key facts) → L3 `PersistentStore` (long-term). Token-budget driven, automatic compaction.

### Tool System
`define_tool` + `ToolRegistry` with Pydantic schema validation. LLM autonomously decides when to call tools via ReAct loop.

### EventBus
Parent-child event propagation, pattern matching, typed events. All agent lifecycle events flow through the bus.

### Interceptor Chain
Middleware pipeline that transforms messages before/after LLM calls. Audit logging, content filtering, prompt injection — all as interceptors.

### Knowledge Base (RAG)
Document ingestion, chunking, embedding, hybrid retrieval (keyword + vector RRF fusion). Bridges to Agent via `KnowledgeProvider` → `ContextOrchestrator`.

### Context Orchestration
Multi-source context collection with adaptive budget allocation. Memory, knowledge, and custom providers unified under `ContextOrchestrator`.

### Skill System
Keyword / pattern / semantic triggers auto-activate domain-specific skills, dynamically injecting expert instructions into the agent.

### Cluster Auction
Capability-scored agent nodes bid on tasks. `RewardBus` updates scores via EMA after each execution. `LifecycleManager` monitors health.

### Resilient Providers
`BaseLLMProvider` with exponential-backoff retry + circuit breaker. Any OpenAI-compatible API works via `OpenAIProvider`.

### Runtime & AmoebaLoop
`Runtime` orchestrates cluster-level task submission. `AmoebaLoop` implements a 6-phase self-organizing cycle: SENSE → MATCH → SCALE → EXECUTE → EVALUATE → ADAPT.

---

## Documentation

See the [Wiki](wiki/Home.md) for detailed documentation:

| Document | Description | Demo |
| ---- | ---- | ---- |
| [Agent](wiki/Agent.md) | Agent core, AgentConfig, run/stream | 01 |
| [Tools](wiki/Tools.md) | define_tool, ToolRegistry, ToolContext | 02 |
| [Events](wiki/Events.md) | EventBus, parent-child propagation | 03 |
| [Interceptors](wiki/Interceptors.md) | InterceptorChain, middleware pipeline | 04 |
| [Memory](wiki/Memory.md) | L1/L2/L3 three-layer memory | 05 |
| [Knowledge](wiki/Knowledge.md) | KnowledgeBase, RAG hybrid retrieval | 06 |
| [Context](wiki/Context.md) | ContextOrchestrator, multi-source | 07 |
| [Skills](wiki/Skills.md) | SkillRegistry, trigger-based activation | 08 |
| [Cluster](wiki/Cluster.md) | ClusterManager, auction, RewardBus | 09-10 |
| [Providers](wiki/Providers.md) | BaseLLMProvider, retry, circuit breaker | 11 |
| [Runtime](wiki/Runtime.md) | Runtime, AmoebaLoop 6-phase cycle | 12-13 |
| [Architecture](wiki/Architecture.md) | Full-stack pipeline, delegation, architecture diagram | 14-15 |

---

## Project Status

Current version: **v0.6.0**.

APIs may evolve rapidly.

Structure will not.

---

## Philosophy

> Structure holds the shape.
> Life fills the shape with motion.

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

**Welcome to living agents.**
