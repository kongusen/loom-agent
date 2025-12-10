"""
Crew System - Multi-Agent Team Coordination

This module provides the Crew abstraction for managing teams of specialized agents
working together on complex tasks.

Design Philosophy:
- Crew coordinates multiple specialized agents
- Each agent has a role with specific capabilities
- Agents communicate via MessageBus and SharedState
- Inspired by CrewAI with loom's event sourcing advantages

Example:
    ```python
    from loom.crew import Crew, Role
    from loom.crew.orchestration import Task, OrchestrationPlan, OrchestrationMode

    # Define roles
    roles = [
        Role(
            name="researcher",
            goal="Gather information",
            tools=["read_file", "grep"],
            capabilities=["research"]
        ),
        Role(
            name="developer",
            goal="Write code",
            tools=["write_file", "edit_file"],
            capabilities=["coding"]
        )
    ]

    # Create crew
    crew = Crew(roles=roles, llm=llm)

    # Define tasks
    tasks = [...]

    # Create plan and execute
    plan = OrchestrationPlan(tasks=tasks)
    results = await crew.kickoff(plan)
    ```
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Any, TYPE_CHECKING
from uuid import uuid4

from loom.crew.roles import Role
from loom.crew.orchestration import Task, OrchestrationPlan, Orchestrator
from loom.crew.communication import MessageBus, SharedState
from loom.crew.performance import PerformanceMonitor

if TYPE_CHECKING:
    from loom.components.agent import Agent
    from loom.interfaces.llm import BaseLLM


@dataclass
class CrewMember:
    """
    Crew member representing an agent with a role.

    Attributes:
        agent_id: Unique identifier for this crew member
        role: Role definition for this member
        agent: Agent instance (optional, created lazily)
    """

    agent_id: str
    role: Role
    agent: Optional["Agent"] = None


class Crew:
    """
    Multi-agent team coordinator.

    Crew manages a team of agents with different roles, coordinating
    their work on complex tasks through orchestration plans.

    Example:
        ```python
        crew = Crew(roles=[researcher_role, developer_role], llm=llm)

        task = Task(
            id="research",
            description="Research project",
            prompt="Analyze the codebase",
            assigned_role="researcher"
        )

        result = await crew.execute_task(task)
        ```
    """

    def __init__(
        self,
        roles: List[Role],
        llm: Optional["BaseLLM"] = None,
        message_bus: Optional[MessageBus] = None,
        shared_state: Optional[SharedState] = None,
        enable_delegation: bool = True,
        max_iterations: int = 20,
        enable_performance_monitoring: bool = True,
    ):
        """
        Initialize crew.

        Args:
            roles: List of roles for crew members
            llm: LLM instance (optional, for creating agents)
            message_bus: Message bus for inter-agent communication
            shared_state: Shared state for coordination
            enable_delegation: Whether to enable task delegation
            max_iterations: Default max iterations for agents
            enable_performance_monitoring: Enable performance tracking
        """
        self.roles = roles
        self.llm = llm
        self.message_bus = message_bus or MessageBus()
        self.shared_state = shared_state or SharedState()
        self.enable_delegation = enable_delegation
        self.max_iterations = max_iterations

        # Initialize crew members (lazy agent creation)
        self.members: Dict[str, CrewMember] = {}
        self._initialize_members()

        # Orchestrator for executing plans
        self.orchestrator = Orchestrator()

        # Performance monitoring
        self.enable_performance_monitoring = enable_performance_monitoring
        self.performance_monitor = PerformanceMonitor() if enable_performance_monitoring else None

    def _initialize_members(self):
        """
        Initialize crew members (without creating agents yet).

        Agents are created lazily when needed to avoid unnecessary overhead.
        """
        for role in self.roles:
            agent_id = f"{role.name}_{uuid4().hex[:8]}"

            member = CrewMember(
                agent_id=agent_id,
                role=role,
                agent=None  # Lazy creation
            )

            self.members[role.name] = member

    def _get_or_create_agent(self, role_name: str) -> "Agent":
        """
        Get or create agent for a role.

        Args:
            role_name: Name of the role

        Returns:
            Agent: Agent instance for the role

        Raises:
            ValueError: If role not found or cannot create agent
        """
        if role_name not in self.members:
            raise ValueError(f"Role '{role_name}' not found in crew")

        member = self.members[role_name]

        # Create agent if not exists
        if member.agent is None:
            if self.llm is None:
                raise ValueError(
                    "Cannot create agent: no LLM provided to Crew. "
                    "Either provide llm parameter or create agents manually."
                )

            # Import here to avoid circular import
            from loom.components.agent import Agent

            # Build system instructions
            system_instructions = self._build_system_instructions(member.role)

            # Create agent with role configuration
            member.agent = Agent(
                llm=self.llm,
                system_instructions=system_instructions,
                max_iterations=member.role.max_iterations or self.max_iterations,
            )

            # Record agent creation
            if self.performance_monitor:
                self.performance_monitor.record_agent_create(role_name)
        else:
            # Record agent reuse
            if self.performance_monitor:
                self.performance_monitor.record_agent_reuse(role_name)

        return member.agent

    def _build_system_instructions(self, role: Role) -> str:
        """
        Build system instructions for a role.

        Args:
            role: Role to build instructions for

        Returns:
            str: System instructions
        """
        instructions = f"""You are a {role.name}.

