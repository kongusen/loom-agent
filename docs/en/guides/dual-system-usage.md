# How to Solve Problems Using Dual System

> **Problem-oriented** - Learn to use System 1 and System 2 to solve different types of problems

## Overview

loom-agent's dual-system architecture provides two complementary problem-solving approaches:
- **System 1 (Fast Stream)**: Suitable for quick responses, conversational interaction
- **System 2 (Deep Thinking)**: Suitable for complex reasoning, multi-step analysis

## Basic Usage

### Default Mode: System 1 Only

By default, Agent only uses System 1 (fast streaming output):

```python
from loom.weave import create_agent, run

# Create Agent (Default only uses System 1)
agent = create_agent("assistant", role="General Assistant")

# Fast response
result = run(agent, "Hello, please introduce yourself")
print(result)
```

**Features**:
- Fast response
- Streaming output
- Suitable for simple conversation

### Enable System 2: Deep Thinking Mode

To enable System 2, you need to configure `ThinkingPolicy`:

```python
from loom.node.agent import AgentNode, ThinkingPolicy
from loom.api.main import LoomApp

# Create LoomApp
app = LoomApp()

# Configure System 2
thinking_policy = ThinkingPolicy(
    enabled=True,              # Enable deep thinking
    max_thoughts=3,            # Max 3 concurrent thoughts
    max_depth=2,               # Max recursion depth 2 levels
    trigger_words=["analyze", "reason", "deep"]  # Trigger words
)

# Create Agent with System 2 enabled
agent = AgentNode(
    node_id="deep-thinker",
    dispatcher=app.dispatcher,
    role="Deep Analyst",
    thinking_policy=thinking_policy
)

# Run task
result = await app.run(agent, "Please deeply analyze the root cause of this problem")
```

**Features**:
- Launches deep thinking in parallel
- Generates structured insights
- Suitable for complex problems

## ThinkingPolicy Configuration Options

### Core Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `enabled` | bool | False | Whether to enable System 2 |
| `max_thoughts` | int | None | Max concurrent thoughts (None=unlimited) |
| `max_depth` | int | None | Max recursion depth (None=unlimited) |
| `total_token_budget` | int | None | Token budget (None=unlimited) |
| `thought_timeout` | float | None | Thought timeout (seconds) |
| `trigger_words` | List[str] | [] | List of trigger words |
| `spawn_threshold` | float | 0.7 | Confidence threshold |

### Warning Thresholds (Soft Limits)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `warn_depth` | 3 | Depth warning threshold |
| `warn_thoughts` | 5 | Thought count warning threshold |
| `warn_timeout` | 10.0 | Timeout warning threshold (seconds) |

## Use Cases

### Scenario 1: Simple Conversation (System 1 Only)

**Suitable for**: Small talk, simple Q&A, fast response

```python
from loom.weave import create_agent, run

agent = create_agent("chatbot", role="Chat Assistant")
result = run(agent, "How is the weather today?")
```

**Features**: Fast, smooth, no deep thinking required

### Scenario 2: Complex Analysis (System 1 + System 2)

**Suitable for**: Data analysis, problem diagnosis, multi-perspective thinking

```python
from loom.node.agent import AgentNode, ThinkingPolicy
from loom.api.main import LoomApp

app = LoomApp()

# Enable deep thinking
thinking_policy = ThinkingPolicy(
    enabled=True,
    max_thoughts=5,
    max_depth=3,
    trigger_words=["analyze", "diagnose", "evaluate"]
)

agent = AgentNode(
    node_id="analyst",
    dispatcher=app.dispatcher,
    role="Data Analyst",
    thinking_policy=thinking_policy
)

result = await app.run(agent, "Analyze the root cause of this system performance degradation")
```

**Workflow**:
1. System 1 gives preliminary response quickly
2. System 2 launches deep analysis in parallel
3. Generates multiple thought nodes (e.g., check logs, analyze metrics, compare history)
4. Projects and merges all insights

### Scenario 3: Controlled Deep Thinking (Resource Limited)

**Suitable for**: Need deep thinking but cost controlled

