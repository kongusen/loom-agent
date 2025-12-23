# Error Handling & Debugging

Loom provides robust mechanisms for handling failures in asynchronous agent systems.

## Common Error Scenarios

### 1. `TimeoutError`
**Cause**: The agent or tool took longer than 30s (default) to respond.
**Fix**: Increase timeout in `LoomApp.run` or check for infinite loops.

```python
# Increase timeout
result = await app.run("task", "agent", timeout=60.0)
```

### 2. `Infinite Loop` (Context Rot)
**Cause**: Agent keeps repeating the same thought or tool call.
**Fix**:
- **Check System Prompt**: Ensure it has "Stop" conditions.
- **Use `BudgetInterceptor`**: Hard limit on tokens/steps.

### 3. Tool Failure
**Cause**: Tool code raised an exception.
**Result**: Agent sees "Tool Error: [Details]" in its context.
**Strategy**: Loom catches tool errors automatically and feeds them back to the LLM so it can retry or self-correct.

## Debugging Techniques

### 1. Enable Structured Logging
Loom uses `structlog`. Enable debug logs to see the flow of events.

```python
import logging
import structlog

structlog.configure(
    processors=[structlog.processors.JSONRenderer()],
    logger_factory=structlog.stdlib.LoggerFactory(),
)
logging.basicConfig(level=logging.DEBUG)
```

### 2. Trace Events
Every `CloudEvent` has a distinct `type` and `id`.
- `node.request`: Input to a node.
- `agent.thought`: The raw LLM reasoning trace.
- `tool.call`: The arguments sent to a tool.
- `tool.result`: The output from a tool.

Hook into the bus to print them:

```python
def print_trace(event):
    print(f"[{event.type}] {event.source} -> {event.subject}")

app.on("*", print_trace)
```
