# Loom Architecture

Version: 0.7.1 | Updated: 2026-04-06

## Overview

Loom is a runtime-oriented agent framework. The core abstraction is:

```
A = ⟨C, M, L*, H_b, S, Ψ⟩
```

| Symbol | Meaning | Module |
|--------|---------|--------|
| C | Context (five partitions) | `loom/context/` |
| M | Memory (session/working/semantic/persistent) | `loom/memory/` |
| L* | Execution loop (Reason → Act → Observe → Δ)* | `loom/runtime/loop.py` |
| H_b | Heartbeat (independent perception layer) | `loom/runtime/heartbeat.py` |
| S | Safety (permissions + hooks + veto) | `loom/safety/` |
| Ψ | Evolution (self-improvement strategies) | `loom/evolution/` |

---

## Layer Map

```
┌─────────────────────────────────────────────┐
│                 loom/api/                   │  ← Public entry point
│  AgentRuntime → Session → Task → Run        │
│  SessionHandle / TaskHandle / RunHandle     │
└────────────────────┬────────────────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
┌───────▼────────┐    ┌───────────▼──────────┐
│  loom/runtime/ │    │  loom/orchestration/ │
│  L* loop       │    │  Planner             │
│  Heartbeat H_b │    │  Coordinator         │
│  Monitors      │    │  SubAgentManager     │
└───────┬────────┘    └───────────┬──────────┘
        │                         │
┌───────▼─────────────────────────▼──────────┐
│              loom/tools/                   │
│  ToolRegistry → ToolExecutor → Governance  │
│  builtin/: file, shell, web, mcp, agent... │
└───────┬────────────────────────────────────┘
        │
┌───────▼──────────────────────────────────────────────────┐
│  loom/context/   loom/memory/   loom/safety/              │
│  ContextManager  SessionMemory  PermissionManager         │
│  Compressor      WorkingMemory  HookManager               │
│  Renewal         SemanticMemory VetoAuthority             │
│  Dashboard       Persistent                               │
└──────────────────────────────────────────────────────────┘
        │
┌───────▼──────────────────────────────────────────────────┐
│  loom/providers/   loom/ecosystem/   loom/evolution/      │
│  LLMProvider       MCPBridge         EvolutionEngine      │
│  Anthropic         PluginLoader      Strategies           │
│  OpenAI            SkillRegistry                          │
│  Gemini                                                   │
└──────────────────────────────────────────────────────────┘
```

---

## Module Reference

### loom/api/ — Public Runtime API

Entry point for all integrations.

**`AgentRuntime`** (`runtime.py`)
- `__init__(profile, provider, event_bus, artifact_store)`
- `create_session(session_id, metadata) → SessionHandle`
- `get_session(session_id) → SessionHandle`
- `list_sessions() → list[Session]`

**`SessionHandle`** (`handles.py`)
- `create_task(goal, context) → TaskHandle`
- `get_task(task_id) → TaskHandle`
- `list_tasks() → list[Task]`
- `close()`

**`TaskHandle`** (`handles.py`)
- `start() → RunHandle`
- `get_run(run_id) → RunHandle`
- `list_runs() → list[Run]`

**`RunHandle`** (`handles.py`)
- `wait() → RunResult` — drives full run lifecycle
- `events() → AsyncIterator[Event]` — stream run events
- `approve(approval_id, decision)` — human-in-loop approval
- `pause()` / `resume()` / `cancel()`
- `artifacts() → list[Artifact]`
- `transcript() → dict`

**Config** (`config.py`)
```python
AgentConfig(system_prompt, model, max_tokens, temperature, max_steps, tool_timeout)
LLMConfig(model, max_tokens, temperature, timeout)
ToolConfig(allowed_tools, blocked_tools, require_approval, timeout)
PolicyConfig(mode, max_tool_calls, require_human_approval)
```

**Models** (`models.py`)
- `RunState`: PENDING / RUNNING / PAUSED / COMPLETED / FAILED / CANCELLED
- `Session`, `Task`, `Run`, `Event`, `Approval`, `Artifact`
- `RunResult(run_id, state, output, events, artifacts, error)`
- `EvidencePack(question, sources, chunks, citations, relevance_score)`

**`AgentProfile`** (`profile.py`)
- `from_preset(preset) → AgentProfile`
- `from_yaml(path) → AgentProfile`

---

### loom/runtime/ — Execution Engine

