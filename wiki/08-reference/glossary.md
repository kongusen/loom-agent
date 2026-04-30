# Glossary

| Term | Definition |
|---|---|
| **Agent** | The single public Loom runtime object, usually created with direct `Agent(...)` keyword fields. |
| **AgentConfig** | Advanced configuration object used when direct `Agent(...)` fields are not enough. |
| **Session** | A stateful interaction scope created by `agent.session(...)`. |
| **Run** | One execution inside a session. |
| **RunContext** | Structured run-scoped inputs, including `inputs` and optional `knowledge`. |
| **KnowledgeQuery** | A stable retrieval request object used by `agent.resolve_knowledge(...)`. |
| **KnowledgeBundle** | Aggregated retrieval result attached to one run through `RunContext`. |
| **ToolSpec** | Stable public tool declaration produced manually or through `@tool`. |
| **PolicyConfig** | Top-level governance config for one agent. |
| **RuntimeConfig** | Top-level runtime config for limits, features, and fallback behavior. |
| **Generation** | Model generation controls such as temperature and output token limit. |
| **Harness (Ψ)** | Safety/control layer that sets boundaries and holds veto power. |
| **Context (C)** | The agent's working perception surface managed by `ContextManager`. |
| **ρ (rho)** | Context pressure = `token_count / max_tokens`. |
| **L\*** | The execution loop: `(Reason → Act → Observe → Δ)*`. |
| **H_b** | Heartbeat: independent background sensing layer. |
| **Veto** | A hard block enforced through `VetoAuthority`. |
