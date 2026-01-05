"""
Protocol Layer - Interface Definitions and Standards

This module provides standardized protocols, message formats, and interface
contracts used across the Loom agent system.

Key Components:
- CloudEvents: Event format for message bus communication
- MCP: Model Context Protocol for tool definitions
- Delegation: Fractal architecture delegation protocol
- Memory Operations: Memory system interface contracts
"""

# CloudEvents Protocol
from .cloudevents import CloudEvent, EventType

# Model Context Protocol (MCP)
from .mcp import MCPToolDefinition

# Delegation Protocol
from .delegation import (
    DelegationRequest,
    DelegationResult,
    SubtaskSpecification,
    TaskDecomposition,
    DELEGATE_SUBTASKS_TOOL,
)

# Memory Operations Protocol
from .memory_operations import (
    MemoryValidator,
    ContextSanitizer,
    ProjectStateObject,
)

# Interface Definitions
try:
    from .interfaces import *
except ImportError:
    # interfaces.py may not have exports
    pass

__all__ = [
    # CloudEvents
    "CloudEvent",
    "EventType",
    # MCP
    "MCPToolDefinition",
    # Delegation
    "DelegationRequest",
    "DelegationResult",
    "SubtaskSpecification",
    "TaskDecomposition",
    "DELEGATE_SUBTASKS_TOOL",
    # Memory
    "MemoryValidator",
    "ContextSanitizer",
    "ProjectStateObject",
]
