# Changelog

All notable changes to this project will be documented in this file.


## [0.4.3] - 2026-01-25

### ⚠️ BREAKING CHANGES

这是一个破坏性变更版本，引入了全新的分形架构设计。

### 🌟 分形架构重新设计

#### 核心概念：有限时间距离下的无限思考

**灵感来源：科赫雪花（Koch Snowflake）**
- 通过递归分解实现"有限时间距离下的无限思考"
- 空间换时间：多Agent并行实现时间压缩
- 局部O(1)，全局无限：每个Agent认知负载恒定，但总思考深度无限
- 自相似性：每层使用相同的Agent执行循环

#### 架构整合

**与现有设计深度整合**：
- **autonomous-agent-design.md**: 使用meta-tools（delegate_task）实现自主委派
- **context-manager-design.md**: 整合TaskContextManager进行智能上下文传递
- **agent-improvements-summary.md**: 保持"Agent is just a for loop"哲学
- **system-optimization-plan.md**: FractalMemory使用LoomMemory (L1-L4)作为底层存储

#### 新增组件

**分形记忆系统**：
- `MemoryScope`: 四种记忆作用域（LOCAL, SHARED, INHERITED, GLOBAL）
- `FractalMemory`: 分形记忆管理器，支持父子节点记忆共享
- `SmartAllocationStrategy`: 智能记忆分配策略
- `MemorySyncManager`: 记忆同步管理器，支持版本控制和冲突解决

**自主委派机制**：
- `delegate_task` meta-tool: LLM自主决策何时委派
- `Agent._auto_delegate`: 自动委派实现
- `Agent._create_child_node`: 创建子节点并智能分配上下文
- `Agent._sync_memory_from_child`: 双向记忆流动

### 📝 设计文档

- **新增**: `docs/design/fractal-architecture-redesign.md` - 完整的分形架构设计
- **更新**: `PLAN.md` - 详细的实施计划（Task 6-9）

### 🎯 核心价值

通过分形架构，实现：
1. **真正的分形组合** - 支持无限递归委派
2. **智能上下文管理** - 自动分配和共享上下文
3. **双向记忆流动** - 父子节点间的记忆可以双向传播
4. **O(1)复杂度保证** - 每个节点的认知负载保持恒定
5. **无限思考能力** - 在有限时间内实现无限深度的思考

### ⚠️ 迁移指南

这是一个破坏性变更，需要：
1. 更新Agent实现以支持meta-tools
2. 迁移到新的FractalMemory系统
3. 更新系统提示词以包含delegate_task描述

详细迁移指南请参考 `docs/design/fractal-architecture-redesign.md`

---

## [0.4.1] - 2026-01-21

### 🔧 Code Quality Improvements

#### 沙盒工具更新
- **修复 ruff 检查问题**：将 `asyncio.TimeoutError` 替换为 `TimeoutError`（UP041 规则）
- **修复 mypy 类型检查**：为 `_create_safe_environment` 方法中的 `safe_env` 变量添加明确的类型注解
- **代码质量提升**：通过 ruff 和 mypy 的所有检查，确保代码符合项目规范

### 📝 Notes

这是一个维护性发布，主要关注代码质量和工具链的完善。所有更改都向后兼容，不影响现有功能。

---

## [0.4.0-alpha] - 2026-01-19

### 🎯 The "Axiomatic Framework" Release

Loom v0.4.0-alpha represents a fundamental shift in the framework's theoretical foundation. This release introduces a formal axiomatic system that defines the core principles of cognitive organisms, reorganizes the entire documentation structure, and emphasizes the framework's mission to counter cognitive entropy.

### 🧩 Core Philosophy

#### 1. Axiomatic Framework
- **5 Foundational Axioms**: Established a formal mathematical foundation for the framework
  - **Axiom A1 (Uniform Interface)**: All nodes implement `NodeProtocol`
  - **Axiom A2 (Event Sovereignty)**: All communication through standardized task models
  - **Axiom A3 (Fractal Composition)**: Nodes recursively compose with O(1) complexity
  - **Axiom A4 (Memory Metabolism)**: Information transforms into knowledge through metabolism
  - **Axiom A5 (Cognitive Emergence)**: Cognition emerges from orchestration interactions
- **Theoretical Foundation**: Every design decision now derives from these axioms
- **Cognitive Organisms**: Shifted focus from "production-grade systems" to building cognitive life forms

