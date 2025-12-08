# Quick Start Guide - loom-agent v0.0.8

Welcome to loom-agent v0.0.8! This guide will help you get started with the new **Recursive State Machine (RSM)** features in 10 minutes.

## What's New in v0.0.8?

v0.0.8 introduces production-ready features that make loom-agent suitable for real-world applications:

- 🎬 **Event Sourcing** - Complete execution history for crash recovery
- 🪝 **Lifecycle Hooks** - Intercept and control execution flow
- 🛡️ **HITL (Human-in-the-Loop)** - Confirm dangerous operations
- 🔄 **Crash Recovery** - Resume from interruptions
- 🐛 **Context Debugger** - Understand "why LLM forgot X"

## Table of Contents

1. [Basic Setup](#1-basic-setup)
2. [Enable Event Sourcing](#2-enable-event-sourcing)
3. [Add Lifecycle Hooks](#3-add-lifecycle-hooks)
4. [Implement HITL](#4-implement-hitl-human-in-the-loop)
5. [Crash Recovery](#5-crash-recovery)
6. [Context Debugging](#6-context-debugging)
7. [Production Setup](#7-production-setup)

---

## 1. Basic Setup

If you're starting fresh, install loom-agent:

```bash
pip install loom-agent[openai]  # or loom-agent[all] for all providers
```

Basic usage (no new features):

```python
import asyncio
from loom import agent

async def main():
    # Create agent (auto-loads API key from OPENAI_API_KEY)
    my_agent = agent(
        provider="openai",
        model="gpt-4",
        tools=[]
    )

    # Run
    result = await my_agent.run("Hello, introduce yourself")
    print(result)

asyncio.run(main())
```

---

## 2. Enable Event Sourcing

Event sourcing records all execution events to disk, enabling crash recovery and debugging.

```python
from loom import agent
from pathlib import Path

# Enable persistence with one parameter
my_agent = agent(
    provider="openai",
    model="gpt-4",
    tools=my_tools,
    enable_persistence=True,  # 🆕 Auto-creates event journal
    journal_path=Path("./logs"),  # 🆕 Where to store events
    thread_id="user-session-1"  # 🆕 Unique ID for this execution
)

# Run normally - events automatically recorded
result = await my_agent.run("Complex multi-step task")
```

**What happens**:
- All events saved to `./logs/thread_user-session-1.jsonl`
- Each line is one event (JSON Lines format)
- Automatic async batched writes (no performance impact)

**Check the logs**:

```bash
cat ./logs/thread_user-session-1.jsonl | jq '.'
```

---

## 3. Add Lifecycle Hooks

Hooks let you intercept execution at 9 different points without modifying core code.

### Example: Logging Hook

```python
from loom import agent
from loom.core.lifecycle_hooks import LoggingHook, MetricsHook

my_agent = agent(
    provider="openai",
    model="gpt-4",
    tools=my_tools,
    hooks=[
        LoggingHook(verbose=True),  # 🆕 Logs all lifecycle events
        MetricsHook(),  # 🆕 Collects metrics
    ]
)

result = await my_agent.run("Search for Python docs")

# Get collected metrics
from loom.core.lifecycle_hooks import MetricsHook
metrics_hook = [h for h in my_agent.hooks if isinstance(h, MetricsHook)][0]
print(metrics_hook.get_metrics())
# Output: {'llm_calls': 2, 'tool_calls': 1, 'iterations': 2, ...}
```

### Example: Custom Hook

Create your own hook to track anything:

```python
class CustomAnalyticsHook:
    def __init__(self):
        self.tool_usage = {}

    async def after_tool_execution(self, frame, tool_result):
        """Called after each tool execution"""
        tool_name = tool_result["tool_name"]
        self.tool_usage[tool_name] = self.tool_usage.get(tool_name, 0) + 1
        return None  # Don't modify the result

    async def before_llm_call(self, frame, messages):
        """Called before each LLM call"""
        print(f"🤖 Calling LLM with {len(messages)} messages")
        return None  # Don't modify messages

# Use it
analytics = CustomAnalyticsHook()

my_agent = agent(
    provider="openai",
    model="gpt-4",
    tools=my_tools,
    hooks=[analytics]
)

await my_agent.run("Complex task")
print(f"Tool usage: {analytics.tool_usage}")
```

**Available Hook Points**:
- `before_iteration_start(frame)` - Start of each iteration
- `before_context_assembly(frame)` - Before building context
- `after_context_assembly(frame, snapshot, metadata)` - After context built
- `before_llm_call(frame, messages)` - Before LLM call
- `after_llm_response(frame, content, tool_calls)` - After LLM responds
- `before_tool_execution(frame, tool_call)` - **Before each tool** (HITL key!)
- `after_tool_execution(frame, tool_result)` - After each tool
- `before_recursion(frame, next_frame)` - Before recursive call
- `after_iteration_end(frame)` - End of iteration

---

## 4. Implement HITL (Human-in-the-Loop)

HITL lets you confirm dangerous operations before they execute.

### Built-in HITL Hook

```python
from loom import agent
from loom.core.lifecycle_hooks import HITLHook

# Define dangerous tools
hitl_hook = HITLHook(
    dangerous_tools=["delete_file", "send_email", "execute_shell"],
    ask_user_callback=lambda msg: input(f"{msg} (y/n): ").lower() == "y"
)

my_agent = agent(
    provider="openai",
    model="gpt-4",
    tools=[delete_file_tool, send_email_tool, safe_tools],
    hooks=[hitl_hook],
    enable_persistence=True,  # Required for checkpoint saving
    journal_path=Path("./logs")
)

# When agent tries to call delete_file:
# Output: "Allow delete_file with args {'path': '/old/logs'}? (y/n): "
# - If user types 'y': Tool executes
# - If user types 'n': Execution paused, checkpoint saved
```

### Custom HITL Logic

```python
class SmartHITLHook:
    async def before_tool_execution(self, frame, tool_call):
        """Custom HITL logic with smart rules"""
        from loom.core.lifecycle_hooks import InterruptException

        tool_name = tool_call["name"]
        args = tool_call["arguments"]

        # Rule 1: Always confirm deletes
        if "delete" in tool_name.lower():
            confirmed = input(f"Confirm delete: {args}? (y/n): ") == "y"
            if not confirmed:
                raise InterruptException("User rejected delete operation")

        # Rule 2: Email requires subject approval
        if tool_name == "send_email":
            subject = args.get("subject", "")
            if "urgent" in subject.lower():
                confirmed = input(f"Send urgent email: {subject}? (y/n): ") == "y"
                if not confirmed:
                    raise InterruptException("User rejected urgent email")

        return None  # Allow execution

my_agent = agent(
    provider="openai",
    model="gpt-4",
    tools=tools,
    hooks=[SmartHITLHook()],
    enable_persistence=True
)
```

---

## 5. Crash Recovery

Resume execution after crashes, server restarts, or HITL interruptions.

### Scenario: Server Crashes Mid-Execution

```python
from loom.core import AgentExecutor, EventJournal
from pathlib import Path

# Initial execution (crashes after 5 seconds)
journal = EventJournal(storage_path=Path("./logs"))
await journal.start()

executor = AgentExecutor(
    llm=llm,
    tools=tools,
    event_journal=journal,
    thread_id="long-task-123"
)

try:
    # Start long-running task
    async for event in executor.tt(messages, turn_state, context):
        # ... processing events ...
        # 💥 CRASH HAPPENS HERE
        pass
finally:
    await journal.stop()
```

**After restart, resume execution**:

```python
# Server restarted - resume from checkpoint
journal = EventJournal(storage_path=Path("./logs"))

executor = AgentExecutor(
    llm=llm,
    tools=tools,
    event_journal=journal
)

# Resume from crash point
async for event in executor.resume(thread_id="long-task-123"):
    if event.type == AgentEventType.AGENT_FINISH:
        print(f"✅ Task completed after recovery: {event.content}")
    elif event.type == AgentEventType.PHASE_START and event.phase == "resume":
        print("📼 Replaying events from journal...")
    elif event.type == AgentEventType.PHASE_END and event.phase == "resume":
        print(f"✅ State reconstructed from {event.metadata['total_events']} events")
```

### High-Level API for Resume

```python
from loom import agent
from pathlib import Path

# Create agent with persistence
my_agent = agent(
    provider="openai",
    model="gpt-4",
    tools=tools,
    enable_persistence=True,
    journal_path=Path("./logs"),
    thread_id="task-456"
)

# Normal execution
try:
    result = await my_agent.run("Long task")
except Exception:
    print("💥 Crashed!")

# Later, resume
recovered_agent = agent(
    provider="openai",
    model="gpt-4",
    tools=tools,
    enable_persistence=True,
    journal_path=Path("./logs"),  # Same path
    thread_id="task-456"  # Same thread_id
)

# Resume execution
async for event in recovered_agent.executor.resume(thread_id="task-456"):
    if event.type == AgentEventType.AGENT_FINISH:
        print(f"✅ Recovered: {event.content}")
```

---

## 6. Context Debugging

Understand why the LLM "forgot" something or made a specific decision.

### Enable Context Debugger

```python
from loom import agent
from loom.core import ContextDebugger

# Create debugger
debugger = ContextDebugger(enable_auto_export=True)

my_agent = agent(
    provider="openai",
    model="gpt-4",
    tools=tools,
    context_debugger=debugger  # 🆕 Enable debugging
)

# Run complex task
await my_agent.run("Multi-step research task")

# Analyze what happened
print(debugger.generate_summary())
```

**Output**:
```
Context Management Summary
=========================
Total iterations: 5
Total assemblies: 5
Average token utilization: 87.3%

Iteration Breakdown:
  - Iteration 1: 8,234 tokens (51.5% utilization)
  - Iteration 2: 12,456 tokens (77.9% utilization)
  - Iteration 3: 15,123 tokens (94.5% utilization) ⚠️ Near limit
  ...
```

### Debug Specific Iteration

```python
# Why did iteration 3 forget file contents?
explanation = debugger.explain_iteration(3)
print(explanation)
```

**Output**:
```
Iteration 3 Context Assembly
=============================
Token Budget: 16,000
Tokens Used: 15,123 (94.5% utilization)

✅ Included Components:
  - base_instructions (1,200 tokens, priority=CRITICAL)
  - tool_definitions (800 tokens, priority=MEDIUM)
  - rag_docs (5,000 tokens, priority=HIGH)

❌ Excluded Components:
  - file_content.py (2,500 tokens, priority=MEDIUM)
    Reason: Token limit exceeded. RAG docs (priority=HIGH) took priority.

💡 Suggestion: Increase max_context_tokens or reduce RAG doc count
```

### Track Specific Component

```python
# Where did "file_content.py" go?
component_history = debugger.explain_component("file_content.py")
print(component_history)
```

**Output**:
```
Component History: file_content.py
===================================
Iteration 1: ✅ Included (2,500 tokens)
Iteration 2: ✅ Included (2,500 tokens)
Iteration 3: ❌ Excluded (token limit exceeded)
Iteration 4: ❌ Excluded (token limit exceeded)
Iteration 5: ✅ Included (2,500 tokens)
```

---

## 7. Production Setup

Combine all features for production-ready agent:

```python
import asyncio
from pathlib import Path
from loom import agent
from loom.core import ContextDebugger
from loom.core.lifecycle_hooks import LoggingHook, MetricsHook, HITLHook

class ProductionAgent:
    def __init__(self, thread_id: str):
        self.thread_id = thread_id
        self.debugger = ContextDebugger(enable_auto_export=True)

        # HITL for dangerous operations
        self.hitl_hook = HITLHook(
            dangerous_tools=["delete_file", "execute_shell", "send_email"],
            ask_user_callback=self.confirm_operation
        )

        # Logging and metrics
        self.logging_hook = LoggingHook(verbose=False)
        self.metrics_hook = MetricsHook()

        # Create agent with all features
        self.agent = agent(
            provider="openai",
            model="gpt-4",
            tools=self.get_tools(),
            system_instructions=self.get_system_prompt(),
            # 🆕 v0.0.8 Features
            enable_persistence=True,
            journal_path=Path("./production_logs"),
            hooks=[self.hitl_hook, self.logging_hook, self.metrics_hook],
            context_debugger=self.debugger,
            thread_id=thread_id,
            # Production settings
            max_iterations=100,
            max_context_tokens=32000,
        )

    def confirm_operation(self, message: str) -> bool:
        """Custom HITL confirmation with logging"""
        print(f"⚠️  HITL: {message}")
        # In production, send to UI/webhook for user confirmation
        return input("Confirm (y/n): ").lower() == "y"

    async def run_with_recovery(self, task: str):
        """Run task with automatic recovery on failure"""
        try:
            result = await self.agent.run(task)
            print(f"✅ Task completed: {result}")

            # Log metrics
            metrics = self.metrics_hook.get_metrics()
            print(f"📊 Metrics: {metrics}")

            return result

        except Exception as e:
            print(f"💥 Error: {e}")
            print("🔄 Attempting recovery...")

            # Resume from checkpoint
            async for event in self.agent.executor.resume(thread_id=self.thread_id):
                if event.type == AgentEventType.AGENT_FINISH:
                    print(f"✅ Recovered: {event.content}")
                    return event.content

    def get_tools(self):
        # Your production tools
        return []

    def get_system_prompt(self):
        return "You are a production AI assistant..."

# Usage
async def main():
    prod_agent = ProductionAgent(thread_id="prod-session-1")
    result = await prod_agent.run_with_recovery("Complex production task")

asyncio.run(main())
```

---

## Next Steps

### Learn More

- **Architecture Details**: [docs/ARCHITECTURE_REFACTOR.md](ARCHITECTURE_REFACTOR.md)
- **Complete Examples**: [examples/integration_example.py](../examples/integration_example.py)
- **API Reference**: [docs/user/api-reference.md](user/api-reference.md)
- **Integration Guide**: [docs/INTEGRATION_COMPLETE.md](INTEGRATION_COMPLETE.md)

### Common Patterns

1. **Development**: No persistence, basic hooks
   ```python
   agent(provider="openai", model="gpt-4", tools=tools)
   ```

2. **Testing**: Persistence + metrics
   ```python
   agent(
       provider="openai", model="gpt-4", tools=tools,
       enable_persistence=True,
       hooks=[MetricsHook()]
   )
   ```

3. **Production**: All features enabled
   ```python
   agent(
       provider="openai", model="gpt-4", tools=tools,
       enable_persistence=True,
       journal_path=Path("/var/log/loom"),
       hooks=[HITLHook(...), LoggingHook(), MetricsHook()],
       context_debugger=ContextDebugger(enable_auto_export=True),
       thread_id=session_id
   )
   ```

### Troubleshooting

**Q: Events not being saved?**
- Ensure `enable_persistence=True` or provide `event_journal`
- Check `journal_path` directory exists and is writable
- Call `await journal.stop()` to flush remaining events

**Q: Hooks not being called?**
- Verify hooks are passed to `agent()` function
- Check hook method signatures match protocol
- Hooks must return `None` or modified value (see docs)

**Q: Resume not working?**
- Ensure same `thread_id` used for original and resumed execution
- Check event journal file exists at expected path
- Verify all tools available in resumed execution

**Q: Context debugger showing nothing?**
- Ensure `context_debugger` passed to `agent()`
- Run at least one complete iteration
- Check `enable_auto_export=True` for file output

---

## Feedback

Found an issue or have a suggestion? Please open an issue:
- **GitHub Issues**: https://github.com/kongusen/loom-agent/issues

---

**Happy Building with loom-agent v0.0.8!** 🎉
