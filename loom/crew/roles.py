"""
Role System - Agent Role Definitions and Registry

This module provides the Role abstraction for defining agent capabilities,
goals, and tool access in a multi-agent crew.

Design Philosophy:
- Roles define "what" an agent does, not "how" it does it
- Roles are reusable templates for creating specialized agents
- Inspired by CrewAI's role system with loom's extensibility

Example:
    ```python
    from loom.crew.roles import Role, RoleRegistry, BUILTIN_ROLES

    # Use built-in role
    researcher = BUILTIN_ROLES["researcher"]

    # Define custom role
    custom_role = Role(
        name="data_analyst",
        description="Specialist in data analysis and visualization",
        goal="Extract insights from data and create visual representations",
        backstory="Expert data scientist with 10 years of experience",
        tools=["read_file", "python_repl", "plot"],
        capabilities=["data_analysis", "visualization", "statistics"]
    )

    # Register custom role
    RoleRegistry.register(custom_role)

    # Retrieve role
    role = RoleRegistry.get("data_analyst")
    ```
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class Role:
    """
    Agent role definition with goals, capabilities, and tool access.

    A Role defines the responsibilities, capabilities, and constraints
    of an agent in a multi-agent system. Roles are used to create
    specialized agents with specific expertise.

    Attributes:
        name: Unique role identifier (e.g., "researcher", "developer")
        description: Human-readable role description
        goal: Primary objective of this role
        backstory: Background narrative to enhance LLM context
        tools: List of allowed tool names (empty = no tools, ["*"] = all tools)
        capabilities: Capability tags for role selection (e.g., "code_analysis")
        max_iterations: Maximum recursion depth for agents with this role
        model_name: Optional model override for this role
        delegation: Whether this role can delegate tasks to other agents
        metadata: Additional role-specific configuration
    """

    name: str
    description: str
    goal: str
    backstory: str = ""
    tools: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)
    max_iterations: int = 20
    model_name: Optional[str] = None
    delegation: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate role configuration"""
        if not self.name:
            raise ValueError("Role name cannot be empty")
        if not self.goal:
            raise ValueError(f"Role '{self.name}' must have a goal")

    def allows_tool(self, tool_name: str) -> bool:
        """
        Check if this role allows using a specific tool.

        Args:
            tool_name: Name of the tool to check

        Returns:
            bool: True if tool is allowed, False otherwise
        """
        if not self.tools:
            return False
        if "*" in self.tools:
            return True
        return tool_name in self.tools

    def has_capability(self, capability: str) -> bool:
        """
        Check if this role has a specific capability.

        Args:
            capability: Capability tag to check

        Returns:
            bool: True if capability exists, False otherwise
        """
        return capability in self.capabilities

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize role to dictionary.

        Returns:
            Dict: Role data as dictionary
        """
        return {
            "name": self.name,
            "description": self.description,
            "goal": self.goal,
            "backstory": self.backstory,
            "tools": self.tools,
            "capabilities": self.capabilities,
            "max_iterations": self.max_iterations,
            "model_name": self.model_name,
            "delegation": self.delegation,
            "metadata": self.metadata,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> Role:
        """
        Deserialize role from dictionary.

        Args:
            data: Role data dictionary

        Returns:
            Role: Reconstructed role
        """
        return Role(
            name=data["name"],
            description=data["description"],
            goal=data["goal"],
            backstory=data.get("backstory", ""),
            tools=data.get("tools", []),
            capabilities=data.get("capabilities", []),
            max_iterations=data.get("max_iterations", 20),
            model_name=data.get("model_name"),
            delegation=data.get("delegation", False),
            metadata=data.get("metadata", {}),
        )

    def __repr__(self) -> str:
        return (
            f"Role(name={self.name!r}, "
            f"capabilities={self.capabilities}, "
            f"tools={len(self.tools)}, "
            f"delegation={self.delegation})"
        )


class RoleRegistry:
    """
    Central registry for managing agent roles.

    Provides a global registry for roles that can be accessed across
    the crew system. Supports built-in roles and custom role registration.

    Example:
        ```python
        # Register custom role
        RoleRegistry.register(custom_role)

        # Get role
        role = RoleRegistry.get("researcher")

        # List all roles
        all_roles = RoleRegistry.list_roles()

        # Check if role exists
        if RoleRegistry.has_role("developer"):
            print("Developer role available")
        ```
    """

    _registry: Dict[str, Role] = {}

    @classmethod
    def register(cls, role: Role) -> None:
        """
        Register a role in the global registry.

        Args:
            role: Role to register

        Raises:
            ValueError: If role with same name already exists
        """
        if role.name in cls._registry:
            raise ValueError(
                f"Role '{role.name}' already registered. "
                f"Use update() to modify existing roles."
            )
        cls._registry[role.name] = role

    @classmethod
    def update(cls, role: Role) -> None:
        """
        Update an existing role or register if not exists.

        Args:
            role: Role to update/register
        """
        cls._registry[role.name] = role

    @classmethod
    def get(cls, name: str) -> Optional[Role]:
        """
        Get role by name.

        Args:
            name: Role name

        Returns:
            Optional[Role]: Role if found, None otherwise
        """
        return cls._registry.get(name)

    @classmethod
    def has_role(cls, name: str) -> bool:
        """
        Check if role exists in registry.

        Args:
            name: Role name

        Returns:
            bool: True if role exists, False otherwise
        """
        return name in cls._registry

    @classmethod
    def list_roles(cls) -> List[Role]:
        """
        Get all registered roles.

        Returns:
            List[Role]: List of all roles
        """
        return list(cls._registry.values())

    @classmethod
    def list_role_names(cls) -> List[str]:
        """
        Get names of all registered roles.

        Returns:
            List[str]: List of role names
        """
        return list(cls._registry.keys())

    @classmethod
    def remove(cls, name: str) -> bool:
        """
        Remove role from registry.

        Args:
            name: Role name to remove

        Returns:
            bool: True if role was removed, False if not found
        """
        if name in cls._registry:
            del cls._registry[name]
            return True
        return False

    @classmethod
    def clear(cls) -> None:
        """Clear all roles from registry (useful for testing)."""
        cls._registry.clear()

    @classmethod
    def find_by_capability(cls, capability: str) -> List[Role]:
        """
        Find all roles with a specific capability.

        Args:
            capability: Capability tag to search for

        Returns:
            List[Role]: Roles with the capability
        """
        return [role for role in cls._registry.values() if role.has_capability(capability)]


# ============================================================================
# Built-in Roles - Enterprise-grade role templates
# ============================================================================

BUILTIN_ROLES = {
    "manager": Role(
        name="manager",
        description="Project manager and team coordinator",
        goal="Coordinate team activities and ensure task completion",
        backstory=(
            "Experienced project manager with expertise in coordinating "
            "multi-agent teams and ensuring efficient task execution. "
            "Specializes in breaking down complex projects into manageable tasks "
            "and delegating to appropriate team members."
        ),
        tools=["task", "delegate"],
        capabilities=["planning", "coordination", "delegation", "oversight"],
        max_iterations=30,
        delegation=True,
    ),
    "researcher": Role(
        name="researcher",
        description="Information gathering and analysis specialist",
        goal="Gather, analyze, and synthesize information from various sources",
        backstory=(
            "Expert researcher with strong analytical skills. "
            "Specializes in information retrieval, data analysis, and "
            "synthesizing complex information into actionable insights. "
            "Experienced in working with codebases, documentation, and data sources."
        ),
        tools=["read_file", "grep", "glob", "web_search"],
        capabilities=["information_gathering", "analysis", "synthesis", "research"],
        max_iterations=25,
    ),
    "developer": Role(
        name="developer",
        description="Software development and coding specialist",
        goal="Write, modify, and maintain high-quality code",
        backstory=(
            "Senior software engineer with expertise in multiple programming languages. "
            "Specializes in writing clean, maintainable code following best practices. "
            "Experienced in implementing features, fixing bugs, and refactoring code."
        ),
        tools=["read_file", "write_file", "edit_file", "bash", "grep", "glob"],
        capabilities=["coding", "debugging", "refactoring", "implementation"],
        max_iterations=30,
    ),
    "qa_engineer": Role(
        name="qa_engineer",
        description="Quality assurance and testing specialist",
        goal="Ensure code quality through comprehensive testing and validation",
        backstory=(
            "Experienced QA engineer with focus on test automation and quality assurance. "
            "Specializes in writing test cases, identifying edge cases, and "
            "ensuring code reliability and correctness."
        ),
        tools=["read_file", "bash", "grep", "write_file"],
        capabilities=["testing", "quality_assurance", "validation", "test_automation"],
        max_iterations=20,
    ),
    "security_auditor": Role(
        name="security_auditor",
        description="Security analysis and vulnerability assessment specialist",
        goal="Identify security vulnerabilities and ensure secure coding practices",
        backstory=(
            "Security expert with deep knowledge of common vulnerabilities and "
            "secure coding practices. Specializes in code review from a security "
            "perspective, identifying OWASP top 10 issues, and recommending fixes."
        ),
        tools=["read_file", "grep", "glob"],
        capabilities=["security_analysis", "vulnerability_assessment", "code_review"],
        max_iterations=20,
    ),
    "tech_writer": Role(
        name="tech_writer",
        description="Technical documentation specialist",
        goal="Create clear, comprehensive technical documentation",
        backstory=(
            "Technical writer with expertise in creating user-friendly documentation. "
            "Specializes in API docs, user guides, and code documentation. "
            "Experienced in translating complex technical concepts into clear language."
        ),
        tools=["read_file", "write_file", "grep", "glob"],
        capabilities=["documentation", "technical_writing", "communication"],
        max_iterations=20,
    ),
}


def register_builtin_roles() -> None:
    """
    Register all built-in roles in the global registry.

    This function should be called during module initialization to
    make built-in roles available through RoleRegistry.
    """
    for role in BUILTIN_ROLES.values():
        RoleRegistry.update(role)


# Auto-register built-in roles on module import
register_builtin_roles()