#### 2. Countering Cognitive Entropy
- **Spatial Entropy**: Fractal architecture maintains O(1) local complexity at infinite depth
- **Temporal Entropy**: Metabolic memory transforms flowing experience into fixed knowledge
- **Ultimate Goal**: Reliable operation at infinite complexity and infinite time

### 📚 Documentation Overhaul

#### 3. New Documentation Structure
- **Removed**: Old `docs/en/` and `docs/zh/` bilingual structure
- **New Organization**:
  - `docs/concepts/` - Theoretical foundations and axiomatic framework
  - `docs/usage/` - User guides and API references
  - `docs/framework/` - Core architecture documentation
  - `docs/features/` - Feature-specific documentation
  - `docs/patterns/` - Design patterns and best practices
  - `docs/optimization/` - Performance optimization guides
  - `docs/archive/` - Legacy documentation
- **Axiomatic Framework Document**: Comprehensive theoretical foundation document
- **Updated Navigation**: Restructured documentation index for better discoverability

#### 4. Updated README Files
- **README.md** (Chinese): Updated to reflect v0.4.0-alpha features and new doc structure
- **README_EN.md** (English): Updated to reflect v0.4.0-alpha features and new doc structure
- **CONTRIBUTING.md**: Updated with new documentation structure guidelines
- **Core Features**: Reorganized to emphasize axiomatic foundation and cognitive organisms

### 🛡️ Protocol Evolution

#### 5. Google A2A Protocol Integration
- **Task-Based Communication**: All interactions now explicitly based on Google A2A protocol
- **SSE Transport**: Server-Sent Events for real-time streaming
- **Standard Task Model**: Formalized task structure with status, parameters, and results

### 🎯 API Refinements

#### 6. FastAPI-Style API Emphasis
- **Type Safety**: Pydantic-based configuration models highlighted
- **LoomApp + AgentConfig**: Simplified agent creation pattern
- **Unified Management**: Centralized event bus and dispatcher management

### 📖 Documentation Content

#### 7. Enhanced Conceptual Documentation
- **Fractal Architecture**: Detailed explanation of complexity conservation
- **Memory System**: Emphasis on metabolic processes and entropy reduction
- **Event Bus**: Clarified as the "nervous system" of cognitive organisms
- **Tool System**: Updated to reflect protocol-first approach

### 🔄 Breaking Changes

- **Documentation Paths**: All documentation links updated to new structure
  - Old: `docs/en/README.md`, `docs/zh/README.md`
  - New: `docs/README.md` with organized subdirectories
- **Conceptual Framing**: Shift from "production systems" to "cognitive organisms"
- **Theoretical Emphasis**: Framework now explicitly grounded in axiomatic system

### 📝 Notes

This is an **alpha release** focused on establishing the theoretical foundation and documentation structure. The core implementation remains stable from v0.3.8, but the conceptual framework and documentation have been fundamentally reorganized to better communicate the framework's unique approach to building AI agents.

---

## [0.3.8] - 2026-01-14

### 🎯 The "PostgreSQL Vector Store" Release

Loom v0.3.8 adds PostgreSQL (pgvector) support for L4 memory vectorization, providing enterprise-grade persistent storage options.

### ✨ New Features

#### 1. PostgreSQL Vector Store Support
- **PostgreSQL + pgvector**: Added PostgreSQL as a vector store provider for L4 memory
- **Enterprise Integration**: Seamless integration with existing PostgreSQL infrastructure
- **ACID Guarantees**: Full transactional support for vector operations
- **Configuration Examples**: Comprehensive configuration examples for PostgreSQL setup

### 📚 Documentation Enhancements

#### 2. Enhanced Memory System Documentation
- **Persistent Storage**: Detailed explanation of L4 vectorization and persistent storage mechanism
- **Semantic Retrieval**: Clear documentation of semantic search and vector comparison workflow
- **Usage Examples**: Complete code examples showing storage and retrieval patterns
- **Multi-Provider Support**: Updated documentation to reflect Qdrant, Chroma, and PostgreSQL support

#### 3. Configuration Updates
- **Vector Store Config**: Added PostgreSQL configuration examples in `loom/config/memory.py`
- **Provider Options**: Updated provider type to include 'postgres' option
- **README Updates**: Updated both Chinese and English README files with PostgreSQL support information

