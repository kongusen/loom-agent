# Changelog

All notable changes to this project will be documented in this file.


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

- **Vector Dimensions**: Updated default vector size from 1536 to 512 (BGE embedding)
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
