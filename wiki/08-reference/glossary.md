# Glossary

| Term | Definition |
|---|---|
| **Agent** | `A = ⟨C, M, L*, H_b, S, Ψ⟩` — the six-component model of an autonomous agent |
| **Harness (Ψ)** | The framework layer that builds the environment and holds veto power. Never replaces model decisions. |
| **Context (C)** | The agent's only perception interface. Five partitions, managed by `ContextManager`. |
| **ρ (rho)** | Context pressure = `token_count / max_tokens`. Hard limit at 1.0 triggers renewal. |
| **L\*** | The execution loop: `(Reason → Act → Observe → Δ)*` |
| **H_b** | Heartbeat — independent background sensing thread running parallel to L* |
| **Δ (Delta)** | The decision phase of L*: continue / goal_reached / renew / decompose / harness |
| **d_max** | Maximum sub-agent recursion depth. Hard constraint enforced by `SubAgentManager`. |
| **Skill (S)** | A progressively loaded capability unit. Only injected into C_skill when task matches. |
| **M_f** | Filesystem memory — the shared substrate for multi-agent communication (Theorem 2) |
| **Renew** | Context disk paging: snapshot C_working → M_f, compress history, rebuild context |
| **Veto** | Ψ's safety valve — blocks any tool call via `VetoAuthority`. Use sparingly. |
| **E1–E4** | Four self-improvement strategies: Tool Learning, Policy Optimization, Constraint Hardening, Amoeba Split |
| **RunHandle** | The object returned by `task.start()` — controls and observes a running agent |
| **ArtifactStore** | Stores outputs produced during a run, retrievable via `run.artifacts()` |
