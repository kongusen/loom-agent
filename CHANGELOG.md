# Changelog

## [0.5.6] - 2026-02-12

### 🔭 可观测性系统（全新模块）

- **LoomTracer**：结构化追踪，支持嵌套 Span（Agent → Iteration → LLM → Tool），12 种 SpanKind
- **LoomMetrics**：Counter / Gauge / Histogram 三类指标，14 个预定义指标常量
- **导出器**：LogSpanExporter（日志）、InMemoryExporter（测试）、`trace_operation` 装饰器
- **零侵入集成**：tracer/metrics 均为可选参数，不传则无开销

### 🔍 统一检索系统

- **双通道设计**：主动通道（Agent 调用 `query` 工具）+ 被动通道（上下文构建时自动检索）
- **UnifiedSearchToolBuilder**：根据是否配置 knowledge_base 动态生成工具定义和描述
- **UnifiedSearchExecutor**：L1 缓存 → 路由 → QueryRewriter 查询增强 → 并行检索 → Reranker 四信号重排序
- **UnifiedRetrievalSource**：被动通道，L4 语义 + RAG 知识库并行召回，预算感知注入
- **QueryRewriter**：纯文本处理，从对话上下文提取高频实词追加到查询
- **Reranker**：VectorScore(0.4) + QueryOverlap(0.35) + OriginDiversity(0.15) + ContentLength(0.1)

### 📚 RAG 知识管线重构

- **GraphRAGKnowledgeBase.from_config()**：根据可用能力自动选择检索策略（hybrid / graph_first / vector_first / graph_only）
- **HybridStrategy 三路融合**：图检索 + 向量检索并行，新增图谱扩展（chunk→entity→relation→entity→chunk），三路加权融合
- **图谱扩展**：向量命中 chunk 沿 `entity_ids` 桥接到知识图谱，1-hop 遍历发现结构相关 chunk
- **检索观测集成**：策略层自动记录 Span 属性（strategy / graph_count / vector_count / expansion_count / parallel_ms 等）
- **ExtractionConfig**：Skill 模式的实体/关系提取配置，用户配置方向，框架提供提取逻辑
- **关键词提取**：chunker 自动提取 CamelCase / snake_case / ALL_CAPS / dotted.path 标识符

### 🤝 SharedMemoryPool（跨 Agent 共享记忆）

- **进程内共享**：多个 Agent 持有同一 pool 引用进行读写
- **版本控制**：自增版本号，可选乐观锁（`expected_version` 参数）
- **EventBus 集成**：写入/删除自动发布事件
- **上下文自动注入**：SharedPoolSource 将共享条目以 `[SHARED:key]` 前缀注入 LLM 上下文
- **分形继承**：子节点自动继承父节点的 shared_pool 引用

### 🧠 记忆系统增强

- **L4Compressor 保真度检查**：FidelityChecker 通过 embedding 余弦相似度(0.6) + 关键词保留率(0.4) 评估压缩质量，低于阈值保留原始 facts
- **MemoryReranker**：统一重排序器，支持 recency / importance / relevance / frequency 四信号
- **AdaptiveBudgetManager**：根据任务阶段动态调整上下文预算分配比例

### 🏗️ Agent 架构重构

- **ExecutionEngine**：从 Agent.core 提取的独立执行引擎
- **AgentFactory**：从 Agent.create() 提取的工厂类，处理渐进式披露配置
- **ToolRouter**：从 core.py 提取的工具路由组件，分发元工具 / 沙盒工具 / 动态工具 / 检索工具
- **Checkpoint**：运行时检查点系统

### 📖 Wiki 全面重写

- 删除 20+ 旧 wiki 页面（API-Agent, Fractal-Architecture, Memory-Layers 等）
- 新建 10 个聚焦页面：Agent, Architecture, Config, Context, Events, Fractal, Memory, Providers, Runtime, Tools
- Observability.md 全面重写：12 种 SpanKind、14 个预定义指标、知识检索观测章节
- Providers.md 新增 RAG 检索流程详细文档：四种策略数据流、双向关联使用表、权重配置

### 🧹 清理与整合

