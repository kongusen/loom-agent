"""
Loom Execution Engine - "The Brain"
===================================

This module handles the runtime orchestration of Agents.

## 🧠 Core Components

### 1. Agent (`Agent`)
The high-level user interface. It wraps an Engine and exposes standard `Runnable` methods (`invoke`, `stream`).
- **Input**: User string or Message.
- **Output**: Assistant Message.
- **Think**: Managed by the Engine.

### 2. RecursiveEngine (`RecursiveEngine`)
The low-level driver of the "Think-Act-Observe" loop.
- **Responsibility**: 
    1. Prompt assembly (System + History + Context).
    2. LLM calling.
    3. Tool parsing and execution (with concurrency).
    4. Recursion control (Max Depth).

### 3. Context (`ContextAssembler`)
Manages the prompt context window.
- **Priority**: System > Messages > Context.
"""

from .context import ContextAssembler, ContextConfig
from .engine import RecursiveEngine, EngineState
from .agent import Agent

__all__ = [
    "ContextAssembler", 
    "ContextConfig",
    "RecursiveEngine", 
    "EngineState",
    "Agent"
]