**`AgentLoop`** (`loop.py`)
- Implements L* = (Reason → Act → Observe → Δ)*
- `run(goal, context, reason_fn, act_fn, observe_fn, delta_fn)`
- Configurable via `LoopConfig(max_steps, timeout, renewal_threshold)`

**`Heartbeat`** (`heartbeat.py`)
- H_b: independent sensing thread running parallel to L*
- `start(event_callback)` / `stop()`
- Sources: `FilesystemMonitor`, `ProcessMonitor`, `ResourceMonitor`, `MFEventsMonitor`
- Classifies urgency: `low` / `medium` / `high` / `critical`

**Monitors** (`monitors.py`)
- `FilesystemMonitor(paths, delta_h)` — file hash change detection
- `ProcessMonitor(pid_file, delta_h)` — process exit detection
- `ResourceMonitor(thresholds, delta_h_memory, delta_h_disk)` — CPU/memory/disk
- `MFEventsMonitor(topics, event_bus)` — event bus topic subscription

---

### loom/context/ — Context Management

**`ContextManager`** (`manager.py`)
- Manages five partitions: system / history / working / knowledge / tool_results
- `rho` property: current context pressure (0.0–1.0)
- `should_renew()` / `renew()` — triggers ContextRenewer
- `should_compress()` / `compress(strategy)` — triggers ContextCompressor

**`ContextCompressor`** (`compression.py`)
Four-level compression triggered by ρ:

| Level | Trigger | Method |
|-------|---------|--------|
| Snip | ρ > 0.7 | `snip_compact(messages, max_length)` |
| Micro | ρ > 0.8 | `micro_compact(messages)` — dedup tool results |
| Collapse | ρ > 0.9 | `context_collapse(messages, goal)` — extractive summary |
| Auto | ρ > 0.95 | `auto_compact(messages, goal)` — score-based keep |

**`ContextRenewer`** (`renewal.py`)
- `renew(partitions, goal)` — snapshot + compress + restore dashboard

**`DashboardManager`** (`dashboard.py`)
- Never-compressed working state
- Tracks: ρ, token budget, progress, plan, events, risks, questions, evidence
- `ingest_heartbeat_event(event, urgency)` — H_b → Dashboard bridge
- `decision_state()` — current state for reasoning

---

### loom/memory/ — Memory Layers

| Class | File | Purpose |
|-------|------|---------|
| `SessionMemory` | `session.py` | Short-term sliding window of messages |
| `WorkingMemory` | `working.py` | Current task dashboard + scratch pad |
| `SemanticMemory` | `semantic.py` | Vector search with cosine similarity + lexical fallback, max_size eviction, optional JSON persistence |
| `PersistentMemory` | `persistent.py` | File-based cross-session key-value store (M_f) |

**`SemanticMemory`**
- `add(entry: MemoryEntry)` — evicts oldest if over `max_size`
- `search(query, top_k, query_embedding) → list[MemoryEntry]`
- Constructor: `SemanticMemory(max_size=10_000, persist_path=None)`

---

### loom/tools/ — Tool System

**`ToolRegistry`** (`registry.py`)
- `register(tool)` / `get(name)` / `list_tools()` / `unregister(name)`

**`ToolExecutor`** (`executor.py`)
- Pipeline: permission check → rate limit → execute → observe
- `execute(tool_call) → ToolResult`

**`ToolGovernance`** (`governance.py`)
- `check_permission(tool_name, tool_definition, arguments) → PermissionDecision`
- `check_rate_limit(tool_name) → bool`
- `set_context(context)` — runtime context for policy evaluation

**Builtin Tools** (`builtin/`)

| Module | Tools |
|--------|-------|
| `file_operations.py` | read_file, write_file, list_directory, delete_file |
| `shell_operations.py` | run_command, run_script |
| `web_operations.py` | web_fetch, web_search |
| `agent_operations.py` | spawn_agent, ask_user |
| `mcp_operations.py` | mcp_connect, mcp_execute |
| `notebook_operations.py` | notebook_read, notebook_run |
| `skill_operations.py` | skill_invoke, skill_discover (placeholder) |
| `lsp_operations.py` | lsp_get_diagnostics, lsp_execute_code (placeholder) |

---

### loom/safety/ — Safety Layer (S)

Three-tier enforcement:

**`PermissionManager`** (`permissions.py`)
- Modes: `DEFAULT` / `PLAN` / `AUTO`
- `grant(tool, action, requires_approval, risk_levels)`
- `evaluate(tool, action, context, hook_decision) → PermissionDecision`

