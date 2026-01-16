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

from contextlib import suppress

# CloudEvents Protocol
from .cloudevents import CloudEvent, EventType

# Delegation Protocol
from .delegation import (
    DELEGATE_SUBTASKS_TOOL,
    DelegationRequest,
    DelegationResult,
    SubtaskSpecification,
    TaskDecomposition,
)

# Model Context Protocol (MCP)
from .mcp import MCPToolDefinition

# Memory Operations Protocol
from .memory_operations import (
    ContextSanitizer,
    MemoryValidator,
    ProjectStateObject,
)

# Interface Definitions
with suppress(ImportError):
    from .interfaces import (
        EventBusProtocol,
        LLMProviderProtocol,
        MemoryStrategy,
        NodeProtocol,
        ReflectiveMemoryStrategy,
        TransportProtocol,
    )

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
    # Protocols
    "NodeProtocol",
    "MemoryStrategy",
    "ReflectiveMemoryStrategy",
    "LLMProviderProtocol",
    "TransportProtocol",
    "EventBusProtocol",
]
