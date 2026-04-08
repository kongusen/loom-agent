# Loom vs. Other Frameworks

## Feature Comparison

| Feature | LangChain | AutoGen | CrewAI | **Loom** |
|---|---|---|---|---|
| Context pressure management | ❌ | ❌ | ❌ | ✅ |
| Five-partition context | ❌ | ❌ | ❌ | ✅ |
| Background heartbeat (H_b) | ❌ | ❌ | ❌ | ✅ |
| Structured R→A→O→Δ loop | ❌ | partial | ❌ | ✅ |
| Context renewal (disk paging) | ❌ | ❌ | ❌ | ✅ |
| Veto authority | ❌ | ❌ | ❌ | ✅ |
| Self-improvement (E1–E4) | ❌ | ❌ | ❌ | ✅ |
| Progressive skill loading | ❌ | ❌ | partial | ✅ |
| MCP integration | partial | ❌ | ❌ | ✅ |
| Multi-provider (Anthropic/OpenAI/Gemini) | ✅ | ✅ | ✅ | ✅ |
| Built-in retry + circuit breaker | partial | ❌ | ❌ | ✅ |

## Design Philosophy

**LangChain** — chains and pipelines. Great for linear workflows, but the model is a step in your pipeline, not an autonomous agent.

**AutoGen** — conversation-based multi-agent. Agents talk to each other, but context management and safety are left to you.

**CrewAI** — role-based crews. Easy to get started, but limited control over what the model sees and when.

**Loom** — agent API first. Application developers assemble one `AgentConfig`, run one `Agent`, and get structured sessions, runtime inputs, safety, heartbeat, and context control underneath that single public surface.

## Public API Positioning

Compared with other frameworks, Loom tries to keep the public contract narrower:

- one main assembly object: `AgentConfig`
- one main execution object: `Agent`
- one stateful continuity object: `Session`
- one run-scoped input object: `RunContext`

Everything else remains available, but advanced objects are intentionally pushed into `loom.config` and `loom.runtime` instead of competing with the top-level application path.
