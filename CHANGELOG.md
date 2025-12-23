# Changelog

All notable changes to this project will be documented in this file.

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
