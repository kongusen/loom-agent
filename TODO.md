# Loom Current Inventory And TODO

This file reflects the repository state as of 2026-04-06.

It is no longer a backlog copied from older wiki claims.
It is a code-first inventory of what is:

- implemented and usable
- implemented as a minimal version
- still placeholder-level
- currently broken or unfinished because the repository is mid-migration

The highest priority now is not adding more surface area.
It is finishing the migration so the package, docs, and tests agree on one runtime architecture.

## Current Reality

### Implemented And Usable

These modules have real code paths and are no longer simple stubs:

- Runtime API object model:
  - `loom/api/runtime.py`
  - `loom/api/handles.py`
  - `loom/api/models.py`
  - `loom/api/events.py`
  - `loom/api/artifacts.py`
- Provider wrappers:
  - `loom/providers/openai.py`
  - `loom/providers/anthropic.py`
  - `loom/providers/gemini.py`
- Context control:
  - `loom/context/manager.py`
  - `loom/context/compression.py`
  - `loom/context/renewal.py`
  - `loom/context/dashboard.py`
- Runtime monitors and heartbeat:
  - `loom/runtime/heartbeat.py`
  - `loom/runtime/monitors.py`
  - `loom/runtime/loop.py`
- Tool governance and execution:
  - `loom/tools/governance.py`
  - `loom/tools/executor.py`
  - `loom/tools/pipeline.py`
- Knowledge and memory building blocks:
  - `loom/tools/knowledge.py`
  - `loom/memory/semantic.py`
  - `loom/api/profile.py`
- Ecosystem and MCP baseline:
  - `loom/ecosystem/mcp.py`
  - `loom/ecosystem/plugin.py`
  - `loom/ecosystem/integration.py`
- Safety baseline:
  - `loom/safety/permissions.py`
  - `loom/safety/hooks.py`
  - `loom/safety/veto.py`
  - `loom/safety/veto_auditor.py`

### Implemented As Minimal Versions

These areas work, but they are still thin implementations rather than mature subsystems:

#### 1. Run execution path

- Status: minimal implementation
- Files:
  - `loom/api/handles.py`
  - `loom/api/runtime.py`
- Current behavior:
  - `RunHandle.wait()` drives real state transitions, events, artifacts, and result materialization
  - if provider is available, it tries a full `Agent` path first
  - if that path fails, it silently falls back to a single-turn provider completion
- Main limitation:
  - the "full Agent path" is not currently reliable because the legacy `loom.agent` stack is not migrated

#### 2. Planner and orchestration

- Status: minimal implementation
- Files:
  - `loom/orchestration/planner.py`
  - `loom/orchestration/subagent.py`
  - `loom/orchestration/coordinator.py`
- Current behavior:
  - planner supports heuristic decomposition and optional LLM decomposition
  - coordinator can execute dependency-ordered tasks
  - sub-agent manager can spawn child runs and aggregate outputs
- Main limitation:
  - planning is still linear and lightweight
  - aggregation is still string-oriented
  - deeper collaboration semantics remain basic

#### 3. Semantic memory and knowledge retrieval

- Status: minimal implementation
- Files:
  - `loom/memory/semantic.py`
  - `loom/tools/knowledge.py`
- Current behavior:
  - lexical fallback works
  - cosine similarity path works when embeddings are provided
  - retrieval and reranking are real
- Main limitation:
  - no external vector backend
  - no persistence/index layer
  - ranking strategy is still heuristic

#### 4. MCP and plugin ecosystem

- Status: minimal implementation
- Files:
  - `loom/ecosystem/mcp.py`
  - `loom/ecosystem/plugin.py`
  - `loom/ecosystem/integration.py`
- Current behavior:
  - one MCP implementation remains
  - stdio path exists
  - mock fallback still exists
  - plugin enable/disable and component loading work
- Main limitation:
  - still closer to a local bridge than a production-grade MCP subsystem

#### 5. Safety and evolution

- Status: minimal implementation
- Files:
  - `loom/evolution/strategies.py`
  - `loom/safety/permissions.py`
  - `loom/safety/hooks.py`
  - `loom/safety/veto.py`
- Current behavior:
  - evolution can aggregate feedback into tool and policy suggestions
  - safety can evaluate permission decisions, hook outcomes, and structured veto logs
- Main limitation:
  - heuristics are lightweight
  - audit and enforcement depth is still limited

## Real Gaps Still Present

These are the remaining feature-level gaps that are actually still missing in the current code.

### 1. Placeholder built-in tools

- Status: partially implemented
- Why it matters: several tools are registered in the builtin surface but still return placeholder payloads
- Files:
  - `loom/tools/builtin/skill_operations.py` ✅ **IMPLEMENTED**
  - `loom/tools/builtin/lsp_operations.py`
- Current gaps:
  - `skill_invoke()` ✅ **IMPLEMENTED** - loads and executes skills from markdown files
  - `skill_discover()` ✅ **IMPLEMENTED** - discovers all available skills
  - `lsp_get_diagnostics()` - requires LSP server integration or MCP bridge
  - `lsp_execute_code()` - requires REPL integration or MCP bridge

