# Coding Agent Guide for loom-agent v0.1.1

**Target Audience**: AI Coding Assistants (Claude Code, GitHub Copilot, Cursor, etc.)

**Purpose**: Enable AI agents to effectively assist developers with loom-agent framework.

**Version**: v0.1.1  
**Last Updated**: 2024-12-12

---

## 🆕 What's New in v0.1.1

**Stream-First Architecture - Complete**

v0.1.1 achieves 100% architectural consistency across ALL components:

| Component | v0.1.0 | v0.1.1 | Status |
|-----------|--------|--------|--------|
| LLM | ABC classes | Protocol | ✅ Complete |
| Agent | Basic API | `execute()` streaming | ✅ Complete |
| Crew | No streaming | `kickoff_stream()` | ✅ Complete |
| Memory | ABC classes | `*_stream()` Protocol | 🆕 **NEW** |
| Context | Sync only | `assemble_stream()` | 🆕 **NEW** |
| Compression | Sync only | `compress_stream()` | 🆕 **NEW** |

**Key Benefits**:
- ✅ Real-time progress visibility for ALL operations  
- ✅ Complete observability (18 new event types)  
- ✅ Backward compatible (convenience wrappers preserved)  
- ✅ Better debugging (see retry logic, fallbacks, exclusions)

---

## 📋 Quick Start Templates

### Template 1: Basic Agent (30 seconds)

```python
import asyncio
from loom import agent

async def main():
    my_agent = agent(
        provider="openai",
        model="gpt-4",
        system_instructions="You are a helpful assistant."
    )
    result = await my_agent.run("What is loom-agent?")
    print(result)

asyncio.run(main())
```

---

### Template 2: Streaming Agent with Real-time Progress

```python
from loom import agent
from loom.core.events import AgentEventType

async def main():
    my_agent = agent(provider="openai", model="gpt-4")

    async for event in my_agent.execute("Explain quantum computing"):
        if event.type == AgentEventType.LLM_DELTA:
            print(event.content, end="", flush=True)
        elif event.type == AgentEventType.TOOL_EXECUTION_START:
            print(f"\n🔧 Tool: {event.metadata['tool_name']}")
        elif event.type == AgentEventType.AGENT_FINISH:
            print("\n✅ Done!")

asyncio.run(main())
```

**When to use**: Long tasks, interactive UIs, need real-time feedback.

---

### Template 3: Production Agent with HITL

```python
from pathlib import Path
from loom import agent
from loom.core.lifecycle_hooks import HITLHook
from loom.builtin.tools import WriteFileTool, BashTool

hitl_hook = HITLHook(
    dangerous_tools=["bash", "write_file"],
    ask_user_callback=lambda msg: input(f"⚠️  {msg}\nAllow? (y/n): ") == "y"
)

production_agent = agent(
    provider="openai",
    model="gpt-4",
    tools=[WriteFileTool(), BashTool()],
    enable_persistence=True,
    journal_path=Path("./logs"),
    hooks=[hitl_hook],
    thread_id="user-session-123"
)

result = await production_agent.run("Create a backup script")
```

---

## 🆕 v0.1.1 Stream-First Features

### 1. Memory Streaming API

```python
from loom.builtin.memory import PersistentMemory
from loom.core.types import Message
from loom.core.events import AgentEventType

memory = PersistentMemory(persist_dir=".loom", enable_persistence=True)

# Stream memory operations - see disk I/O in real-time
async for event in memory.add_message_stream(
    Message(role="user", content="Hello!")
):
    if event.type == AgentEventType.MEMORY_SAVE_START:
        print("💾 Saving...")
    elif event.type == AgentEventType.MEMORY_SAVE_COMPLETE:
        print(f"✅ Saved to {event.metadata['file']}")

# Convenience wrapper (backward compatible)
await memory.add_message(Message(role="user", content="Hello!"))
```

**Benefits**: Disk I/O visibility, backup tracking, debug persistence issues.

---

### 2. Context Assembly Streaming