```python
thinking_policy = ThinkingPolicy(
    enabled=True,
    max_thoughts=2,              # Limit concurrent thoughts
    max_depth=2,                 # Limit recursion depth
    total_token_budget=5000,     # Limit Token usage
    thought_timeout=30.0         # 30 seconds timeout
)

agent = AgentNode(
    node_id="budget-analyst",
    dispatcher=app.dispatcher,
    role="Cost-sensitive Analyst",
    thinking_policy=thinking_policy
)
```

**Features**:
- Balance depth and cost
- Avoid resource overconsumption
- Suitable for production environments

### Scenario 4: Trigger Word Mode (Smart Activation)

**Suitable for**: Automatically decide whether to enable System 2 based on task content

```python
thinking_policy = ThinkingPolicy(
    enabled=True,
    trigger_words=["analyze", "reason", "deep", "evaluate", "diagnose"],
    max_thoughts=3
)

agent = AgentNode(
    node_id="smart-agent",
    dispatcher=app.dispatcher,
    role="Smart Assistant",
    thinking_policy=thinking_policy
)

# Contains trigger word -> Start System 2
await app.run(agent, "Please deeply analyze this problem")

# Does not contain trigger word -> System 1 Only
await app.run(agent, "Hello")
```

**Features**:
- Automatically identify complex tasks
- Save unnecessary computation
- Smarter user experience

## Best Practices

### 1. Choose Appropriate Mode

| Task Type | Recommended Config |
|-----------|--------------------|
| Simple Conversation | System 1 only |
| Quick Q&A | System 1 only |
| Data Analysis | System 1 + System 2 |
| Problem Diagnosis | System 1 + System 2 |
| Multi-step Reasoning | System 1 + System 2 |
| Creative Generation | System 1 + System 2 |

### 2. Set Reasonable Limits

**Production Recommendations**:
```python
thinking_policy = ThinkingPolicy(
    enabled=True,
    max_thoughts=3,           # Avoid too much parallelism
    max_depth=2,              # Prevent infinite recursion
    total_token_budget=10000, # Control cost
    thought_timeout=60.0      # Avoid long waits
)
```

### 3. Optimize with Trigger Words

**Recommended Trigger Words**:
- Analysis: `["analyze", "evaluate", "diagnose", "check"]`
- Reasoning: `["reason", "derive", "prove", "explain"]`
- Depth: `["deep", "detailed", "comprehensive", "thorough"]`

### 4. Monitor and Debug

Observe System 2 status:
```python
# View cognitive state
print(f"Active thoughts: {len(agent.cognitive_state.active_thoughts)}")
print(f"State space dimensionality: {agent.cognitive_state.dimensionality()}")

# View completed thoughts
for thought in agent.cognitive_state.get_completed_thoughts():
    print(f"Thought {thought.id}: {thought.result}")
```

## FAQ

### Q1: When does System 2 start?

**A**: When `ThinkingPolicy.enabled=True`, System 2 starts if:
- Task contains trigger words (if `trigger_words` is configured)
- Or starts unconditionally (if `trigger_words` is empty)

### Q2: How to view System 2 output?

**A**: System 2 output is merged into final result via ProjectionOperator:
```python
# View projected insights
observables = agent.projector.project(agent.cognitive_state)
for obs in observables:
    print(f"Insight: {obs.content}")
```

### Q3: Will System 1 and System 2 conflict?

**A**: No. Two systems work in parallel:
- System 1 provides fast streaming output
- System 2 thinks deeply in background
- Finally merge results via projection

### Q4: How to control cost?

**A**: Use limit parameters:
- `max_thoughts`: Limit concurrent thoughts
- `max_depth`: Limit recursion depth
- `total_token_budget`: Limit Token usage
- `thought_timeout`: Limit thinking time

## Summary

Dual-system architecture provides flexible problem-solving approaches:

1. **System 1**: Fast, intuitive, suitable for simple tasks
2. **System 2**: Deep, rational, suitable for complex tasks
3. **Flexible Config**: Precise control via ThinkingPolicy
4. **Cost Controllable**: Multiple limit parameters protect resources

## Related Documentation

- [Architecture Design](../concepts/architecture.md) - Understand dual-system architecture
- [Cognitive Dynamics](../concepts/cognitive-dynamics.md) - Understand theoretical foundation
- [Create Agent](../tutorials/your-first-agent.md) - Basic tutorial