### 🔧 Improvements

- **Vector Dimensions**: Clarified that vector dimensions depend on the embedding model used (BGE: 512, OpenAI: 1536+)
- **Documentation Clarity**: Improved clarity around persistent storage and cross-session memory
- **Configuration Examples**: Added comprehensive examples for all vector store providers

## [0.3.7] - 2026-01-14

### 🎯 The "Simplified Cognition" Release

Loom v0.3.7 focuses on architectural simplification and enhanced context projection, removing the Router system while maintaining dual-system thinking capabilities.

### 🔴 Breaking Changes

#### 1. Router System Removed
- **Removed**: `loom/cognition/router.py` (QueryClassifier, AdaptiveRouter, SystemType, RoutingDecision)
- **Removed**: `loom/config/router.py` (RouterConfig)
- **Removed**: `LoomBuilder.with_system12_routing()` method
- **Removed**: Router-related configurations from `CognitiveSystemConfig`

**Migration**: System 1/2 dual-system thinking is still supported through `ContextManager` and `ConfidenceEstimator`. The routing logic is now implicit based on query features and confidence scores.

### ✨ New Features

#### 2. Enhanced Projection System
- **Async Projection**: `create_projection()` is now an async method
- **Budget Control**: New `total_budget` parameter (default: 2000 tokens)
- **Projection Modes**: Support for 5 projection modes (MINIMAL, STANDARD, CONTEXTUAL, ANALYTICAL, DEBUG)
- **Auto Mode Detection**: Automatically detects appropriate projection mode based on instruction
- **Event Publishing**: New `agent.context.projected` event for observability

#### 3. Enhanced Memory System
- **Sync Addition**: New `add_sync()` method for projection (skips vectorization)
- **L4 Compression**: Automatic L4 knowledge base compression when facts exceed threshold
- **Performance**: Improved projection performance by using sync operations

#### 4. Enhanced Feature Extraction
- **Tool Detection**: New `tool_required` field in `QueryFeatures`
- **Multilingual Support**: Tool intent detection supports Chinese and English keywords
- **Better Classification**: Improved query classification accuracy

### 🔧 Improvements

#### 5. Simplified Configuration
- **CognitiveSystemConfig**: Simplified from "routing + memory + context" to "memory + context"
- **Builder API**: Removed `AgentMetaConfig`, using direct `role` and `system_prompt` fields
- **Less Nesting**: Reduced configuration complexity

#### 6. Code Quality
- **ContextAssembler**: Now requires `dispatcher` parameter for event publishing
- **Async Methods**: `load_resource()` is now async
- **Import Cleanup**: Simplified imports in FractalOrchestrator

### 📚 Documentation

- Updated architecture documentation to reflect Router removal
- Added comprehensive projection strategy documentation
- Updated memory system documentation with L4 compression details

### 🐛 Bug Fixes

- Fixed projection context not being properly applied to child agents
- Improved error handling in projection creation

## [0.3.6] - 2026-01-05

### 🧠 The "Sentient Memory" Release

Loom v0.3.6 brings a massive upgrade to the memory and execution systems, making agents more "sentient" with persistent semantic memory and truly recursive capabilities.

### ✨ Core Features

#### 1. Composite Memory System (L4 Semantic Memory)
- **Persistency**: Integrated `Qdrant` for vector-based semantic memory. Agents now "remember" facts across sessions.
- **L1-L4 Hierarchy**: Formalized memory layers:
    - **L1 (Reaction)**: Ephemeral working memory.
    - **L2 (Working)**: Short-term task context.
    - **L3 (Episodic)**: History of past interactions.
    - **L4 (Semantic)**: Crystallized knowledge and user persona.
- **Metabolic Lifecycle**: `Ingest` -> `Digest` -> `Assimilate` loop for automated memory consolidation.

#### 2. Protocol-Based Recursive Mechanism
- **Infinite Delegation**: Agents can delegate tasks to other nodes recursively with no depth limit.
- **Fractal Orchestrator**: Unifies execution logic, treating every sub-task as a recursive node call.
- **ToolExecutor Unification**: Merged `FractalOrchestrator` and `ToolExecutor` into a single, robust execution engine.

#### 3. Context Intelligence
- **Compression**: Smart context compression to retain critical information (L4 facts) while summarizing older interactions.
- **Token Optimization**: Reduced token usage by ~60% through active context management.

