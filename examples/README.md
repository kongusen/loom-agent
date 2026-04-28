# Examples

Runnable examples that all use the current public `Agent` API.

| File | Concept | API key? |
|---|---|---|
| [00_agent_overview.py](00_agent_overview.py) | Single-agent public API overview | Mixed |
| [01_hello_agent.py](01_hello_agent.py) | Minimal `Agent -> run()` | No |
| [02_provider_config.py](02_provider_config.py) | `Model` and `Generation` | Yes |
| [03_events_and_artifacts.py](03_events_and_artifacts.py) | `Session`, `Run`, events, artifacts | No |
| [04_multi_task_session.py](04_multi_task_session.py) | Stateful sessions and `RunContext` | No |
| [12_heartbeat_and_safety.py](12_heartbeat_and_safety.py) | Heartbeat, watch config, safety rules | No |
| [13_repo_copilot.py](13_repo_copilot.py) | End-to-end repo copilot app pattern | No |
| [14_internal_docs_qa.py](14_internal_docs_qa.py) | End-to-end grounded docs QA pattern | No |
| [15_approval_workflow.py](15_approval_workflow.py) | End-to-end approval workflow pattern | No |
| [16_signal_adapters.py](16_signal_adapters.py) | Gateway/cron/heartbeat-style events normalized as `RuntimeSignal` | No |
| [17_runtime_kernel_platform.py](17_runtime_kernel_platform.py) | Runtime kernel plus 7 mechanisms in one platform-style agent | Mixed |

## Public API Shape

```text
Agent(...)
    -> run()
    -> stream()
    -> receive(...)
    -> session(SessionConfig(...))
          -> Session
                -> start()/run()/stream()/receive()
```

## Run

```bash
pip install loom-agent

python examples/01_hello_agent.py
python examples/03_events_and_artifacts.py
python examples/04_multi_task_session.py
python examples/13_repo_copilot.py
python examples/14_internal_docs_qa.py
python examples/15_approval_workflow.py
python examples/16_signal_adapters.py
python examples/17_runtime_kernel_platform.py

# With a real provider:
ANTHROPIC_API_KEY=sk-ant-... python examples/02_provider_config.py
```

## Documentation

- [Getting Started](../wiki/01-getting-started/README.md)
- [Cookbook](../wiki/09-cookbook/README.md)
- [API Reference](../wiki/07-api-reference/README.md)
- [Architecture](../wiki/Architecture.md)

## Scenario Mapping

| If you are building... | Start with |
|---|---|
| Single-turn assistant | [01_hello_agent.py](01_hello_agent.py) |
| Session workflow | [04_multi_task_session.py](04_multi_task_session.py) |
| Knowledge-backed answers | [00_agent_overview.py](00_agent_overview.py) |
| Guardrailed tool agent | [12_heartbeat_and_safety.py](12_heartbeat_and_safety.py) |
| Monitoring or ops agent | [12_heartbeat_and_safety.py](12_heartbeat_and_safety.py) |
| Gateway, cron, or heartbeat adapter | [16_signal_adapters.py](16_signal_adapters.py) |
| Repo copilot | [13_repo_copilot.py](13_repo_copilot.py) |
| Internal docs QA | [14_internal_docs_qa.py](14_internal_docs_qa.py) |
| Approval workflow | [15_approval_workflow.py](15_approval_workflow.py) |
| Runtime kernel platform | [17_runtime_kernel_platform.py](17_runtime_kernel_platform.py) |

## Note

If an older note or example mentions `AgentRuntime`, `TaskHandle`, `RunHandle`, or `create_agent(AgentConfig(...))` as the main path, treat it as historical material. The supported 0.8.x application path is `Agent + Model + Runtime/Capability + Session/RunContext`.
