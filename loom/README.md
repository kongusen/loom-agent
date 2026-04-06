# Loom 0.7.1

hernss Agent Framework Implementation

## Architecture

Based on axiom system: **A = ⟨C, M, L*, H_b, S, Ψ⟩**

- **C**: Context - Five-partition structure
- **M**: Memory - (M_s, M_f, M_w)
- **L***: Loop - (Reason → Act → Observe → Δ)*
- **H_b**: Heartbeat - Independent perception layer
- **S**: Skill - Progressive capability system
- **Ψ**: Harness - Runtime with veto power

## Installation

```bash
pip install -e .
```

## Quick Start

```python
from loom import Agent
from loom.providers import AnthropicProvider

provider = AnthropicProvider(api_key="your-key")
agent = Agent(provider)

result = await agent.run("Your goal here")
```

## Directory Structure

- `agent/` - Agent core (A = Model ∘ Ψ)
- `context/` - Context management (C)
- `execution/` - Execution loop (L*, H_b)
- `memory/` - Memory system (M)
- `tools/` - Tool system
- `capabilities/` - Skill system (S)
- `orchestration/` - Multi-agent coordination
- `safety/` - Security and constraints
- `providers/` - LLM providers
