# Loom Package Layout

Loom exposes one public SDK API centered on `Agent`.

```python
from loom import Agent, Capability, Model, Runtime

agent = Agent(
    model=Model.anthropic("claude-sonnet-4"),
    instructions="You are a coding assistant",
    capabilities=[
        Capability.files(read_only=True),
        Capability.web(),
    ],
    runtime=Runtime.sdk(),
)

result = await agent.run("Inspect this repository")
print(result.output)
```

## Import Layers

Use the package in three layers:

- `loom`: primary application-facing entry point
- `loom.config`: advanced configuration and compatibility objects
- `loom.runtime`: runtime mechanism contracts and internals

Typical application imports stay small:

```python
from loom import Agent, Capability, Model, Runtime, SessionConfig, RunContext, tool
```

Compatibility imports such as `AgentConfig`, `ModelRef`, `GenerationConfig`, and `create_agent()` remain available through `0.8.x`, but new code should prefer `Agent(...)`.

## Package Structure

- `agent.py` - public Agent API and compatibility factory
- `config.py` - public config facade and 0.8 aliases
- `runtime/` - sessions, runs, engine, signals, capabilities, policies
- `context/` - context partitions, compression, renewal
- `memory/` - session, semantic, persistent memory
- `tools/` - registry, execution, governance
- `safety/` - permissions, hooks, veto authority
- `orchestration/` - planning and multi-agent coordination adapters
- `ecosystem/` - skills, plugins, MCP integration
- `providers/` - model provider implementations