```python
from loom.core.context_assembly import ContextAssembler, ComponentPriority
from loom.core.events import AgentEventType

assembler = ContextAssembler(max_tokens=4000)

assembler.add_component(
    "system", system_prompt,
    priority=ComponentPriority.CRITICAL,
    truncatable=False
)

assembler.add_component(
    "docs", large_docs,
    priority=ComponentPriority.HIGH,
    truncatable=True
)

# Stream assembly - see what gets included/excluded/truncated
async for event in assembler.assemble_stream():
    if event.type == AgentEventType.CONTEXT_COMPONENT_INCLUDED:
        print(f"✅ {event.metadata['component_name']} ({event.metadata['token_count']} tokens)")

    elif event.type == AgentEventType.CONTEXT_COMPONENT_TRUNCATED:
        original = event.metadata['original_tokens']
        truncated = event.metadata['truncated_tokens']
        print(f"✂️  Truncated: {original} → {truncated} tokens")

    elif event.type == AgentEventType.CONTEXT_COMPONENT_EXCLUDED:
        print(f"❌ Excluded: {event.metadata['component_name']}")

    elif event.type == AgentEventType.CONTEXT_ASSEMBLY_COMPLETE:
        utilization = event.metadata['utilization']
        print(f"📦 Utilization: {utilization:.1%}")
```

**Benefits**: Understand exclusions, debug token issues, optimize priorities.

---

### 3. Compression Streaming with Retry Visibility

```python
from loom.core.compression_manager import CompressionManager
from loom.core.events import AgentEventType

compressor = CompressionManager(llm=llm, max_retries=3)

# Stream compression - see retry and fallback logic
async for event in compressor.compress_stream(messages):
    if event.type == AgentEventType.COMPRESSION_START:
        original = event.metadata['original_tokens']
        target = event.metadata['target_tokens']
        print(f"🗜️  Compressing {original} → {target} tokens...")

    elif event.type == AgentEventType.COMPRESSION_PROGRESS:
        if event.metadata['status'] == 'retry':
            attempt = event.metadata['attempt']
            delay = event.metadata['backoff_delay']
            print(f"⚠️  Retry {attempt}/3 (backoff: {delay}s)")

    elif event.type == AgentEventType.COMPRESSION_FALLBACK:
        method = event.metadata['fallback_method']
        print(f"🔄 Fallback to {method}")

    elif event.type == AgentEventType.COMPRESSION_COMPLETE:
        compressed = event.metadata['compressed_tokens']
        ratio = event.metadata['reduction_ratio']
        print(f"✅ {compressed} tokens ({ratio:.1%} reduction)")
```

**Benefits**: See why compression fails, track retries, understand fallbacks.

---

### 4. Crew Streaming (Enhanced)

```python
from loom.crew import Crew, Role, Task, OrchestrationPlan, OrchestrationMode
from loom.core.events import AgentEventType

crew = Crew(roles=[...], llm=llm)

plan = OrchestrationPlan(
    tasks=[Task(...), Task(...), Task(...)],
    mode=OrchestrationMode.SEQUENTIAL
)

# Stream crew execution - see task progress
async for event in crew.kickoff_stream(plan):
    if event.type == AgentEventType.CREW_TASK_START:
        print(f"🚀 Starting: {event.metadata['task_id']}")
    elif event.type == AgentEventType.CREW_TASK_COMPLETE:
        print(f"✅ Completed: {event.metadata['task_id']}")

# Convenience wrapper
results = await crew.kickoff(plan)
```

---

## ✅ Best Practices

### 1. Use Streaming for Long Tasks

```python
# ✅ DO - Real-time progress
async for event in agent.execute("Complex task"):
    if event.type == AgentEventType.LLM_DELTA:
        print(event.content, end="")

# ❌ DON'T - Black box execution
result = await agent.run("Complex task")  # No visibility
```

---

### 2. Enable Persistence in Production

```python
# ✅ DO
agent(
    llm=llm,
    enable_persistence=True,
    journal_path=Path("./logs"),
    thread_id=f"user-{user_id}-{session_id}"
)

# ❌ DON'T
agent(llm=llm)  # Loses progress on crash
```

---

### 3. Add HITL for Dangerous Tools

```python
# ✅ DO
hitl = HITLHook(dangerous_tools=["bash", "write_file", "delete_file"])
agent(llm=llm, tools=all_tools, hooks=[hitl])

# ❌ DON'T
agent(llm=llm, tools=[BashTool(), DeleteFileTool()])
```