- 删除 `docs/` 目录全部 40+ 旧文档（archive, features, framework, optimization, refactoring, usage）
- 删除旧示例（cli_stream_demo, conversational_assistant, task_executor 等）
- 新增 4 个 demo：17_memory_rag_autowiring, 18_adaptive_budget, 19_tracing_metrics, 20_checkpoint
- 新增 README_CN.md 中文说明
- 更新 16 个现有 demo 适配新 API

### ✅ 测试

- 新增测试：test_knowledge/, test_phase4_observability, test_phase5_wiring, test_unified_search, test_shared_pool, test_client_pool, test_tokenizer_cache
- 全量回归：1267 passed, 10 skipped, 0 failures

---

## [0.5.5] - 2026-02-10

- 清理 FractalMemory，采用统一 Session-EventBus 架构
- 移除 FractalMemory 独立模块，记忆统一由 MemoryManager 管理

## [0.5.4] - 2026-02-09

- Context 模块重构：ContextOrchestrator 统一入口，多源收集 + 预算管理 + 压缩
- 多 Agent 协作系统：OutputCollector 支持 interleaved/sequential/grouped 三种输出策略

## [0.5.3] - 2026-02-08

- FractalStreamAPI：分形架构的流式 API 支持
- Version API：版本信息查询接口

## [0.5.2] - 2026-02-07

- Tools 模块重构：SandboxToolManager 统一工具注册和沙盒执行
- Skills 热更新系统：运行时 Skill 发现和激活

## [0.5.1] - 2026-02-05

- 隐藏变量暴露：Agent 内部状态可观测
- 可观测性改进：性能优化和模块重构

---

## [0.5.0] - 2026-02-03

### ⚠️ BREAKING CHANGES

这是一个重大重构版本，引入了全新的Agent API和统一架构。

### 🌟 Agent API重构（渐进式披露）

**核心理念：Progressive Disclosure**
- **Agent.create()**: 统一的Agent创建接口，支持渐进式参数披露
- **capabilities参数**: 声明式能力配置（reflection、planning、delegation）
- **skills参数**: 三种形态的Skill激活（指令注入、工具编译、节点实例化）
- 移除deprecated的LoomApp和AgentConfig

### 🧠 统一内存架构

**MemoryManager整合**：
- 整合LoomMemory（L1-L4分层）和FractalMemory（作用域）
- 实现SHARED内存作用域的双向传播（parent↔child）
- ContextOrchestrator统一上下文构建

### 🔧 Skills和Tools系统整合

**三种Skill激活形态**：
- Form 1: 指令注入（知识增强）
- Form 2: 工具编译（能力扩展）
- Form 3: 节点实例化（委派协作）

**SandboxToolManager**：
- 统一工具管理和沙箱隔离
- 支持动态工具创建和注册

### 🐛 Bug修复

- 修复12个ruff linting错误（导入排序、未使用导入）
- 修复SHARED内存作用域双向传播机制
- 修复测试中的MockLLMProvider接口实现
- 移除未使用的方法参数

### 📚 文档更新

- 添加v0.4.x → v0.5.0迁移指南
- 更新API参考文档
- 清理临时开发文档和测试记录

### ✅ 测试

- 1136 tests passed
- Coverage: 81.83%
- 所有linting检查通过

## [0.4.4] - 2026-01-28

### ✅ Context & Memory升级（会话显式化）

- **session_id** 显式化：Task/MemoryUnit/TaskSummary/Fact 统一携带 `session_id`，上层决定会话边界  
- **L3/L4 语义升级**：L3=会话摘要，L4=跨会话长期记忆  
- **记忆检索**：L1/L2/L3 支持按 `session_id` 过滤，L4 默认跨会话  

### 🧠 上下文管理（Direct/Bus分离）

- **L1 = Direct + 近期**，**L2 = Bus相关**，比例可配置  
- **Direct/BUS 保底条数**：避免关键消息被 token 压制  
- **EventBus 点对点**：新增 `query_by_target`，支持 TTL/priority  
- **统一直连协议字段**：`node.message` + `content/priority/ttl/session`  

### 🔧 工具与框架

- 上下文工具支持 `session_id` 查询  
- EventBusDelegation / Agent 事件传递 session  

### ✅ 测试

- `pytest tests/unit/test_memory tests/unit/test_events tests/unit/test_tools tests/unit/test_orchestration -q`  

All notable changes to this project will be documented in this file.


## [0.4.2] - 2026-01-25

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