**`HookManager`** (`hooks.py`)
- `register(event, callback)`
- `evaluate(event, context, agent_context) → HookOutcome`
- `AgentContext(agent_id, goal, step_count, tool_name, tool_arguments, execution_trace)`

**`VetoAuthority`** (`veto.py`)
- Ψ's safety valve — can block any tool call
- `add_rule(VetoRule(name, predicate, reason))`
- `check_tool(tool_name, arguments) → (vetoed: bool, reason: str)`
- `audit_summary() → dict`

---

### loom/providers/ — LLM Providers

**`LLMProvider`** (abstract, `base.py`)
- Built-in retry + circuit breaker
- `complete(messages, params) → str` — with retry
- `stream(messages, params) → AsyncIterator[str]`
- `_complete(messages, params) → str` — implement in subclass

**Concrete providers:**
- `AnthropicProvider(api_key, base_url)` — Anthropic Messages API
- `OpenAIProvider(api_key, base_url, organization)` — OpenAI Chat Completions
- `GeminiProvider(api_key)` — Google Generative AI

**`CompletionParams`**
```python
CompletionParams(model="claude-3-5-sonnet-20241022", max_tokens=4096, temperature=1.0)
```

**`RetryConfig`**
```python
RetryConfig(max_retries=3, base_delay=1.0, circuit_open_after=5, circuit_reset_after=60.0)
```

---

### loom/orchestration/ — Multi-Agent

**`TaskPlanner`** (`planner.py`)
- `plan(goal, provider, max_tasks) → list[Task]` — LLM decomposition or heuristic
- `get_ready_tasks()` — dependency-ordered ready queue
- `update_status(task_id, status)`

**`Coordinator`** (`coordinator.py`)
- `register_agent(agent_id, manager)`
- `execute_plan(agent_id, planner, task_timeout=120.0) → dict[str, SubAgentResult]`
- `aggregate_results(results) → dict` — structured: total/succeeded/failed/outputs/errors

**`SubAgentManager`** (`subagent.py`)
- `spawn(goal, depth, inherit_context) → SubAgentResult`
- `spawn_many(goals, depth) → list[SubAgentResult]`
- Max depth guard: returns `MAX_DEPTH_EXCEEDED` at limit

---

### loom/ecosystem/ — Plugins & MCP

**`MCPBridge`** (`mcp.py`)
- `register_server(name, config, scope)` — scope: user / plugin / dynamic
- `connect(server_name) → bool` — stdio subprocess or mock fallback
- `execute_tool(server_name, tool_name, **kwargs)` — with timeout + reconnect
- `get_default_mcp_bridge()` — thread-safe singleton

**`PluginLoader`** (`plugin.py`)
- `load_plugin(plugin_dir, source) → Plugin`
- `enable_plugin(name)` / `disable_plugin(name)`
- `apply_to_agent(plugin_name, agent)` — wires MCP servers + hooks to agent

---

### loom/evolution/ — Self-Evolution (Ψ)

**`EvolutionEngine`** (`engine.py`)
- `register_strategy(strategy)`
- `evolve(agent)` — applies all registered strategies

**Strategies** (`strategies.py`)
- `ToolLearningStrategy` — ranks tools by success rate, suggests promotions/demotions
- `PolicyOptimizationStrategy` — analyzes policy diffs, suggests threshold adjustments

---

### loom/knowledge/ (via loom/tools/knowledge.py)

**`KnowledgePipeline`**
- `register_source(source_id, source)`
- `retrieve(question, goal, top_k=5) → EvidencePack`
- Configurable: `rerank_retrieval_weight=0.7`, `rerank_goal_weight=0.3`
- Embedding cache with LRU eviction (`embedding_cache_max=1000`)

---

## Data Flow

```
User
 │
 ▼
AgentRuntime.create_session()
 │
 ▼
SessionHandle.create_task(goal)
 │
 ▼
TaskHandle.start() → RunHandle
 │
 ├── RunHandle.wait()
 │    ├── provider.complete(messages, params)
 │    ├── publishes Events to EventBus
 │    └── stores Artifacts in ArtifactStore
 │
 ├── RunHandle.events() → stream
 └── RunHandle.artifacts() → list
```

## Typical Usage

```python
from loom.api import AgentRuntime, AgentConfig, AgentProfile
from loom.providers import AnthropicProvider

provider = AnthropicProvider(api_key="...")
profile = AgentProfile.from_preset("default")
runtime = AgentRuntime(profile=profile, provider=provider)

session = runtime.create_session()
task = session.create_task("Summarize this document")
run = task.start()
result = await run.wait()
print(result.output)
```