---

### 4. Monitor Context Budget

```python
# ✅ DO
from loom.core import ContextDebugger

debugger = ContextDebugger(enable_auto_export=True)
agent(llm=llm, tools=tools, context_debugger=debugger)

# After execution
print(debugger.explain_iteration(10))

# ❌ DON'T
agent(llm=llm, tools=tools)  # No context visibility
```

---

## 🔍 Quick Reference

### v0.1.1 Event Types (Complete List)

```python
from loom.core.events import AgentEventType

# Agent lifecycle
AgentEventType.AGENT_START
AgentEventType.AGENT_FINISH
AgentEventType.ITERATION_START

# LLM events
AgentEventType.LLM_DELTA
AgentEventType.LLM_COMPLETE
AgentEventType.LLM_TOOL_CALLS

# Tool events
AgentEventType.TOOL_EXECUTION_START
AgentEventType.TOOL_RESULT

# Memory events (v0.1.1)
AgentEventType.MEMORY_ADD_START
AgentEventType.MEMORY_ADD_COMPLETE
AgentEventType.MEMORY_SAVE_START
AgentEventType.MEMORY_SAVE_COMPLETE
AgentEventType.MEMORY_MESSAGES_LOADED

# Context events (v0.1.1)
AgentEventType.CONTEXT_ASSEMBLY_START
AgentEventType.CONTEXT_COMPONENT_INCLUDED
AgentEventType.CONTEXT_COMPONENT_TRUNCATED
AgentEventType.CONTEXT_COMPONENT_EXCLUDED
AgentEventType.CONTEXT_ASSEMBLY_COMPLETE

# Compression events (v0.1.1)
AgentEventType.COMPRESSION_START
AgentEventType.COMPRESSION_PROGRESS
AgentEventType.COMPRESSION_FALLBACK
AgentEventType.COMPRESSION_COMPLETE

# Crew events
AgentEventType.CREW_KICKOFF_START
AgentEventType.CREW_TASK_START
AgentEventType.CREW_TASK_COMPLETE
```

---

### Built-in Tools

```python
from loom.builtin.tools import (
    ReadFileTool,        # Read files
    WriteFileTool,       # Write files
    EditFileTool,        # Edit files (line-based)
    GlobTool,           # Find files by pattern
    GrepTool,           # Search in files
    BashTool,           # Execute shell commands
    WebSearchTool,      # Web search (requires API key)
)
```

---

### Agent Parameters

```python
agent(
    provider="openai",              # LLM provider
    model="gpt-4",                  # Model name
    system_instructions="...",      # System prompt
    tools=[...],                    # Tool instances

    # Persistence
    enable_persistence=False,       # Event sourcing
    journal_path=None,              # Log directory
    thread_id=None,                 # Session ID

    # Hooks & Debugging
    hooks=[],                       # Lifecycle hooks
    context_debugger=None,          # Context debugger

    # Limits
    max_iterations=50,              # Max recursion depth
    max_context_tokens=8000,        # Context limit
)
```

---

## 🎨 Common Patterns

### Pattern 1: Real-time Streaming UI

```python
async def streaming_ui(user_input: str):
    my_agent = agent(provider="openai", model="gpt-4")

    async for event in my_agent.execute(user_input):
        if event.type == AgentEventType.LLM_DELTA:
            print(event.content, end="", flush=True)
        elif event.type == AgentEventType.TOOL_EXECUTION_START:
            print(f"\n🔧 {event.metadata['tool_name']}")
        elif event.type == AgentEventType.ITERATION_START:
            print(f"\n🔄 Iteration {event.metadata['iteration']}")
        elif event.type == AgentEventType.AGENT_FINISH:
            print("\n✨ Done!")
```

---

### Pattern 2: Context Budget Monitoring

```python
async def monitor_context():
    assembler = ContextAssembler(max_tokens=4000)
    
    # Add components...
    
    included, truncated, excluded = [], [], []

    async for event in assembler.assemble_stream():
        if event.type == AgentEventType.CONTEXT_COMPONENT_INCLUDED:
            included.append(event.metadata['component_name'])
        elif event.type == AgentEventType.CONTEXT_COMPONENT_TRUNCATED:
            truncated.append(event.metadata['component_name'])
        elif event.type == AgentEventType.CONTEXT_COMPONENT_EXCLUDED:
            excluded.append(event.metadata['component_name'])
        elif event.type == AgentEventType.CONTEXT_ASSEMBLY_COMPLETE:
            print(f"✅ Included: {included}")
            print(f"✂️  Truncated: {truncated}")
            print(f"❌ Excluded: {excluded}")
            print(f"📈 Utilization: {event.metadata['utilization']:.1%}")
```

