# Application Cookbook

This section turns Loom's `0.8.x` public SDK into repeatable application patterns.

Use these pages when you already understand the basic API shape and want to build a real app without rediscovering the structure each time.

## Core Rule

Every pattern starts from the same public path:

```text
Agent + Model + Runtime + Capability
    -> Session / Run
    -> RunContext / RuntimeSignal
```

The cookbook varies only:

- which `Runtime` profile to use
- which `Capability` declarations to enable
- when to use `agent.run()` vs `agent.session(...)`
- what to pass through `RunContext`
- when to feed external events through `RuntimeSignal` / `SignalAdapter`

## Foundation Patterns

- [Single-Turn Assistant](single-turn-assistant.md)
- [Session Workflow](session-workflow.md)
- [Knowledge-Backed Answers](knowledge-backed-answers.md)
- [Guardrailed Tool Agent](guardrailed-tool-agent.md)
- [Monitoring Agent](monitoring-agent.md)

## Product Scenarios

- [Repo Copilot](repo-copilot.md)
- [Internal Docs QA](internal-docs-qa.md)
- [Ops Agent](ops-agent.md)
- [Approval Workflow](approval-workflow.md)

## Example Mapping

| Scenario | Start with |
|---|---|
| Single-turn assistant | `examples/01_hello_agent.py` |
| Session workflow | `examples/04_multi_task_session.py` |
| Knowledge-backed answers | `examples/00_agent_overview.py` |
| Guardrailed tool agent | `examples/12_heartbeat_and_safety.py` |
| Monitoring agent | `examples/12_heartbeat_and_safety.py` |
| Gateway, cron, or heartbeat adapter | `examples/16_signal_adapters.py` |
| Repo copilot | `examples/13_repo_copilot.py` |
| Internal docs QA | `examples/14_internal_docs_qa.py` |
| Approval workflow | `examples/15_approval_workflow.py` |

## Reading Order

1. Start with single-turn if your app answers one request at a time.
2. Move to session workflow when continuity matters.
3. Add knowledge when the answer must be grounded in explicit evidence.
4. Add capabilities when the agent needs files, web, shell, MCP, or skills.
5. Add governance when tools can have side effects.
6. Add signals when gateway, cron, heartbeat, or application events should affect runtime state.
7. Pick the closest product scenario and adapt it instead of starting from a blank file.
