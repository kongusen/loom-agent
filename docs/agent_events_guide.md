# Agent Events Guide (Loom 2.0)

## Overview

Loom 2.0 introduces a unified event system for streaming agent execution. Instead of waiting for a final response, you can now receive real-time updates about:

- Context assembly progress
- Document retrieval
- LLM token generation
- Tool execution
- Errors and recovery

This guide shows you how to use the AgentEvent system effectively.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Event Types](#event-types)
3. [Basic Usage Patterns](#basic-usage-patterns)
4. [Advanced Patterns](#advanced-patterns)
5. [Building Custom Event Producers](#building-custom-event-producers)
6. [Migration from Loom 1.0](#migration-from-loom-10)

---

## Quick Start

### Basic Example: Streaming Agent Execution

```python
from loom import Agent
from loom.core.events import AgentEventType

# Create agent
agent = Agent(llm=my_llm, tools=my_tools)

# Stream execution
async for event in agent.execute("Search for TODO comments in the codebase"):
    if event.type == AgentEventType.LLM_DELTA:
        # Print LLM output in real-time
        print(event.content, end="", flush=True)

    elif event.type == AgentEventType.TOOL_PROGRESS:
        # Show tool progress
        print(f"\n[Tool: {event.metadata['tool_name']}] {event.metadata['status']}")

    elif event.type == AgentEventType.AGENT_FINISH:
        # Final response
        print(f"\n✓ Completed: {event.content}")
```

### Backward Compatible API

If you just want the final result (like Loom 1.0):

```python
# Still works! Internally uses the new event system
result = await agent.run("Your prompt here")
print(result)
```

---

## Event Types

### Phase Events

Track execution phases:

```python
from loom.core.events import AgentEventType

# Phase lifecycle
PHASE_START       # A new phase started (e.g., "context_assembly")
PHASE_END         # A phase completed
```

**Example:**
```python
async for event in agent.execute(prompt):
    if event.type == AgentEventType.PHASE_START:
        print(f"Starting phase: {event.phase}")
    elif event.type == AgentEventType.PHASE_END:
        print(f"Completed phase: {event.phase} ({event.metadata.get('duration_ms')}ms)")
```

---

### Context Events

Track context assembly and memory management:

```python
CONTEXT_ASSEMBLY_START     # Starting to build system context
CONTEXT_ASSEMBLY_COMPLETE  # Context ready
COMPRESSION_APPLIED        # History was compressed to save tokens
```

**Example:**
```python
async for event in agent.execute(prompt):
    if event.type == AgentEventType.COMPRESSION_APPLIED:
        tokens_saved = event.metadata.get('tokens_saved', 0)
        print(f"Compressed history, saved {tokens_saved} tokens")
```

---

### RAG Events

Track document retrieval:

```python
RETRIEVAL_START     # Starting to retrieve documents
RETRIEVAL_PROGRESS  # Found documents (metadata contains doc info)
RETRIEVAL_COMPLETE  # Retrieval finished
```

**Example:**
```python
async for event in agent.execute(prompt):
    if event.type == AgentEventType.RETRIEVAL_PROGRESS:
        doc_title = event.metadata.get('doc_title')
        relevance = event.metadata.get('relevance_score')
        print(f"Retrieved: {doc_title} (relevance: {relevance:.2f})")
```

---

### LLM Events

Track language model interaction:

```python
LLM_START       # LLM call started
LLM_DELTA       # Streaming text chunk (event.content contains the text)
LLM_COMPLETE    # LLM call finished
LLM_TOOL_CALLS  # LLM requested tool calls
```

**Example: Real-time Streaming**
```python
async for event in agent.execute(prompt):
    if event.type == AgentEventType.LLM_DELTA:
        # Print tokens as they arrive
        print(event.content, end="", flush=True)
```

**Example: Collect Full Response**
```python
from loom.core.events import EventCollector

collector = EventCollector()

async for event in agent.execute(prompt):
    collector.add(event)

# Reconstruct full LLM output
full_text = collector.get_llm_content()
print(full_text)
```

---

### Tool Events

Track tool execution:

```python
TOOL_CALLS_START       # Starting to execute tool calls
TOOL_EXECUTION_START   # Individual tool started
TOOL_PROGRESS          # Progress update from tool
TOOL_RESULT            # Tool completed successfully
TOOL_ERROR             # Tool execution failed
```

**Example: Tool Progress**
```python
async for event in agent.execute(prompt):
    if event.type == AgentEventType.TOOL_EXECUTION_START:
        tool_name = event.tool_call.name
        print(f"\n▶ Running {tool_name}...")

    elif event.type == AgentEventType.TOOL_PROGRESS:
        status = event.metadata['status']
        print(f"  {status}")

    elif event.type == AgentEventType.TOOL_RESULT:
        result = event.tool_result
        if result.is_error:
            print(f"  ✗ Failed: {result.content}")
        else:
            print(f"  ✓ Completed in {result.execution_time_ms:.1f}ms")
```

---

### Agent Events

Track overall agent state:

```python
ITERATION_START          # New iteration started (for multi-turn)
ITERATION_END            # Iteration completed
AGENT_FINISH             # Agent execution finished
MAX_ITERATIONS_REACHED   # Hit iteration limit
```

**Example:**
```python
async for event in agent.execute(prompt):
    if event.type == AgentEventType.ITERATION_START:
        print(f"Iteration {event.iteration}/{agent.max_iterations}")

    elif event.type == AgentEventType.MAX_ITERATIONS_REACHED:
        print("⚠ Maximum iterations reached")
```

---

### Error Events

Track errors and recovery:

```python
ERROR               # Error occurred
RECOVERY_ATTEMPT    # Attempting to recover
RECOVERY_SUCCESS    # Recovery succeeded
RECOVERY_FAILED     # Recovery failed
```

**Example:**
```python
async for event in agent.execute(prompt):
    if event.type == AgentEventType.ERROR:
        error = event.error
        print(f"Error: {type(error).__name__}: {str(error)}")

    elif event.type == AgentEventType.RECOVERY_ATTEMPT:
        strategy = event.metadata.get('strategy')
        print(f"Attempting recovery: {strategy}")
```

---

## Basic Usage Patterns

### Pattern 1: Simple Streaming

Print LLM output as it arrives:

```python
async for event in agent.execute(prompt):
    if event.type == AgentEventType.LLM_DELTA:
        print(event.content, end="", flush=True)
    elif event.type == AgentEventType.AGENT_FINISH:
        print("\n✓ Done")
```

---

### Pattern 2: Progress Indicators

Show a progress bar or spinner:

```python
from rich.console import Console
from rich.progress import Progress

console = Console()

async with Progress() as progress:
    task = progress.add_task("Processing...", total=None)

    async for event in agent.execute(prompt):
        if event.type == AgentEventType.PHASE_START:
            progress.update(task, description=f"Phase: {event.phase}")

        elif event.type == AgentEventType.TOOL_PROGRESS:
            tool_name = event.metadata['tool_name']
            status = event.metadata['status']
            progress.update(task, description=f"[{tool_name}] {status}")

        elif event.type == AgentEventType.AGENT_FINISH:
            progress.update(task, completed=100, description="✓ Completed")
```

---

### Pattern 3: Collect All Events

Store events for analysis:

```python
from loom.core.events import EventCollector

collector = EventCollector()

async for event in agent.execute(prompt):
    collector.add(event)

# Analyze later
print(f"Total events: {len(collector.events)}")
print(f"Tool results: {len(collector.get_tool_results())}")
print(f"Errors: {len(collector.get_errors())}")
print(f"Final response: {collector.get_final_response()}")
```

---

### Pattern 4: Selective Handling

Only handle specific event types:

```python
async for event in agent.execute(prompt):
    # Only care about tool events
    if event.is_tool_event():
        if event.type == AgentEventType.TOOL_RESULT:
            print(f"Tool {event.tool_result.tool_name}: {event.tool_result.content}")

    # And final response
    elif event.type == AgentEventType.AGENT_FINISH:
        print(f"Final: {event.content}")
```

---

## Advanced Patterns

### Pattern 5: Separate LLM and Tool Output

Display LLM reasoning and tool results differently:

```python
async for event in agent.execute(prompt):
    if event.is_llm_content():
        # LLM reasoning in italic
        print(f"\033[3m{event.content}\033[0m", end="")

    elif event.type == AgentEventType.TOOL_RESULT:
        # Tool results in bold
        tool_name = event.tool_result.tool_name
        content = event.tool_result.content
        print(f"\n\033[1m[{tool_name}]\033[0m\n{content}\n")
```

---

### Pattern 6: Event Filtering

Create custom event filters:

```python
def is_retrieval_event(event):
    return event.type.value.startswith("retrieval_")

def is_error_related(event):
    return event.type in {
        AgentEventType.ERROR,
        AgentEventType.RECOVERY_ATTEMPT,
        AgentEventType.RECOVERY_SUCCESS,
        AgentEventType.RECOVERY_FAILED
    }

async for event in agent.execute(prompt):
    if is_retrieval_event(event):
        print(f"RAG: {event.type.value}")

    elif is_error_related(event):
        print(f"⚠ {event.type.value}")
```

---

### Pattern 7: Event Logging

Log all events for debugging:

```python
import logging

logger = logging.getLogger("agent_events")

async for event in agent.execute(prompt):
    logger.debug(
        f"Event: {event.type.value}",
        extra={
            "phase": event.phase,
            "iteration": event.iteration,
            "metadata": event.metadata
        }
    )

    # Also handle events normally
    if event.type == AgentEventType.LLM_DELTA:
        print(event.content, end="")
```

---

### Pattern 8: Event Metrics

Track performance metrics:

```python
import time

class EventMetrics:
    def __init__(self):
        self.phase_times = {}
        self.tool_times = {}
        self.start_time = None

    def track(self, event):
        if event.type == AgentEventType.PHASE_START:
            self.phase_times[event.phase] = time.time()

        elif event.type == AgentEventType.PHASE_END:
            duration = time.time() - self.phase_times[event.phase]
            print(f"Phase '{event.phase}': {duration*1000:.1f}ms")

        elif event.type == AgentEventType.TOOL_RESULT:
            exec_time = event.tool_result.execution_time_ms
            tool_name = event.tool_result.tool_name
            self.tool_times[tool_name] = exec_time
            print(f"Tool '{tool_name}': {exec_time:.1f}ms")

metrics = EventMetrics()

async for event in agent.execute(prompt):
    metrics.track(event)
```

---

## Building Custom Event Producers

### Create Your Own Event-Producing Components

```python
from typing import AsyncGenerator
from loom.core.events import AgentEvent, AgentEventType
from loom.interfaces.event_producer import EventProducer

class CustomRetriever(EventProducer):
    """Custom document retriever that produces events"""

    async def produce_events(self) -> AsyncGenerator[AgentEvent, None]:
        yield AgentEvent(type=AgentEventType.RETRIEVAL_START)

        # Simulate retrieval
        for i in range(5):
            yield AgentEvent(
                type=AgentEventType.RETRIEVAL_PROGRESS,
                metadata={
                    "doc_index": i,
                    "doc_title": f"Document {i}",
                    "relevance_score": 0.9 - i * 0.1
                }
            )

        yield AgentEvent(
            type=AgentEventType.RETRIEVAL_COMPLETE,
            metadata={"total_docs": 5}
        )

# Usage
retriever = CustomRetriever()

async for event in retriever.produce_events():
    if event.type == AgentEventType.RETRIEVAL_PROGRESS:
        print(f"Found: {event.metadata['doc_title']}")
```

---

## Migration from Loom 1.0

### Loom 1.0 (Non-streaming)

```python
# Old way
agent = Agent(llm=llm, tools=tools)
result = await agent.run(prompt)
print(result)
```

### Loom 2.0 (Backward Compatible)

```python
# Still works!
agent = Agent(llm=llm, tools=tools)
result = await agent.run(prompt)
print(result)
```

### Loom 2.0 (New Streaming API)

```python
# New way - full control
agent = Agent(llm=llm, tools=tools)

async for event in agent.execute(prompt):
    if event.type == AgentEventType.LLM_DELTA:
        print(event.content, end="")
    elif event.type == AgentEventType.AGENT_FINISH:
        print("\n✓ Done")
```

### Migration Checklist

- ✅ `agent.run()` still works (no changes needed)
- ✅ Switch to `agent.execute()` for streaming when ready
- ✅ Use `EventCollector` to collect events if needed
- ✅ No breaking changes to existing code

---

## Best Practices

### 1. Always Handle Terminal Events

```python
async for event in agent.execute(prompt):
    # Handle normal events
    if event.type == AgentEventType.LLM_DELTA:
        print(event.content, end="")

    # Always handle terminal events
    if event.is_terminal():
        if event.type == AgentEventType.ERROR:
            print(f"\n✗ Error: {event.error}")
        elif event.type == AgentEventType.AGENT_FINISH:
            print("\n✓ Success")
        break
```

### 2. Use EventCollector for Complex Logic

```python
collector = EventCollector()

async for event in agent.execute(prompt):
    collector.add(event)

    # Simple real-time display
    if event.type == AgentEventType.LLM_DELTA:
        print(event.content, end="")

# Complex analysis after completion
llm_content = collector.get_llm_content()
tool_results = collector.get_tool_results()
errors = collector.get_errors()
```

### 3. Handle Errors Gracefully

```python
try:
    async for event in agent.execute(prompt):
        if event.type == AgentEventType.ERROR:
            error = event.error
            if isinstance(error, RecoverableError):
                print("⚠ Retrying...")
            else:
                raise error

        elif event.type == AgentEventType.RECOVERY_SUCCESS:
            print("✓ Recovered from error")
except Exception as e:
    print(f"Fatal error: {e}")
```

---

## Summary

The AgentEvent system gives you:

✅ **Real-time streaming** - See LLM output as it generates
✅ **Progress visibility** - Track tool execution, retrieval, etc.
✅ **Fine-grained control** - Handle each event type differently
✅ **Backward compatibility** - Old code still works
✅ **Extensibility** - Build custom event producers

For more examples, see:
- `tests/unit/test_agent_events.py` - Comprehensive test suite
- `examples/streaming_demo.py` - Full demo application
- `docs/api_reference.md` - Complete API documentation
