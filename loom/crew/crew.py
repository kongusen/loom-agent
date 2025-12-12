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
from typing import Dict, List, Optional, Any, TYPE_CHECKING, AsyncGenerator
from uuid import uuid4

from loom.crew.roles import Role
from loom.crew.orchestration import Task, OrchestrationPlan, Orchestrator, OrchestrationMode
from loom.crew.communication import MessageBus, SharedState
from loom.crew.performance import PerformanceMonitor
from loom.core.events import AgentEvent, AgentEventType

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

    async def execute_task_stream(
        self,
        task: Task,
        context: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[AgentEvent, None]:
        """
        Execute a single task with streaming events (Core Implementation).

        This is the core streaming implementation. All task execution
        flows through this method.

        Args:
            task: Task to execute
            context: Optional execution context

        Yields:
            AgentEvent: Streaming execution events including:
                - CREW_TASK_START: Task execution started
                - CREW_AGENT_ASSIGNED: Agent assigned to task
                - All agent execution events (LLM_DELTA, TOOL_*, etc.)
                - CREW_TASK_COMPLETE: Task completed successfully
                - CREW_TASK_ERROR: Task failed

        Raises:
            ValueError: If assigned role not found

        Example:
            ```python
            async for event in crew.execute_task_stream(task):
                if event.type == AgentEventType.CREW_TASK_START:
                    print(f"Starting task: {event.metadata['task_id']}")
                elif event.type == AgentEventType.LLM_DELTA:
                    print(event.content, end="", flush=True)
                elif event.type == AgentEventType.CREW_TASK_COMPLETE:
                    print(f"\\nTask completed: {event.content}")
            ```
        """
        # Start performance tracking
        if self.performance_monitor:
            self.performance_monitor.start_task(task.id, task.assigned_role)

        # Emit task start event
        yield AgentEvent(
            type=AgentEventType.CREW_TASK_START,
            metadata={
                "task_id": task.id,
                "task_prompt": task.prompt,
                "assigned_role": task.assigned_role,
            }
        )

        try:
            # Get or create agent for role
            agent = self._get_or_create_agent(task.assigned_role)

            # Emit agent assigned event
            yield AgentEvent(
                type=AgentEventType.CREW_AGENT_ASSIGNED,
                metadata={
                    "task_id": task.id,
                    "role": task.assigned_role,
                    "agent_id": self.members[task.assigned_role].agent_id,
                }
            )

            # Build full context
            full_context = {
                **(context or {}),
                **task.context,
                "shared_state": self.shared_state,
                "message_bus": self.message_bus,
            }

            # Inject context into prompt
            prompt_with_context = self._inject_context(task.prompt, full_context)

            # Stream agent execution
            result_content = ""
            async for event in agent.execute(prompt_with_context):
                # Forward agent events
                yield event

                # Collect final result from AGENT_FINISH event
                if event.type == AgentEventType.AGENT_FINISH and event.content:
                    result_content = event.content

            # Emit task complete event
            yield AgentEvent(
                type=AgentEventType.CREW_TASK_COMPLETE,
                content=result_content,
                metadata={
                    "task_id": task.id,
                    "assigned_role": task.assigned_role,
                }
            )

            # Finish performance tracking (success)
            if self.performance_monitor:
                self.performance_monitor.finish_task(task.id, success=True)

        except Exception as e:
            # Emit task error event
            yield AgentEvent(
                type=AgentEventType.CREW_TASK_ERROR,
                error=e,
                metadata={
                    "task_id": task.id,
                    "assigned_role": task.assigned_role,
                    "error_message": str(e),
                }
            )

            # Finish performance tracking (failure)
            if self.performance_monitor:
                self.performance_monitor.finish_task(
                    task.id, success=False, error=str(e)
                )
            raise

    async def execute_task(
        self,
        task: Task,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Execute a single task (non-streaming convenience method).

        This method internally calls execute_task_stream() and collects
        the final result. For real-time progress updates, use
        execute_task_stream() directly.

        Args:
            task: Task to execute
            context: Optional execution context

        Returns:
            str: Task result

        Raises:
            ValueError: If assigned role not found
        """
        result_content = ""

        async for event in self.execute_task_stream(task, context):
            # Collect final result
            if event.type == AgentEventType.CREW_TASK_COMPLETE and event.content:
                result_content = event.content

        return result_content

    async def kickoff_stream(
        self,
        plan: OrchestrationPlan,
    ) -> AsyncGenerator[AgentEvent, None]:
        """
        Start crew execution with streaming events (Core Implementation).

        This is the core streaming implementation for crew orchestration.
        All crew execution flows through this method.

        Args:
            plan: Orchestration plan with tasks

        Yields:
            AgentEvent: Streaming execution events including:
                - CREW_START: Crew execution started
                - CREW_TASK_START: Each task starting
                - All task execution events (forwarded from execute_task_stream)
                - CREW_TASK_COMPLETE: Each task completing
                - CREW_COMPLETE: Crew execution completed
                - CREW_ERROR: Crew execution failed

        Example:
            ```python
            plan = OrchestrationPlan(tasks=[task1, task2], mode=OrchestrationMode.SEQUENTIAL)

            async for event in crew.kickoff_stream(plan):
                if event.type == AgentEventType.CREW_START:
                    print("Crew started")
                elif event.type == AgentEventType.CREW_TASK_START:
                    print(f"Task {event.metadata['task_id']} starting")
                elif event.type == AgentEventType.LLM_DELTA:
                    print(event.content, end="", flush=True)
                elif event.type == AgentEventType.CREW_COMPLETE:
                    print("\\nCrew completed")
            ```
        """
        # Start orchestration tracking
        if self.performance_monitor:
            orch_id = self.performance_monitor.start_orchestration()

        import time
        start_time = time.time()

        # Emit crew start event
        yield AgentEvent(
            type=AgentEventType.CREW_START,
            metadata={
                "plan_mode": plan.mode.value,
                "total_tasks": len(plan.tasks),
                "task_ids": [t.id for t in plan.tasks],
            }
        )

        try:
            # Execute orchestration plan with streaming
            results: Dict[str, Any] = {}

            # Delegate to orchestrator's execute method, but forward events
            # For now, we implement sequential mode inline for streaming support
            if plan.mode == OrchestrationMode.SEQUENTIAL:
                # Topological sort for dependency order
                sorted_tasks = self.orchestrator._topological_sort(plan.tasks)

                for task in sorted_tasks:
                    # Check condition
                    if not task.should_execute(plan.shared_context):
                        continue

                    # Build task context with dependency results
                    task_context = self.orchestrator._build_task_context(
                        task, results, plan.shared_context
                    )

                    # Stream task execution
                    task_result = ""
                    async for event in self.execute_task_stream(task, context=task_context):
                        # Forward all task events
                        yield event

                        # Collect task result
                        if event.type == AgentEventType.CREW_TASK_COMPLETE and event.content:
                            task_result = event.content

                    # Store result
                    results[task.id] = task_result

                    # Update shared context
                    if task.output_key:
                        plan.shared_context[task.output_key] = task_result

            else:
                # For other modes, use non-streaming orchestrator
                # (can be enhanced later for full streaming support)
                results = await self.orchestrator.execute(plan, self)

            # Emit crew complete event
            yield AgentEvent(
                type=AgentEventType.CREW_COMPLETE,
                metadata={
                    "results": results,
                    "total_tasks": len(plan.tasks),
                    "completed_tasks": len(results),
                }
            )

            # Finish orchestration tracking
            if self.performance_monitor:
                duration = time.time() - start_time
                self.performance_monitor.finish_orchestration(duration)

        except Exception as e:
            # Emit crew error event
            yield AgentEvent(
                type=AgentEventType.CREW_ERROR,
                error=e,
                metadata={
                    "error_message": str(e),
                }
            )

            # Record orchestration failure
            if self.performance_monitor:
                duration = time.time() - start_time
                self.performance_monitor.finish_orchestration(duration)
            raise

    async def kickoff(
        self,
        plan: OrchestrationPlan,
    ) -> Dict[str, Any]:
        """
        Start crew execution (non-streaming convenience method).

        This method internally calls kickoff_stream() and collects
        the results. For real-time progress updates, use kickoff_stream() directly.

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
        results: Dict[str, Any] = {}

        async for event in self.kickoff_stream(plan):
            # Collect results from CREW_COMPLETE event
            if event.type == AgentEventType.CREW_COMPLETE and event.metadata.get("results"):
                results = event.metadata["results"]

        return results

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
