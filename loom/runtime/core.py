"""Runtime — optional standalone runtime for cluster orchestration."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from ..agent import Agent
from ..cluster import ClusterManager
from ..cluster.lifecycle import LifecycleManager

if TYPE_CHECKING:
    from ..cluster.amoeba_loop import AmoebaLoop

from ..cluster.planner import TaskPlanner
from ..cluster.reward import RewardBus
from ..cluster.skill_registry import SkillNodeRegistry
from ..config import AgentConfig, ClusterConfig
from ..context import ContextOrchestrator, MemoryContextProvider
from ..memory import MemoryManager
from ..tools import ToolRegistry
from ..tools.builtin import delegate_tool, done_tool
from ..types import AgentNode, CapabilityProfile, DoneEvent, LLMProvider, Skill, SubTask, TaskAd

logger = logging.getLogger(__name__)


class Runtime:
    """Standalone runtime: create cluster, route tasks, manage lifecycle."""

    def __init__(
        self,
        provider: LLMProvider,
        config: AgentConfig | None = None,
        cluster_config: ClusterConfig | None = None,
    ) -> None:
        self._provider = provider
        self._agent_config = config or AgentConfig()
        self.cluster = ClusterManager(cluster_config)
        self.reward_bus = RewardBus()
        self.lifecycle = LifecycleManager(self.cluster.config)
        self._planner = TaskPlanner(provider)
        self._skill_registry = SkillNodeRegistry()
        self._memory = MemoryManager()
        self._health_timer = None

    def add_agent(
        self,
        agent: Agent | None = None,
        tools: ToolRegistry | None = None,
        capabilities: CapabilityProfile | None = None,
        depth: int = 0,
    ) -> AgentNode:
        if agent is None:
            agent = self._create_agent(tools)
        agent.on_delegate = self._handle_delegate
        node = AgentNode(
            id=agent.id,
            depth=depth,
            capabilities=capabilities
            or CapabilityProfile(tools=[t.name for t in agent.tools.list()]),
            agent=agent,
        )
        self.cluster.add_node(node)
        return node

    def _create_agent(self, tools: ToolRegistry | None = None) -> Agent:
        reg = tools or ToolRegistry()
        reg.register(done_tool)
        reg.register(delegate_tool)
        return Agent(provider=self._provider, config=self._agent_config, tools=reg)

    async def submit(self, task: TaskAd) -> str:
        winner = self.cluster.select_winner(task)
        if not winner:
            return "Error: no available agents"
        if self.lifecycle.should_split(task, winner):
            return await self._execute_split(winner, task)
        return await self._execute_single(winner, task)

    async def _execute_single(self, node: AgentNode, task: TaskAd) -> str:
        node.status = "busy"
        node.last_active_at = time.time()
        try:
            result: DoneEvent = await node.agent.run(task.description)
            success = not result.content.startswith("Error:")
            self.reward_bus.evaluate(node, task, success, token_cost=result.usage.total_tokens)
            return result.content
        except Exception as e:
            self.reward_bus.evaluate(node, task, False, error_count=1)
            return f"Error: {e}"
        finally:
            node.status = "idle"
            node.last_active_at = time.time()
            self._check_health()

    async def _execute_split(self, parent: AgentNode, task: TaskAd) -> str:
        parent.status = "splitting"
        parent_mem = parent.agent.memory
        seed = await parent_mem.extract_for(task.description, budget=2000)
        subtasks = await self._planner.decompose(task)

        async def run_subtask(st: SubTask) -> str:
            sub_ad = TaskAd(
                domain=st.domain or task.domain,
                description=st.description,
                estimated_complexity=st.estimated_complexity,
                token_budget=task.token_budget,
            )
            winner = self.cluster.select_winner(sub_ad)
            if not winner:
                child = self.add_agent(depth=parent.depth + 1)
                winner = child
            await winner.agent.memory.absorb(seed)
            result = await self._execute_single(winner, sub_ad)
            child_entries = await winner.agent.memory.get_l2_context(st.description)
            await parent_mem.absorb(child_entries, boost=0.1)
            return result

        results = await self._planner.execute_dag(subtasks, run_subtask)
        parent.status = "idle"
        return await self._planner.aggregate(task, results)

    async def _handle_delegate(self, task_desc: str, domain: str) -> str:
        task = TaskAd(domain=domain, description=task_desc)
        return await self.submit(task)

    def _check_health(self) -> None:
        for node in self.cluster.nodes:
            self.reward_bus.decay_inactive(node)
        dying = [n for n in self.cluster.nodes if self.lifecycle.check_health(n).status == "dying"]
        for node in dying:
            try:
                self.lifecycle.apoptosis(node, self.cluster)
                logger.info("Apoptosis: removed agent %s", node.id)
            except Exception:
                pass

    def load_skill(self, skill: Skill) -> AgentNode:
        """Load a skill as a cluster node."""
        self._skill_registry.register(skill)
        agent = Agent(provider=self._provider, name=f"skill:{skill.name}")
        caps = CapabilityProfile(
            scores={skill.name: 0.7},
            tools=[t.name for t in getattr(skill, "tools", [])],
        )
        node = self.add_agent(agent=agent, capabilities=caps)
        self._skill_registry.mark_loaded(skill.name)
        return node

    async def discover_skill(self, input_text: str) -> AgentNode | None:
        """Match input to a skill and load it if found."""
        match = await self._skill_registry.find_match(input_text)
        if not match:
            return None
        return self.load_skill(match["skill"])

    def build_context_for(self, agent_id: str) -> ContextOrchestrator:
        """Create a ContextOrchestrator wired to the agent's memory."""
        orch = ContextOrchestrator()
        node = self.cluster.get_node(agent_id)
        if node and node.agent and hasattr(node.agent, "memory"):
            orch.register(MemoryContextProvider(node.agent.memory))
        return orch

    def get_memory(self) -> MemoryManager:
        return self._memory

    def create_node(
        self,
        tools: ToolRegistry | None = None,
        capabilities: CapabilityProfile | None = None,
        depth: int = 0,
    ) -> AgentNode:
        """Factory: create and register a new agent node."""
        return self.add_agent(tools=tools, capabilities=capabilities, depth=depth)

    def amoeba_loop(self) -> AmoebaLoop:
        """Factory: create an AmoebaLoop wired to this runtime's components."""
        from ..cluster.amoeba_loop import AmoebaLoop

        return AmoebaLoop(
            cluster=self.cluster,
            reward_bus=self.reward_bus,
            lifecycle=self.lifecycle,
            planner=self._planner,
            skill_registry=self._skill_registry,
            llm=self._provider,
        )

    def health_check(self) -> list:
        """Run health check on all nodes, return list of HealthReports."""
        return [self.lifecycle.check_health(n) for n in self.cluster.nodes]

    def dispose(self) -> None:
        """Clean up timers and resources."""
        self._health_timer = None
