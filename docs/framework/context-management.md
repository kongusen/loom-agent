# Context Management

## Overview

Context management is the **core capability** of any AI agent system. Loom's context management system prevents context degradation while maximizing agent intelligence through intelligent memory integration and token optimization.

**Key Goals**:
- Prevent context overflow (token limit violations)
- Prevent context corruption (irrelevant information)
- Maximize intelligence (include relevant context)
- Ensure consistency (predictable behavior)

## Architecture

### Context Building Flow

```
┌─────────────────────────────────────────────────────────┐
│                  Agent Execution Loop                    │
│                                                          │
│  while True:                                             │
│    messages = context_manager.build_context(task)       │
│    response = llm.chat(messages, tools)                 │
│    if not response.tool_calls: break                    │
│    execute_tools(response.tool_calls)                   │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│              TaskContextManager                          │
│                                                          │
│  1. Collect Context Sources                             │
│     ├─ L1 Memory (auto-included)                        │
│     ├─ External Knowledge Base (auto-queried)           │
│     └─ Current Task                                      │
│                                                          │
│  2. Convert to Messages                                  │
│     └─ Task → LLM Message Format                        │
│                                                          │
│  3. Apply Token Limits                                   │
│     └─ Fit to max_tokens constraint                     │
│                                                          │
│  4. Return Optimized Messages                            │
└─────────────────────────────────────────────────────────┘
```

## Context Structure

### Ordering

The context is built in a specific order to maximize effectiveness:

```
1. System Prompt (role: system)
2. L1 Memory (role: user/assistant) - Auto-included
3. External Knowledge (role: system) - Auto-queried
4. Available Tools (via tools parameter)
5. Current Task (role: user)
```

**Rationale**:
- **System Prompt**: Sets agent behavior and capabilities
- **L1 Memory**: Provides immediate conversation context
- **External Knowledge**: Injects relevant domain knowledge
- **Tools**: Defines available actions
- **Current Task**: Triggers agent reasoning

### Message Format

Messages follow the OpenAI/Anthropic standard format:

```python
{
    "role": "system" | "user" | "assistant",
    "content": "message content"
}
```

## Core Components

### TaskContextManager

**Location**: `loom/memory/task_context.py`

**Purpose**: Builds optimized LLM context from multiple sources.

**Key Features**:
- Automatic L1 inclusion
- External knowledge integration
- Token-aware truncation
- Message format conversion

**Configuration**:
```python
from loom.memory.task_context import TaskContextManager
from loom.memory.tokenizer import TokenCounter

context_manager = TaskContextManager(
    token_counter=TokenCounter(),
    sources=[memory_source, event_source],
    max_tokens=4000,
    system_prompt="You are a helpful AI assistant",
    knowledge_base=knowledge_base  # Optional
)
```

### Context Sources

**MemoryContextSource**:
```python
from loom.memory.task_context import MemoryContextSource

memory_source = MemoryContextSource(memory=loom_memory)
# Retrieves tasks from L1 and L2 layers
```

**EventBusContextSource**:
```python
from loom.memory.task_context import EventBusContextSource

event_source = EventBusContextSource(event_bus=event_bus)
# Retrieves thinking events and tool calls
```

### Message Converter

**Purpose**: Converts Task objects to LLM message format.

**Conversion Rules**:
```python
# Task with action="node.thinking" → assistant message
Task(action="node.thinking", parameters={"content": "I need to..."})
→ {"role": "assistant", "content": "I need to..."}

# Task with action="execute" → user message
Task(action="execute", parameters={"content": "Read file X"})
→ {"role": "user", "content": "Read file X"}

# Task with action="node.tool_call" → assistant message
Task(action="node.tool_call", parameters={"tool_name": "read_file"})
→ {"role": "assistant", "content": "[Calling read_file(...)]"}

# Task with action="node.tool_result" → omitted
# Tool results are not injected into LLM context by default to avoid echoing large outputs.
```

### Direct Message Protocol (Point-to-Point)

To avoid schema drift between modules, all point-to-point (direct) messages must follow a unified Task schema. Direct messages are indexed by `target_agent` / `target_node_id` and are prioritized in L1 context.

**Action**: `node.message`

**Required Fields**:
- `task.source_agent`: sender agent ID
- `task.target_agent`: target agent ID
- `task.parameters.content`: message content

