# Loom Architecture

Version: 0.7.2 | Updated: 2026-04-08

## Overview

Loom now exposes one public API centered on `Agent`, while keeping the internal runtime split across context, memory, tools, safety, heartbeat, orchestration, and providers.

The key architectural rule is:

- public API first
- internal runtime second

Application developers should reason about Loom as `AgentConfig -> Agent -> Session -> Run`. The deeper runtime decomposition exists to support that contract, not to replace it as a second public abstraction.

The internal conceptual model is still:

```text
A = ⟨C, M, L*, H_b, S, Ψ⟩
```

| Symbol | Meaning | Module |
|---|---|---|
| `C` | Context management | `loom/context/` |
| `M` | Memory layers | `loom/memory/` |
| `L*` | Execution loop | `loom/runtime/loop.py` |
| `H_b` | Heartbeat sensing | `loom/runtime/heartbeat.py` |
| `S` | Skills, tools, plugins, MCP | `loom/tools/`, `loom/ecosystem/` |
| `Ψ` | Safety boundaries and veto | `loom/safety/` |

## Public Layer Map

```text
loom/__init__.py
    └── loom/agent.py
            ├── Agent
            ├── create_agent()
            └── tool()

loom/config.py
    ├── AgentConfig
    ├── ModelRef
    ├── GenerationConfig
    ├── PolicyConfig / ToolPolicy
    ├── MemoryConfig
    ├── HeartbeatConfig
    ├── RuntimeConfig
    ├── KnowledgeQuery / KnowledgeBundle
    └── SafetyRule

loom/runtime/session.py
    ├── SessionConfig
    ├── Session
    ├── RunContext
    ├── Run
    └── RunResult
```

Import layering is intentional:

- `loom`: narrow primary application surface
- `loom.config`: stable configuration vocabulary
- `loom.runtime`: runtime lifecycle objects

## Runtime Flow

```text
AgentConfig
    -> Agent
        -> Session
            -> Run
                -> AgentEngine
                    -> ContextManager
                    -> ToolGovernance / ToolExecutor
                    -> VetoAuthority
                    -> Heartbeat
                    -> Provider
```

## Public Contracts

### Agent Assembly

`AgentConfig` is the only top-level public assembly object.

Key stable config domains:

- `model`: provider-backed model reference
- `generation`: model generation controls
- `tools`: declared `ToolSpec` list
- `knowledge`: declarative knowledge sources
- `policy`: governance and context
- `memory`: session memory settings
- `heartbeat`: watch sources and interrupt policy
- `runtime`: limits, features, fallback behavior
- `safety_rules`: declarative veto rules

### Runtime Objects

The supported public execution path is:

```text
AgentConfig -> Agent -> Session -> Run
```

`RunContext` is the structured runtime input object. It carries:

- `inputs`: arbitrary structured run inputs
- `knowledge`: one aggregated `KnowledgeBundle`
- `extensions`: future-compatible extra fields

### Knowledge Contract

Knowledge is now expressed through a stable request/result pair:

```text
KnowledgeQuery -> Agent.resolve_knowledge(...) -> KnowledgeBundle -> RunContext
```

This stabilizes the public retrieval contract even though the execution engine has not yet been deeply rewired around retrieval internals.

## Internal Execution Boundary

The public API is adapted into the internal engine here:

- `loom/agent.py`: public config normalization and engine assembly
- `loom/runtime/engine.py`: execution engine and provider calls
- `loom/runtime/session.py`: session/run lifecycle

This split matters because it lets Loom evolve internals without reopening the public API contract every time.

## Architecture Reading Rule

When this page describes context, loop, heartbeat, safety, or orchestration internals, treat them as implementation layers underneath the public `Agent` API.

They explain how Loom works, not a second developer-facing API that applications should assemble directly.

## Module Reference

### `loom/agent.py`

- normalizes public config objects
- compiles public tool declarations into engine tools
- adapts policy, heartbeat, safety, runtime, and knowledge into engine inputs

### `loom/config.py`

- defines all public stable config and evidence objects
- holds the developer-facing API schema

### `loom/runtime/`

- `session.py`: `Session`, `Run`, `RunContext`, `RunResult`
- `engine.py`: `AgentEngine`, provider orchestration
- `loop.py`: reason/act/observe/delta loop
- `heartbeat.py`: watch-source driven sensing

### `loom/tools/`

- registry, execution, governance, builtin tools

### `loom/safety/`

- veto authority, permission hooks, constraints

### `loom/providers/`

- provider implementations and low-level completion params

## Historical Note

Older documents may still refer to:

- `loom/api`
- `AgentRuntime`
- `SessionHandle`
- `TaskHandle`
- `RunHandle`

Treat those as historical design material, not the current public API.