**Role Description**: {role.description}

**Goal**: {role.goal}
"""

        if role.backstory:
            instructions += f"\n**Background**: {role.backstory}\n"

        if role.capabilities:
            instructions += f"\n**Capabilities**: {', '.join(role.capabilities)}\n"

        if role.tools:
            instructions += f"\n**Available Tools**: {', '.join(role.tools)}\n"

        if role.delegation and self.enable_delegation:
            instructions += """
**Delegation**: You can delegate tasks to other team members when needed.
Use clear task descriptions and specify the target role.
"""

        return instructions

    async def execute_task(
        self,
        task: Task,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Execute a single task.

        Args:
            task: Task to execute
            context: Optional execution context

        Returns:
            str: Task result

        Raises:
            ValueError: If assigned role not found
        """
        # Start performance tracking
        if self.performance_monitor:
            self.performance_monitor.start_task(task.id, task.assigned_role)

        try:
            # Get or create agent for role
            agent = self._get_or_create_agent(task.assigned_role)

            # Build full context
            full_context = {
                **(context or {}),
                **task.context,
                "shared_state": self.shared_state,
                "message_bus": self.message_bus,
            }

            # Inject context into prompt
            prompt_with_context = self._inject_context(task.prompt, full_context)

            # Execute task
            result = await agent.run(prompt_with_context)

            # Finish performance tracking (success)
            if self.performance_monitor:
                self.performance_monitor.finish_task(task.id, success=True)

            return result

        except Exception as e:
            # Finish performance tracking (failure)
            if self.performance_monitor:
                self.performance_monitor.finish_task(
                    task.id, success=False, error=str(e)
                )
            raise

    async def kickoff(
        self,
        plan: OrchestrationPlan,
    ) -> Dict[str, Any]:
        """
        Start crew execution with orchestration plan.

        Args:
            plan: Orchestration plan with tasks

        Returns:
            Dict[str, Any]: Task results keyed by task ID

        Example:
            ```python
            plan = OrchestrationPlan(
                tasks=[task1, task2, task3],
                mode=OrchestrationMode.PARALLEL
            )

            results = await crew.kickoff(plan)
            print(results["task1"])
            ```
        """
        # Start orchestration tracking
        if self.performance_monitor:
            orch_id = self.performance_monitor.start_orchestration()

        import time
        start_time = time.time()

        try:
            results = await self.orchestrator.execute(plan, self)

            # Finish orchestration tracking
            if self.performance_monitor:
                duration = time.time() - start_time
                self.performance_monitor.finish_orchestration(duration)

            return results

        except Exception as e:
            # Record orchestration failure
            if self.performance_monitor:
                duration = time.time() - start_time
                self.performance_monitor.finish_orchestration(duration)
            raise

    def _inject_context(self, prompt: str, context: Dict[str, Any]) -> str:
        """
        Inject context into prompt.

        Args:
            prompt: Original prompt
            context: Context dictionary

        Returns:
            str: Prompt with injected context
        """
        # Filter out non-serializable objects
        safe_context = {
            k: v for k, v in context.items()
            if k not in ["shared_state", "message_bus", "dependency_results"]
        }

        if not safe_context:
            return prompt

        context_str = "\n".join([
            f"**{key}**: {value}"
            for key, value in safe_context.items()
        ])

        return f"""{prompt}

**Additional Context**:
{context_str}
"""

    def get_member(self, role_name: str) -> Optional[CrewMember]:
        """
        Get crew member by role name.

        Args:
            role_name: Name of the role

        Returns:
            Optional[CrewMember]: Crew member if found
        """
        return self.members.get(role_name)

    def list_roles(self) -> List[str]:
        """
        Get list of available role names.

        Returns:
            List[str]: Role names
        """
        return list(self.members.keys())

    def get_stats(self) -> Dict[str, Any]:
        """
        Get crew statistics.

        Returns:
            Dict: Statistics including member count, message bus stats,
                  and performance metrics if enabled
        """
        stats = {
            "total_members": len(self.members),
            "roles": self.list_roles(),
            "message_bus_stats": self.message_bus.get_stats(),
            "enable_delegation": self.enable_delegation,
        }

        # Add performance stats if monitoring enabled
        if self.performance_monitor:
            stats["performance"] = self.performance_monitor.get_stats()

        return stats

    def get_performance_summary(self) -> Optional[str]:
        """
        Get human-readable performance summary.

        Returns:
            Optional[str]: Performance summary or None if monitoring disabled
        """
        if self.performance_monitor:
            return self.performance_monitor.get_summary()
        return None

    def reset_performance_stats(self) -> None:
        """Reset performance statistics"""
        if self.performance_monitor:
            self.performance_monitor.reset()