#### 4. Built-in Skills Architecture
- **DDD Structure**: Skills are now organized using Domain-Driven Design principles.
- **Native Skills**: Added `device_news`, `device_calendar`, `knowledge_search`, and `device_divination` as standard skills.

### 🐛 Bug Fixes
- Fixed `net::ERR_CONNECTION_REFUSED` in Manager API.
- Optimized cache invalidation for voice requests (O(K) complexity).
- Resolved Docker module errors for `wayne_shared`.

## [0.3.0] - 2025-12-23

### 🧬 The "Controlled Fractal" Release

Loom v0.3.0 represents a complete architectural evolution, introducing the "Controlled Fractal" design philosophy. This release shifts from a simple agent looper to a robust, distributed-ready kernel.

### 🌟 Core Architecture
- **Fractal Nodes**: Unified `Agent`, `Tool`, and `Crew` as standard `Node` implementations. Nodes can be composed recursively.
- **Protocol-First**: Replaced rigid inheritance with `typing.Protocol` interfaces (`NodeProtocol`, `TransportProtocol`).
- **Universal Event Bus**: Introduced a standardized CloudEvents-based bus for all communication.
- **Metabolic Memory**: New biological memory system (`Ingest` -> `Digest` -> `Assimilate`) to prevent context overflow.

### ✨ Key Features
- **LoomApp**: New high-level facade for managing the kernel, bus, and interceptors.
- **Interceptors**: AOP-style hooks for `Budget`, `Timeout`, and `HITL` (Human-in-the-loop).
- **Attention Router**: New node type that dynamically routes tasks using LLM reasoning.
- **Bilingual Documentation**: Complete English and Chinese documentation suite (`docs/` and `docs/zh/`).

### 📦 Breaking Changes
- Replaced `loom.agent()` factory with `LoomApp` and `AgentNode` classes.
- Moved core logic from `loom.core` to `loom.kernel` and `loom.node`.
- Updated configuration format to use `control_config` dictionaries.

## [0.2.1] - 2025-12-22

### 🎯 Major Simplification Release

This release focuses on **radical simplification** and **code clarity**, removing verbose documentation and streamlining the codebase to its essential core.

### 📚 Documentation Overhaul

- **Removed 18,000+ lines** of verbose, redundant documentation
- Simplified documentation structure to focus on practical usage
- Streamlined API documentation for better clarity
- Removed outdated guides and examples that caused confusion

### 🔧 Code Simplification

- **loom/__init__.py**: Reduced from ~400 lines to ~45 lines - cleaner exports and better AI-readable structure
- **loom/core/message.py**: Major simplification - removed ~900 lines of complexity
- **loom/patterns/crew.py**: Streamlined by ~1,200 lines - focused on core functionality
- **loom/builtin/***: Simplified module exports and reduced boilerplate

### ✨ Philosophy

This release embodies the principle: **"Perfection is achieved not when there is nothing more to add, but when there is nothing left to take away."**

- Focus on core functionality
- Remove abstractions that don't add value
- Make the codebase more maintainable and understandable
- Improve AI agent comprehension of the framework

### 🎯 Impact

- **Faster onboarding**: Less documentation to read, clearer structure
- **Better maintainability**: Less code to maintain and debug
- **Improved clarity**: Core concepts are more visible
- **AI-friendly**: Simplified structure is easier for AI agents to understand and use

## [0.2.0] - 2025-12-20

### 🚀 Major Features

- **Loom Studio**: A complete visual development platform including `loom.studio` (Web UI) and `loom.visualization` (CLI & HTTP Tracers).
- **Native MCP Support**: Implementation of the Model Context Protocol (MCP), allowing seamless integration with external tool servers (`loom.tools.mcp`).
- **Concurrency Safety**: Completely refactored `AgentExecutor` to support thread-safe parallel execution by isolating state into `RunContext`.

### ✨ Enhancements

- Added `rich` based CLI visualization handler.
- Added `fastapi` and `uvicorn` support for the Studio server.
- Improved dependency management with optional extras (`studio`).
- Enhanced `AgentEvent` system to support visualization needs.

### 🐛 Bug Fixes

- Fixed a critical race condition in `AgentExecutor` where recursion depth and stats were stored in instance attributes, causing issues in parallel execution modes.

## [0.1.10] - 2025-12-15
... (Older versions)