**Optional Fields**:
- `task.parameters.target_node_id`: target node ID (if different from agent ID)
- `task.parameters.priority`: float 0.0–1.0 (default 0.5)
- `task.parameters.ttl_seconds`: time-to-live in seconds (if expired, message is ignored)
- `task.parameters.parent_task_id`: parent task ID for traceability
- `task.parameters.metadata`: free-form metadata

**Example**:
```python
from loom.runtime import Task

direct_msg = Task(
    task_id="task-123:event:node.message",
    source_agent="agent-a",
    target_agent="agent-b",
    action="node.message",
    parameters={
        "content": "Please focus on the database migration plan.",
        "priority": 0.8,
        "ttl_seconds": 600,
        "target_node_id": "agent-b",
        "parent_task_id": "task-123",
        "metadata": {"reason": "handoff"},
    },
)
```

**Notes**:
- Direct messages are treated as L1 context and should remain concise.
- If `ttl_seconds` is set, expired messages will not be returned by `query_by_target`.

## Token Management

### Token Counting

**TokenCounter** provides accurate token counting for different LLM providers.

**Usage**:
```python
from loom.memory.tokenizer import TokenCounter

counter = TokenCounter()
token_count = counter.count_messages(messages)
```

### Token Limit Strategy

When messages exceed `max_tokens`, the system applies a **recency-based truncation** strategy:

1. **Always preserve**: System message (if present)
2. **Always preserve**: Most recent N messages
3. **Discard**: Middle messages if needed

**Example**:
```python
# Before truncation (5000 tokens)
[system, msg1, msg2, msg3, msg4, msg5, msg6, msg7, msg8]

# After truncation to 4000 tokens
[system, msg6, msg7, msg8]  # Kept most recent messages
```

## Usage Examples

### Basic Usage

```python
from loom.memory.task_context import TaskContextManager
from loom.runtime import Task

# Build context for current task
current_task = Task(
    task_id="task_123",
    action="execute",
    parameters={"content": "Read file data.txt"}
)

messages = await context_manager.build_context(current_task)

# Messages ready for LLM
response = await llm.chat(messages, tools=available_tools)
```

### With Session ID

Loom does not define what a "session" is. The upper layer decides when to start or switch a session.  
When a `session_id` is present:
- L1/L2/L3 queries default to the same session
- EventBus direct/bus events are filtered by session
- L4 remains cross-session (no default filter)

```python
from loom.runtime import Task

current_task = Task(
    task_id="task_123",
    action="execute",
    parameters={"content": "Refactor the memory layer"},
    session_id="session-2026-01-28",
)
```

### Query Memory by Session

```python
# L2 session working memory
await executor.execute("query_l2_memory", {"limit": 10, "session_id": "session-2026-01-28"})

# L3 session summaries
await executor.execute("query_l3_memory", {"limit": 20, "session_id": "session-2026-01-28"})
```

### With External Knowledge

```python
from loom.providers.knowledge import VectorKnowledgeBase

# Create knowledge base
kb = VectorKnowledgeBase(embedding_provider, vector_store)

# Configure context manager with knowledge base
context_manager = TaskContextManager(
    token_counter=TokenCounter(),
    sources=[memory_source],
    knowledge_base=kb,  # Auto-queries relevant knowledge
    max_tokens=4000
)

# Knowledge is automatically included in context
messages = await context_manager.build_context(current_task)
```

## Best Practices

### Context Optimization

1. **L1 Auto-Inclusion**: Rely on automatic L1 inclusion for speed
2. **Lazy L2/L3/L4 Access**: Let LLM search when needed via tools
3. **Knowledge Base Integration**: Use auto-query for small, fast knowledge bases
4. **Token Budget**: Set appropriate max_tokens based on model limits

### Performance Tips

1. **Minimize Context Sources**: Only include necessary sources
2. **Optimize Knowledge Queries**: Keep knowledge base queries fast (<100ms)
3. **Monitor Token Usage**: Track actual token consumption
4. **Cache When Possible**: Reuse context for similar tasks

## Related Documentation

- [Memory System](../features/memory-system.md)
- [External Knowledge Base](../features/external-knowledge-base.md)
- [Search & Retrieval](../features/search-and-retrieval.md)
