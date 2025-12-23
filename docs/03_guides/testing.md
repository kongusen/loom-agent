# Testing Agents

Testing probabilistic agents requires a mix of deterministic unit tests and eval-based integration tests.

## Unit Testing Nodes

You can unit test a `Node` in isolation by mocking the `Dispatcher`.

```python
import pytest
from unittest.mock import AsyncMock
from loom.node.agent import AgentNode
from loom.protocol.cloudevents import CloudEvent

@pytest.mark.asyncio
async def test_agent_node_process():
    # 1. Mock Dispatcher
    mock_dispatcher = AsyncMock()
    
    # 2. Create Agent with Mock LLM
    agent = AgentNode("test-agent", mock_dispatcher)
    
    # 3. Simulate Event
    event = CloudEvent.create(
        source="user", 
        type="node.request", 
        data={"task": "hello"}
    )
    
    # 4. Run
    result = await agent.process(event)
    
    # 5. Assert
    assert result["response"] is not None
```

## Integration Testing (Evals)

For end-to-end reliability, run the agent against a dataset of tasks and grade the output.

### 1. Define Dataset
```json
[
  {"input": "Calculate 2+2", "expected": "4"},
  {"input": "Who is president?", "expected_contains": "Biden"}
]
```

### 2. Run Eval Loop
```python
for item in dataset:
    response = await app.run(item["input"], "agent")
    score = grader_llm.grade(response, item["expected"])
    print(f"Score: {score}")
```

## Mocking LLM Providers

Loom includes `MockLLMProvider` for deterministic testing.

```python
from loom.infra.llm.mock import MockLLMProvider

mock = MockLLMProvider(responses=[
    "Thought: I should use the calculator.",
    "Final Answer: 4"
])

agent = AgentNode(..., provider=mock)
```
