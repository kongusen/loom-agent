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

**Loom** — runtime-first. The framework manages context pressure, background sensing, and safety boundaries so the model can focus on reasoning. The Harness is the stage; the model is the actor.