### 2. Legacy/full Agent execution path is not migrated

- Status: broken behind fallback
- Why it matters: the public runtime currently advertises a deeper execution path than the repository can safely execute
- Files:
  - `loom/api/handles.py`
  - `loom/agent/core.py`
  - `loom/agent/runtime.py`
- Current gaps:
  - `loom/api/handles.py` tries to import `..config.AgentConfig`, which no longer exists
  - `loom/agent/core.py` still imports deleted modules such as `loom.config`, `loom.events`, `loom.scene`, `loom.skills`
  - the runtime works today mainly because `_execute_run()` catches that failure and falls back

### 3. Public package root is broken

- Status: broken
- Why it matters: `import loom` should be a stable entry point, but it currently fails during import
- Files:
  - `loom/__init__.py`
  - `loom/agent/__init__.py`
  - `loom/agent/core.py`
- Current gaps:
  - `loom/__init__.py` eagerly imports legacy modules that still depend on deleted packages
  - importing `loom`, `loom.runtime`, `loom.tools`, `loom.context`, or `loom.agent` fails because parent package import fails first

### 4. Duplicate runtime stacks still coexist

- Status: migration incomplete
- Why it matters: the repo currently exposes both old and new stacks, which makes maturity hard to reason about
- Files:
  - `loom/runtime/`
  - `loom/execution/`
  - `loom/safety/`
  - `loom/security/`
- Current gaps:
  - `loom/runtime` is the newer runtime-facing stack
  - `loom/execution` is still present as a separate older stack
  - `loom/safety` and `loom/security` overlap conceptually
  - package exports still blur the line between canonical and legacy modules

## Migration And Alignment Work

These are now the highest-priority tasks.

### P0. Repair package imports and exported surface

- Priority: highest
- Why it matters: until this is fixed, the repository is structurally inconsistent even if many submodules work in isolation
- Tasks:
  - make `import loom` succeed
  - stop `loom/__init__.py` from importing broken legacy modules
  - either migrate `loom.agent` to the new architecture or remove it from the public root export
  - ensure public imports match the architecture described in `README.md`

### P1. Decide the fate of the legacy stack

- Priority: highest
- Why it matters: today the repo mixes a new runtime API with an older Agent stack that still points to deleted packages
- Tasks:
  - choose whether `loom/agent/` remains a supported layer
  - if yes, migrate it to `loom/api`, `loom/context`, `loom/runtime`, `loom/tools`
  - if not, remove it from public exports and from docs
  - do the same cleanup for `loom/execution/` vs `loom/runtime/`
  - do the same cleanup for `loom/security/` vs `loom/safety/`

### P2. Reconcile tests with the migrated codebase

- Priority: high
- Why it matters: current test collection is broken, which hides real regressions
- Evidence:
  - `pytest tests/core -q` on 2026-04-06 fails during collection
- Current blockers:
  - import errors caused by the broken package root
  - `tests/core/test_cluster_extended.py` is syntactically corrupted
  - some tests still assert placeholder behavior that no longer matches the code, such as web tool expectations
- Tasks:
  - restore package imports first
  - remove or repair corrupted tests
  - update tests to match moved implementations such as `web_operations.py`

### P3. Realign docs, wiki, and TODO with the current architecture

- Priority: high
- Why it matters: several docs still describe pre-migration code paths
- Examples:
  - old wiki pages still describe `RunHandle.wait()` and providers as partial/mock
  - previous TODO references `loom/tools/builtin/web.py`, which no longer exists
- Tasks:
  - sync README, wiki, and package metadata to the current runtime-first architecture
  - remove references to deleted files and stale status claims
  - ensure status labels distinguish "implemented", "minimal", and "broken during migration"

### P4. Align package metadata and versioning

- Priority: medium
- Why it matters: release metadata currently disagrees with code and docs
- Files:
  - `pyproject.toml`
  - `loom/__version__.py`
- Current gaps:
  - `pyproject.toml` says `0.7.0`
  - `loom/__version__.py` says `0.7.1`
  - package description still says "Minimal self-organizing multi-agent framework" while README now positions Loom as a runtime-oriented framework

## What Is No Longer A TODO

These items should not be treated as outstanding feature work anymore:

- `loom/api/profile.py` `AgentProfile.from_yaml()`
- `loom/memory/semantic.py` search
- `loom/tools/knowledge.py` retrieval and rerank
- `loom/context/compression.py` `micro_compact()`
- `loom/context/renewal.py` and `loom/context/dashboard.py` renew/dashboard baseline
- `loom/evolution/strategies.py` basic evolution strategies
- `loom/safety/*` structured permission/hook/veto baseline
- `loom/tools/builtin/web_operations.py` web fetch and web search baseline

## Practical Summary

The repository is no longer best described as "missing many capabilities".

It is better described as:

1. a new runtime-centered core that already has many real minimal implementations
2. a legacy stack still exported from the package root
3. a migration that is not fully closed in imports, tests, metadata, and docs

That means the next correct work is consolidation, not uncontrolled feature expansion.
