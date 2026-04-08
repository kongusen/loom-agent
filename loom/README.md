# Loom Package Layout

Loom exposes one public API centered on `Agent`.

```python
from loom import AgentConfig, ModelRef, create_agent

agent = create_agent(
    AgentConfig(
        model=ModelRef.anthropic("claude-sonnet-4"),
        instructions="You are a coding assistant",
    )
)

result = await agent.run("Inspect this repository")
print(result.output)
```

## Import Layers

Use the package in two layers:

- `loom`: the primary application-facing entry point
- `loom.config` and `loom.runtime`: advanced configuration and runtime objects

Typical application imports stay small:

```python
from loom import AgentConfig, ModelRef, SessionConfig, RunContext, create_agent, tool
```

When you need richer configuration, import it explicitly from submodules:

```python
from loom.config import PolicyConfig, MemoryConfig, RuntimeConfig, HeartbeatConfig
from loom.runtime import Session, Run, RunResult
```

## Package Structure

- `agent.py` - public Agent API
- `config.py` - stable public configuration DSL
- `runtime/` - sessions, runs, engine, loop, heartbeat
- `context/` - context partitions, compression, renewal
- `memory/` - session, semantic, persistent memory
- `tools/` - registry, execution, governance
- `safety/` - permissions, hooks, veto authority
- `orchestration/` - planning and multi-agent coordination
- `ecosystem/` - skills, plugins, MCP integration
- `providers/` - model provider implementations
