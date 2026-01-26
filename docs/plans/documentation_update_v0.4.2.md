# Documentation Update Plan (v0.4.2)

**Status**: Draft
**Target Version**: v0.4.2
**Based On**: 
- `docs/design/fractal-architecture-redesign.md`
- `docs/design/system-optimization-plan.md`
- Existing Codebase (`loom/`)

## 1. Overview

The goal is to synchronize the documentation system with the v0.4.2 codebase, which implements significant architectural changes including the Fractal Composite Node, Hierarchical Memory (L1-L4), and Type-Safe Event Bus.

## 2. Documentation Structure Updates

We will maintain the existing 6-part structure in `README.md` but update the content and organizational details.

### 2.1 Concepts & Framework (Update)
Low-level architectural documents need to reflect the new implementation.

- **`docs/framework/fractal-architecture.md`**
  - **Current**: Likely outlines the old `NodeContainer`.
  - **Update**: Rewrite to describe the **Composite Node** pattern, Recursive Task Delegation, and the new `fractal/` directory structure.
  - **Source**: `fractal-architecture-redesign.md` + `loom/fractal/` code.

- **`docs/features/memory-system.md`**
  - **Current**: General description of memory.
  - **Update**: Detail the **L1-L4 Layer** implementation (`loom/memory/layers/`), `FractalMemory` manager, and the `MemoryScope` (Local, Shared, Global).
  - **Source**: `system-optimization-plan.md` + `loom/memory/` code.

- **`docs/framework/event-bus.md`**
  - **Current**: String-based event routing.
  - **Update**: Document the **Type-Safe Event Bus**, `TaskAction` enums, and Protocol-based handlers.
  - **Source**: `system-optimization-plan.md` + `loom/events/` code.

- **`docs/framework/context-management.md`**
  - **Update**: Include "Smart Context" and Task Feature analysis if implemented.

### 2.2 Usage & Examples (New/Update)
We need concrete code examples showing how to instantiate and use these new systems.

- **`docs/usage/getting-started.md`**
  - Update the "Hello World" agent to use the new initialization patterns.

- **`docs/usage/examples/` (New Folder)**
  - `memory_layers.md`: Example of configuring L1-L4 layers and using `LoomMemory`.
  - `fractal_agent.md`: Example of creating a parent agent with child nodes using `CompositeNode`.
  - `custom_events.md`: Example of defining custom Actions and Handlers.

### 2.4 Root Documentation (Update)
- **`README.md`** & **`README_EN.md`**
  - Update version to v0.4.2.
  - Highlight **Type-Safe Event Bus** and **Composite Node** improvements.
  - Review and verify feature claims against new implementation.

### 2.3 API Reference (Update)
- Ensure references to `NodeContainer` are updated/removed in favor of `CompositeNode` (if applicable) or updated logic.

## 3. Execution Steps

1.  **Preparation**:
    - [ ] Create `docs/usage/examples/` directory.
    - [ ] Verify `docs/plans/` exists (or create it) for this document.

2.  **Core Framework Docs**:
    - [ ] Update `docs/framework/fractal-architecture.md`.
    - [ ] Update `docs/features/memory-system.md`.
    - [ ] Update `docs/framework/event-bus.md`.

3.  **Root & Usage Guides**:
    - [ ] Update `README.md` and `README_EN.md`.
    - [ ] Create `docs/usage/examples/simple_agent.py` (code or markdown block).
    - [ ] Create `docs/usage/examples/fractal_tree.py`.
    - [ ] Update `docs/usage/getting-started.md`.

4.  **Review & Cleanup**:
    - [ ] Update `docs/README.md` links.
    - [ ] Archive obsolete designs in `docs/archive/`.

## 4. Key Content to Migrate

### From `fractal-architecture-redesign.md`
- The "Koch Snowflake" analogy (keep in concepts).
- `MemoryScope` and `AccessPolicies`.
- `CompositeNode` and `CompositionStrategy`.

### From `system-optimization-plan.md`
- L1-L4 specific implementations (CircularBuffer, PriorityQueue, etc.).
- Event Bus `TaskAction` enum usage.

## 5. Next Actions
- Approve this plan.
- Begin with **Core Framework Docs** updates.