---

### Pattern 3: Resilient Compression

```python
async def compress_with_monitoring(messages):
    compressor = CompressionManager(llm=llm, max_retries=3)
    
    retry_count = 0
    fallback_used = False

    async for event in compressor.compress_stream(messages):
        if event.type == AgentEventType.COMPRESSION_PROGRESS:
            if event.metadata['status'] == 'retry':
                retry_count += 1
                print(f"⚠️  Retry {retry_count}")

        elif event.type == AgentEventType.COMPRESSION_FALLBACK:
            fallback_used = True
            print(f"🔄 Fallback: {event.metadata['fallback_method']}")

        elif event.type == AgentEventType.COMPRESSION_COMPLETE:
            print(f"✅ Compressed ({retry_count} retries, fallback: {fallback_used})")
            return event.metadata['compressed_messages']
```

---

## 💡 Tips for Coding Agents

1. **Use Streaming**: For tasks >30s, always use `execute()` instead of `run()`
2. **Enable Persistence**: Production code must have `enable_persistence=True`
3. **Add HITL**: Protect destructive tools with `HITLHook`
4. **Monitor Context**: Use `ContextDebugger` for complex tasks
5. **Test Recovery**: Always test crash recovery flow if using persistence
6. **Unique Thread IDs**: Use `f"user-{user_id}-{session_id}"` pattern
7. **Minimal Tools**: Only include necessary tools for the task
8. **Clear Instructions**: Write specific, actionable system instructions
9. **Check Events**: Use v0.1.1 event streaming for debugging
10. **Profile Performance**: Track token usage and tool calls

---

## 🎯 Quick Checklist

When building with loom-agent v0.1.1:

- [ ] Need real-time progress? → Use `execute()` not `run()`
- [ ] Production code? → `enable_persistence=True`
- [ ] Dangerous tools? → Add `HITLHook`
- [ ] Complex workflow? → Use `Crew` with `kickoff_stream()`
- [ ] Large context? → Enable `ContextDebugger`
- [ ] Memory operations? → Use `*_stream()` methods
- [ ] Context assembly? → Monitor with `assemble_stream()`
- [ ] Compression? → Track with `compress_stream()`
- [ ] Tested recovery? → Verify crash recovery flow
- [ ] Unique thread_id? → Use proper pattern

---

## 🐛 Debugging with v0.1.1

### Stream All Operations

```python
# Memory streaming
async for event in memory.add_message_stream(msg):
    print(f"[MEMORY] {event.type}: {event.metadata}")

# Context streaming  
async for event in assembler.assemble_stream():
    print(f"[CONTEXT] {event.type}: {event.metadata}")

# Compression streaming
async for event in compressor.compress_stream(msgs):
    print(f"[COMPRESS] {event.type}: {event.metadata}")

# Agent streaming
async for event in agent.execute(task):
    print(f"[AGENT] {event.type}")
```

### Use Context Debugger

```python
debugger = ContextDebugger(enable_auto_export=True)
agent(llm=llm, context_debugger=debugger)

# After execution
print(debugger.generate_summary())
print(debugger.explain_iteration(n))
```

### Check Event Journal

```python
from loom.core import EventJournal

journal = EventJournal(Path("./logs"))
events = await journal.replay(thread_id="thread-123")

for event in events:
    print(f"{event.type}: {event.metadata}")
```

---

## 📚 Further Reading

- **User Guide**: `docs/user/user-guide.md`
- **API Reference**: `docs/user/api-reference.md`
- **Migration Guide**: `docs/MIGRATION_GUIDE_V0_1.md`
- **Examples**: `examples/` directory
- **Tests**: `tests/` for real usage patterns

---

**Version**: v0.1.1  
**Last Updated**: 2024-12-12  
**Framework**: loom-agent  
**License**: MIT
