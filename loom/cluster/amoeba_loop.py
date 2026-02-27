"""AmoebaLoop — 6-phase self-organizing LoopStrategy.

SENSE → MATCH → SCALE+EXECUTE → EVALUATE+ADAPT
"""

from __future__ import annotations

import json
import random
import re
import time
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING

from ..errors import AuctionNoWinnerError
from ..types import (
    AgentEvent,
    AgentNode,
    CapabilityProfile,
    CompletionParams,
    ComplexityEstimate,
    DoneEvent,
    ErrorEvent,
    TaskAd,
    TaskResult,
    TaskSpec,
    TextDeltaEvent,
    TokenUsage,
    UserMessage,
)

if TYPE_CHECKING:
    from ..types import LLMProvider
    from . import ClusterManager
    from .blueprint_forge import BlueprintForge
    from .lifecycle import LifecycleManager
    from .planner import TaskPlanner
    from .reward import RewardBus
    from .skill_registry import SkillNodeRegistry

_DOMAIN_KEYWORDS: dict[str, list[str]] = {}  # kept for backward compat; unused by LLM routing


class AmoebaLoop:
    """6-phase LoopStrategy: SENSE → MATCH → SCALE+EXECUTE → EVALUATE+ADAPT."""

    name = "amoeba"

    def __init__(
        self,
        cluster: ClusterManager,
        reward_bus: RewardBus,
        lifecycle: LifecycleManager,
        planner: TaskPlanner,
        skill_registry: SkillNodeRegistry,
        llm: LLMProvider,
        complexity_llm_threshold: int = 200,
        evolution_reward_threshold: float = 0.35,
        evolution_window: int = 5,
        forge: BlueprintForge | None = None,
    ) -> None:
        self._cluster = cluster
        self._reward = reward_bus
        self._lifecycle = lifecycle
        self._planner = planner
        self._skills = skill_registry
        self._llm = llm
        self._complexity_threshold = complexity_llm_threshold
        self._evo_threshold = evolution_reward_threshold
        self._evo_window = evolution_window
        self._calibration: dict[str, dict] = {}  # domain → {bias, count}
        self._forge = forge

    # ── Main execute (LoopStrategy interface) ──

    async def execute(self, ctx) -> AsyncGenerator[AgentEvent, None]:
        start = time.monotonic()
        usage = TokenUsage()
        msgs = ctx.messages
        user_msg = next((m for m in reversed(msgs) if m.role == "user"), None)
        input_text = user_msg.content if user_msg else ""

        # Phase 1+2: SENSE + MATCH (combined LLM semantic selection)
        spec, winner = await self._sense_and_match(input_text)
        yield TextDeltaEvent(
            text=f"complexity={spec.task.estimated_complexity:.2f} domains={','.join(spec.domain_hints)} "
        )

        if not winner:
            yield ErrorEvent(error=str(AuctionNoWinnerError(spec.task.task_id)), recoverable=False)
            yield DoneEvent(
                content="", steps=1, duration_ms=int((time.monotonic() - start) * 1000), usage=usage
            )
            return
        yield TextDeltaEvent(text=f"winner={winner.id} ")

        # Phase 3+4: SCALE + EXECUTE
        result = await self._scale_and_execute(winner, spec, input_text)
        usage.total_tokens += result.token_cost
        yield TextDeltaEvent(text=result.content)

        # Phase 5+6: EVALUATE + ADAPT
        reward, recycled = await self._evaluate_and_adapt(winner, spec, result)
        yield TextDeltaEvent(text=f"\n[Adapt] reward={reward:.2f} recycled={recycled}\n")

        yield DoneEvent(
            content=result.content,
            steps=1,
            duration_ms=int((time.monotonic() - start) * 1000),
            usage=usage,
        )

    # ── Phase 1+2: SENSE + MATCH (LLM semantic selection, à la Claude Code) ──

    async def _sense_and_match(self, input_text: str) -> tuple[TaskSpec, AgentNode | None]:
        skill_descs = self._collect_skill_descriptions()
        complexity, selected_skill, domains = await self._llm_sense_and_match(
            input_text, skill_descs
        )
        calibrated = self._calibrate(
            ComplexityEstimate(score=complexity, domains=domains, method="llm")
        )
        c = calibrated.score
        task = TaskAd(
            domain=selected_skill or "general",
            description=input_text,
            estimated_complexity=c,
            token_budget=2048 if c < 0.4 else 4096 if c < 0.7 else 8192,
        )
        spec = TaskSpec(task=task, objective=input_text, domain_hints=calibrated.domains)
        winner = (
            self._resolve_skill_node(selected_skill)
            if selected_skill
            else self._cluster.find_idle()
        )

        # Blueprint Forge fallback: match or forge when no winner found
        if not winner and self._forge:
            bp = await self._forge.match(task)
            if not bp:
                bp = await self._forge.forge(task, context=input_text)
            fallback_parent = self._cluster.nodes[0] if self._cluster.nodes else None
            if bp and fallback_parent:
                winner = self._forge.spawn(bp, fallback_parent)
                self._cluster.add_node(winner)

        return spec, winner

    def _collect_skill_descriptions(self) -> list[dict[str, str]]:
        """Collect name+description from loaded nodes and unloaded catalog."""
        from_nodes = []
        for node in self._cluster.nodes:
            if node.id.startswith("skill:"):
                name = node.id.removeprefix("skill:")
                skill = self._skills.get(name)
                from_nodes.append(
                    {
                        "name": name,
                        "description": getattr(skill, "description", name) if skill else name,
                    }
                )
        loaded_names = {d["name"] for d in from_nodes}
        from_catalog = [d for d in self._skills.describe_all() if d["name"] not in loaded_names]
        return from_nodes + from_catalog

    async def _llm_sense_and_match(
        self, input_text: str, skills: list[dict[str, str]]
    ) -> tuple[float, str | None, list[str]]:
        """Single LLM call: estimate complexity + select best skill."""
        skill_list = "\n".join(f"- {s['name']}: {s['description']}" for s in skills)
        try:
            r = await self._llm.complete(
                CompletionParams(
                    messages=[
                        UserMessage(
                            content=(
                                "You are a task router. Given available skills and a task, "
                                "select the BEST skill and assess complexity.\n\n"
                                f"Available skills:\n{skill_list}\n\n"
                                'Reply ONLY with JSON: {"skill":"<name>","complexity":0.0-1.0,"domains":["..."]}\n\n'
                                f"Task: {input_text}"
                            )
                        )
                    ],
                    temperature=0,
                    max_tokens=128,
                )
            )
            m = re.search(r"\{[\s\S]*\}", r.content)
            if m:
                obj = json.loads(m.group())
                name = (
                    obj.get("skill", "").strip().lower()
                    if isinstance(obj.get("skill"), str)
                    else None
                )
                matched = next((s["name"] for s in skills if s["name"] == name), None)
                return (
                    max(0.0, min(1.0, obj.get("complexity", 0.5))),
                    matched,
                    obj.get("domains", ["general"]),
                )
        except Exception:
            pass
        return 0.5, skills[0]["name"] if skills else None, ["general"]

    def _resolve_skill_node(self, skill_name: str) -> AgentNode | None:
        """Resolve a skill name to a loaded node, lazy-loading if needed."""
        node_id = f"skill:{skill_name}"
        existing = self._cluster.get_node(node_id)
        if existing and existing.status != "dying":
            return existing
        skill = self._skills.get(skill_name)
        if not skill:
            return None
        from ..agent import Agent

        agent = Agent(provider=self._llm, name=node_id)
        node = AgentNode(
            id=node_id,
            depth=0,
            capabilities=CapabilityProfile(scores={skill_name: 0.7}, tools=[]),
            agent=agent,
        )
        self._cluster.add_node(node)
        self._skills.mark_loaded(skill_name)
        return node

    # ── Phase 3+4: SCALE + EXECUTE ──

    async def _scale_and_execute(
        self, winner: AgentNode, spec: TaskSpec, input_text: str
    ) -> TaskResult:
        winner.status = "busy"
        winner.last_active_at = time.time()
        self._cluster.update_load(winner.id, 0.8)
        try:
            c = spec.task.estimated_complexity
            if c > 0.7 and self._lifecycle.should_split(spec.task, winner):
                return await self._execute_mitosis(winner, spec)
            prompt = self._build_enriched_prompt(spec) if c >= 0.4 else input_text
            t0 = time.monotonic()
            done = await winner.agent.run(prompt)
            return TaskResult(
                task_id=spec.task.task_id,
                agent_id=winner.id,
                content=done.content,
                success=True,
                token_cost=done.usage.total_tokens,
                duration_ms=int((time.monotonic() - t0) * 1000),
            )
        except Exception:
            return TaskResult(
                task_id=spec.task.task_id,
                agent_id=winner.id,
                content="",
                success=False,
                error_count=1,
            )
        finally:
            winner.status = "idle"
            self._cluster.update_load(winner.id, 0)

    async def _execute_mitosis(self, parent: AgentNode, spec: TaskSpec) -> TaskResult:
        subtasks = await self._planner.decompose(spec.task)
        results = await self._planner.execute_dag(
            subtasks[:4],
            lambda st: self._run_subtask(parent, spec, st),
        )
        content = await self._planner.aggregate(spec.task, results)
        return TaskResult(
            task_id=spec.task.task_id,
            agent_id=parent.id,
            content=content,
            success=True,
            token_cost=0,
            duration_ms=0,
        )

    async def _run_subtask(self, parent: AgentNode, spec: TaskSpec, st) -> str:
        sub_ad = TaskAd(
            domain=st.domain or spec.task.domain,
            description=st.description,
            estimated_complexity=st.estimated_complexity,
        )
        winner = self._cluster.select_winner(sub_ad)
        if not winner and self._forge:
            bp = await self._forge.match(sub_ad)
            if not bp:
                bp = await self._forge.forge(sub_ad, context=spec.objective)
            child = self._forge.spawn(bp, parent)
            self._cluster.add_node(child)
            winner = child
        elif not winner:
            from ..agent import Agent

            child = self._lifecycle.mitosis(
                parent,
                sub_ad,
                agent_factory=lambda _depth: Agent(provider=self._llm, name=f"child:{parent.id}"),
            )
            self._cluster.add_node(child)
            winner = child
        return str((await winner.agent.run(st.description)).content)

    def _build_enriched_prompt(self, spec: TaskSpec) -> str:
        p = f"Objective: {spec.objective}"
        if spec.output_format:
            p += f"\nOutput format: {spec.output_format}"
        if spec.boundaries:
            p += f"\nConstraints: {spec.boundaries}"
        if spec.tool_guidance:
            p += f"\nTool guidance: {spec.tool_guidance}"
        return p

    # ── Phase 5+6: EVALUATE + ADAPT ──

    async def _evaluate_and_adapt(
        self,
        winner: AgentNode,
        spec: TaskSpec,
        result: TaskResult,
    ) -> tuple[float, bool]:
        # EVALUATE
        reward = self._reward.evaluate(
            winner,
            spec.task,
            result.success,
            result.token_cost,
            result.error_count,
        )

        # ADAPT: consecutive losses
        if reward < 0.5:
            winner.consecutive_losses += 1
        else:
            winner.consecutive_losses = 0

        # ADAPT: health check → apoptosis
        recycled = False
        health = self._lifecycle.check_health(winner)
        if health.recommendation == "recycle":
            try:
                self._lifecycle.apoptosis(winner, self._cluster)
                recycled = True
            except Exception:
                pass

        # ADAPT: skill evolution (matches Amoba)
        if not recycled and self._should_evolve_skill(winner):
            await self._trigger_skill_evolution(winner, spec)

        # ADAPT: complexity calibration
        actual = self._derive_actual_complexity(result)
        self._record_calibration(spec.task.domain, spec.task.estimated_complexity, actual)

        # ADAPT: decay inactive
        self._reward.decay_inactive(winner)

        # ADAPT: blueprint reward propagation + evolution
        if self._forge and winner.blueprint_id:
            bp = self._forge.store.get(winner.blueprint_id)
            if bp:
                bp.total_tasks += 1
                bp.reward_history.append(reward)
                recent = bp.reward_history[-20:]
                bp.avg_reward = sum(recent) / len(recent)
                self._forge.store.save(bp)
                # Trigger evolution if underperforming
                if (
                    len(bp.reward_history) >= self._forge.evolve_window
                    and bp.avg_reward < self._forge.evolve_threshold
                ):
                    await self._forge.evolve(bp)

        # ADAPT: blueprint pruning (10% chance per cycle)
        if self._forge and random.random() < 0.1:
            config = self._cluster.config
            self._forge.store.prune(
                min_reward=getattr(config, "blueprint_prune_min_reward", 0.2),
                min_tasks=getattr(config, "blueprint_prune_min_tasks", 3),
            )

        return reward, recycled

    # ── Helpers: calibration ──

    def _derive_actual_complexity(self, result: TaskResult) -> float:
        token_ratio = min(result.token_cost / 8192, 1.0)
        duration_ratio = min(result.duration_ms / 30000, 1.0)
        return token_ratio * 0.6 + duration_ratio * 0.4

    def _record_calibration(self, domain: str, estimated: float, actual: float) -> None:
        entry = self._calibration.get(domain, {"bias": 0.0, "count": 0})
        entry["bias"] = 0.3 * (actual - estimated) + 0.7 * entry["bias"]
        entry["count"] += 1
        self._calibration[domain] = entry

    def _should_evolve_skill(self, node: AgentNode) -> bool:
        """Check if node's recent performance warrants skill evolution."""
        recent = node.reward_history[-self._evo_window :]
        if len(recent) < self._evo_window:
            return False
        avg = sum(r.reward for r in recent) / len(recent)
        return avg < self._evo_threshold

    async def _trigger_skill_evolution(self, node: AgentNode, spec: TaskSpec) -> None:
        """Use LLM to suggest skill improvements for underperforming node."""
        try:
            r = await self._llm.complete(
                CompletionParams(
                    messages=[
                        UserMessage(
                            content=(
                                f"Agent {node.id} is underperforming on domain '{spec.task.domain}'. "
                                f"Capabilities: {node.capabilities.scores}. "
                                f"Suggest a focused skill improvement as JSON: "
                                f'{{"domain":"...","boost":0.0-0.3,"reasoning":"..."}}'
                            )
                        )
                    ],
                    temperature=0.3,
                    max_tokens=128,
                )
            )
            import re as _re

            m = _re.search(r"\{[\s\S]*\}", r.content)
            if m:
                obj = json.loads(m.group())
                domain = obj.get("domain", spec.task.domain)
                boost = min(0.3, max(0.0, obj.get("boost", 0.1)))
                current = node.capabilities.scores.get(domain, 0.5)
                node.capabilities.scores[domain] = min(1.0, current + boost)
        except Exception:
            pass

    def _calibrate(self, estimate: ComplexityEstimate) -> ComplexityEstimate:
        domain = estimate.domains[0] if estimate.domains else "general"
        entry = self._calibration.get(domain)
        if not entry or entry["count"] < 3:
            return estimate
        return ComplexityEstimate(
            score=max(0.0, min(1.0, estimate.score + entry["bias"])),
            domains=estimate.domains,
            reasoning=estimate.reasoning,
            method=estimate.method,
        )
