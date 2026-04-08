<div align="center">

<img src="loom.svg" alt="Loom Agent" width="300"/>

# Loom

**Build stateful agents with context control, safety boundaries, and extensible runtime capabilities.**

[![PyPI](https://img.shields.io/pypi/v/loom-agent.svg)](https://pypi.org/project/loom-agent/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/kongusen/loom-agent)
[![License: Apache 2.0 + Commons Clause](https://img.shields.io/badge/License-Apache_2.0_with_Commons_Clause-red.svg)](LICENSE)

**English** | [中文](README_CN.md)

[Wiki](wiki/Home.md) | [Quick Start](wiki/01-getting-started/README.md) | [PyPI](https://pypi.org/project/loom-agent/)

</div>

---

Loom exposes one public API centered on `Agent`. You configure an agent once, then use `run()`, `stream()`, and `session()` to build applications with multi-step execution, tools, heartbeat monitoring, safety rules, and session-scoped state.

## Quick Start

```bash
pip install loom-agent
export ANTHROPIC_API_KEY=sk-ant-...
```

```python
import asyncio
from loom import (
    AgentConfig,
    GenerationConfig,
    ModelRef,
    RunContext,
    SessionConfig,
    create_agent,
    tool,
)
from loom.config import (
    MemoryBackend,
    MemoryConfig,
    PolicyConfig,
    PolicyContext,
    RuntimeConfig,
    RuntimeFeatures,
    RuntimeLimits,
    ToolAccessPolicy,
    ToolPolicy,
    ToolRateLimitPolicy,
)


@tool(description="Search documentation", read_only=True)
async def search_docs(query: str) -> str:
    return f"Results for: {query}"


async def main():
    agent = create_agent(
        AgentConfig(
            model=ModelRef.anthropic("claude-sonnet-4"),
            instructions="You are a concise coding assistant",
            tools=[search_docs],
            policy=PolicyConfig(
                tools=ToolPolicy(
                    access=ToolAccessPolicy(
                        allow=["search_docs"],
                        read_only_only=True,
                    ),
                    rate_limits=ToolRateLimitPolicy(max_calls_per_minute=60),
                ),
                context=PolicyContext.named("repo"),
            ),
            memory=MemoryConfig(backend=MemoryBackend.in_memory()),
            generation=GenerationConfig(max_output_tokens=512),
            runtime=RuntimeConfig(
                limits=RuntimeLimits(max_iterations=32),
                features=RuntimeFeatures(enable_safety=True),
            ),
        )
    )

    result = await agent.run("Summarize this repository")
    print(result.output)


asyncio.run(main())
```

Import rule:

- Use `from loom import ...` for the primary application path.
- Use `from loom.config import ...` for advanced configuration objects.
- Use `from loom.runtime import ...` for runtime states, runs, and sessions when you need them directly.

## Sessions

Use `session()` when the application needs continuity across runs.

```python
session = agent.session(SessionConfig(id="demo-user"))

first = await session.run("List three qualities of a good API")
second = await session.run(
    "Summarize the previous answer in one sentence",
    context=RunContext(inputs={"previous_answer": first.output}),
)

print(second.output)
```

## Knowledge Evidence

Use `KnowledgeQuery` to resolve stable evidence, then attach it to one run through `RunContext`.

```python
from loom import KnowledgeQuery

knowledge = agent.resolve_knowledge(
    KnowledgeQuery(
        text="What are the production deployment rules?",
        goal="Summarize deployment policy",
        top_k=3,
    )
)

result = await agent.run(
    "Summarize deployment policy",
    context=RunContext(knowledge=knowledge),
)
```

## Streaming, Events, and Artifacts

```python
run = agent.session(SessionConfig(id="stream-demo")).start("Inspect the project layout")

async for event in run.events():
    print(event.type, event.payload)

result = await run.wait()
artifacts = await run.artifacts()
```

## Extensible Configuration

Loom keeps configuration extensible through stable config objects on the public API:

- `AgentConfig`: top-level stable entry for one agent
- `knowledge`: reusable knowledge sources for evidence and retrieval
- `policy`: tool access controls, context-specific governance, rate limits
- `memory`: session-level memory options
- `heartbeat`: watch sources, interval, entropy threshold
- `safety_rules`: veto rules for dangerous operations
- `runtime`: engine-level limits and features

Example:

```python
agent = create_agent(
    AgentConfig(
        model=ModelRef.anthropic("claude-sonnet-4"),
        instructions="You are a deployment assistant",
        knowledge=[
            KnowledgeSource.inline(
                "deployment-docs",
                [
                    KnowledgeDocument(content="Staging deploys are automatic.", title="Staging"),
                    KnowledgeDocument(content="Production deploys require approval.", title="Production"),
                ],
                description="Internal deployment notes",
            )
        ],
        policy=PolicyConfig(
            context=PolicyContext.named("deployment"),
            tools=ToolPolicy(
                access=ToolAccessPolicy(allow=["deploy"]),
                rate_limits=ToolRateLimitPolicy(max_calls_per_minute=10),
            ),
        ),
        memory=MemoryConfig(backend=MemoryBackend.in_memory()),
        heartbeat=HeartbeatConfig(
            interval=5.0,
            interrupt_policy=HeartbeatInterruptPolicy(),
            watch_sources=[
                WatchConfig.filesystem(
                    paths=["./src"],
                    method=FilesystemWatchMethod.HASH,
                ),
                WatchConfig.resource(
                    thresholds=ResourceThresholds(cpu_pct=80.0),
                ),
            ],
        ),
        runtime=RuntimeConfig(
            limits=RuntimeLimits(max_iterations=24, max_context_tokens=120000),
        ),
        safety_rules=[
            SafetyRule.when_argument_equals(
                name="no_prod_deploy",
                reason="Production deployment is blocked",
                tool_name="deploy",
                argument="env",
                value="production",
            )
        ],
    )
)
```

## Architecture

```text
loom/agent.py        ← Public agent API
loom/runtime/        ← Sessions, runs, loop, heartbeat, engine
loom/context/        ← Context partitions, compression, renewal, dashboard
loom/memory/         ← Session, working, semantic, persistent memory
loom/tools/          ← Tool registry, executor, governance pipeline
loom/orchestration/  ← Task planning and multi-agent coordination
loom/safety/         ← Permissions, hooks, veto authority
loom/ecosystem/      ← Skills, plugins, MCP bridge, activation
loom/evolution/      ← Self-improvement strategies
loom/providers/      ← Anthropic, OpenAI, Gemini, Qwen, Ollama
```

## Why Loom

- Structured Reason → Act → Observe → Δ execution loop
- Context pressure management and renewal
- Background heartbeat sensing
- Tool governance and veto-based safety boundaries
- Session-scoped runs, events, and artifacts
- Extensible skills, plugins, and MCP integrations

## License

Apache 2.0 with Commons Clause. See [LICENSE](LICENSE).
