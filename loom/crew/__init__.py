"""
Loom Crew - Enterprise Multi-Agent Collaboration System

This module provides CrewAI/AutoGen-level team collaboration capabilities
while maintaining loom-agent's unique event sourcing and crash recovery advantages.

Key Components:
- Role: Agent role definitions with goals, tools, and capabilities
- RoleRegistry: Central registry for managing roles
- Task: Task definition with dependencies and context
- OrchestrationPlan: Multi-task execution plans
- Orchestrator: Task execution coordinator
- MessageBus: Inter-agent communication system
- SharedState: Thread-safe shared state management
- Crew: Multi-agent team coordinator
- CrewMember: Individual team member representation

Example:
    ```python
    from loom.crew import Crew, Role, Task, OrchestrationPlan, OrchestrationMode

    # Define roles
    roles = [
        Role(
            name="researcher",
            goal="Gather and analyze information",
            tools=["read_file", "grep"],
            capabilities=["information_gathering"]
        ),
        Role(
            name="developer",
            goal="Write and modify code",
            tools=["write_file", "edit_file"],
            capabilities=["coding"]
        )
    ]

    # Create crew
    crew = Crew(roles=roles)

    # Define tasks
    tasks = [
        Task(
            id="research",
            description="Research codebase",
            prompt="Analyze the project structure",
            assigned_role="researcher",
            output_key="research_result"
        ),
        Task(
            id="implement",
            description="Implement feature",
            prompt="Add new feature based on research",
            assigned_role="developer",
            dependencies=["research"]
        )
    ]

    # Execute
    plan = OrchestrationPlan(tasks=tasks, mode=OrchestrationMode.SEQUENTIAL)
    results = await crew.kickoff(plan)
    ```
"""

from __future__ import annotations

__version__ = "0.1.0"

# Phase 1: Roles
from loom.crew.roles import Role, RoleRegistry, BUILTIN_ROLES

# Phase 2: Orchestration
from loom.crew.orchestration import (
    Task,
    OrchestrationPlan,
    OrchestrationMode,
    Orchestrator
)

# Phase 3: Communication
from loom.crew.communication import (
    AgentMessage,
    MessageType,
    MessageBus,
    SharedState
)

# Phase 4: Crew
from loom.crew.crew import Crew, CrewMember

__all__ = [
    # Core version
    "__version__",

    # Roles (Phase 1)
    "Role",
    "RoleRegistry",
    "BUILTIN_ROLES",

    # Orchestration (Phase 2)
    "Task",
    "OrchestrationPlan",
    "OrchestrationMode",
    "Orchestrator",

    # Communication (Phase 3)
    "AgentMessage",
    "MessageType",
    "MessageBus",
    "SharedState",

    # Crew (Phase 4)
    "Crew",
    "CrewMember",
]
