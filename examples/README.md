# Examples

Runnable examples from simple to advanced. No API key needed for 01, 03, 04, 06, 07.

| File | Concept | API key? |
|---|---|---|
| [01_hello_agent.py](01_hello_agent.py) | Runtime → Session → Task → Run | No |
| [02_provider_config.py](02_provider_config.py) | Anthropic / OpenAI / Gemini provider | Yes |
| [03_events_and_artifacts.py](03_events_and_artifacts.py) | Event stream + artifact inspection | No |
| [04_multi_task_session.py](04_multi_task_session.py) | Multiple tasks, context passing | No |
| [05_multi_agent.py](05_multi_agent.py) | TaskPlanner + Coordinator orchestration | No |
| [06_evolution.py](06_evolution.py) | Self-improvement strategies E1–E4 | No |
| [07_context_pressure.py](07_context_pressure.py) | Context compression levels (ρ triggers) | No |

## Run

```bash
pip install loom-agent

python examples/01_hello_agent.py
python examples/06_evolution.py
python examples/07_context_pressure.py

# With a real LLM:
ANTHROPIC_API_KEY=sk-ant-... python examples/02_provider_config.py
```

## Docs

- [Quick Start](../wiki/01-getting-started/README.md)
- [Core Concepts](../wiki/02-core-concepts/README.md)
- [Multi-Agent](../wiki/04-multi-agent/README.md)
- [Self-Improvement](../wiki/06-self-improvement/README.md)
