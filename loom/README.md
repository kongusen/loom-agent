# Loom Package Layout

Loom exposes one public SDK API centered on `Agent`.

```python
from loom import Agent, Files, Model, Runtime, Web

agent = Agent(
    model=Model.anthropic("claude-sonnet-4"),
    instructions="You are a coding assistant",
    capabilities=[
        Files(read_only=True),
        Web.enabled(),
    ],
    runtime=Runtime.sdk(),
)

result = await agent.run("Inspect this repository")
print(result.output)
```

## Import Layers

Use the package in three layers:

- `loom`: primary application-facing entry point
- `loom.config`: advanced configuration objects
- `loom.runtime`: runtime mechanism contracts and internals

Typical application imports stay small:

```python
from loom import Agent, Files, Model, Runtime, SessionConfig, RunContext, Web, tool
```

Application code should use `Agent(...)`; lower-level configuration objects remain under `loom.config`.

## Package Structure

- `agent.py` - public Agent API
- `config.py` - public config facade
- `runtime/` - sessions, runs, engine, signals, capabilities, policies
- `context/` - context partitions, compression, renewal
- `memory/` - session, semantic, persistent memory
- `tools/` - registry, execution, governance
- `safety/` - permissions, hooks, veto authority
- `orchestration/` - planning and multi-agent coordination adapters
- `ecosystem/` - skills, plugins, MCP integration
- `providers/` - model provider implementations
