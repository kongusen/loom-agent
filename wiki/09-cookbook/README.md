# Application Cookbook

This section turns Loom's public `Agent` API into repeatable application patterns.

Use these pages when you already understand the basic API shape and want to build a real app without rediscovering the structure each time.

## Core Rule

Every pattern in this cookbook starts from the same public path:

```text
AgentConfig -> Agent -> Session -> Run
```

The cookbook varies only:

- what goes into `AgentConfig`
- when to use `agent.run()` vs `agent.session(...)`
- what to pass through `RunContext`
- which advanced config objects to import from `loom.config`

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
| Repo copilot | `examples/13_repo_copilot.py` |
| Internal docs QA | `examples/14_internal_docs_qa.py` |
| Ops agent | `examples/12_heartbeat_and_safety.py` |
| Approval workflow | `examples/15_approval_workflow.py` |

## Reading Order

1. Start with single-turn if your app answers one request at a time.
2. Move to session workflow when continuity matters.
3. Add knowledge when the answer must be grounded in explicit evidence.
4. Add guardrails when tools can have side effects.
5. Add monitoring when heartbeat and safety must work together.
6. Pick the closest product scenario and adapt it instead of starting from a blank file.
