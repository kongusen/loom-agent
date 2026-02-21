"""AmoebaLoop — 6-phase self-organizing LoopStrategy.

SENSE → MATCH → SCALE+EXECUTE → EVALUATE+ADAPT
"""

from __future__ import annotations

import json
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
    from .lifecycle import LifecycleManager
    from .planner import TaskPlanner
    from .reward import RewardBus
    from .skill_registry import SkillNodeRegistry

_DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "code": ["code", "function", "bug", "api", "implement", "refactor"],
    "data": ["data", "database", "query", "sql", "schema"],
    "writing": ["write", "draft", "essay", "article", "document"],
    "math": ["calculate", "equation", "formula", "math", "statistics"],
    "research": ["research", "analyze", "compare", "evaluate", "study"],
}


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

    # ── Main execute (LoopStrategy interface) ──

    async def execute(self, ctx) -> AsyncGenerator[AgentEvent, None]:
        start = time.monotonic()
        usage = TokenUsage()
        msgs = ctx.messages
        user_msg = next((m for m in reversed(msgs) if m.role == "user"), None)
        input_text = user_msg.content if user_msg else ""

        # Phase 1: SENSE
        spec = await self._sense(input_text)
        yield TextDeltaEvent(
            text=f"[Sense] complexity={spec.task.estimated_complexity:.2f} domains={spec.domain_hints}\n"
        )

        # Phase 2: MATCH
        winner, tier = await self._match(spec, input_text)
        if not winner:
            yield ErrorEvent(error=str(AuctionNoWinnerError(spec.task.task_id)), recoverable=False)
            yield DoneEvent(
                content="", steps=1, duration_ms=int((time.monotonic() - start) * 1000), usage=usage
            )
            return
        yield TextDeltaEvent(text=f"[Match] winner={winner.id} tier={tier}\n")

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

    # ── Phase 1: SENSE ──

    async def _sense(self, input_text: str) -> TaskSpec:
        estimate = (
            self._heuristic_complexity(input_text)
            if len(input_text) < self._complexity_threshold
            else await self._llm_complexity(input_text)
        )
        calibrated = self._calibrate(estimate)
        c = calibrated.score
        task = TaskAd(
            domain=calibrated.domains[0] if calibrated.domains else "general",
            description=input_text,
            estimated_complexity=c,
            token_budget=2048 if c < 0.4 else 4096 if c < 0.7 else 8192,
        )
        return TaskSpec(task=task, objective=input_text, domain_hints=calibrated.domains)

    def _heuristic_complexity(self, text: str) -> ComplexityEstimate:
        words = len(text.split())
        sentences = len(re.findall(r"[.!?。！？]", text))
        has_list = bool(re.search(r"\d+[.)]|[-*•]", text))
        domains = self._detect_domains(text)
        score = min(words / 200, 0.5)
        if sentences > 2:
            score += 0.15
        if has_list:
            score += 0.1
        if len(domains) > 2:
            score += 0.15
        return ComplexityEstimate(score=min(score, 1.0), domains=domains, method="heuristic")

    async def _llm_complexity(self, text: str) -> ComplexityEstimate:
        try:
            r = await self._llm.complete(
                CompletionParams(
                    messages=[
                        UserMessage(
                            content=f'Assess this task. Reply ONLY with JSON: {{"score":0.0-1.0,"domains":["..."],"reasoning":"..."}}\n\nTask: {text}'
                        )
                    ],
                    temperature=0,
                    max_tokens=128,
                )
            )
            m = re.search(r"\{[\s\S]*\}", r.content)
            if m:
                obj = json.loads(m.group())
                return ComplexityEstimate(
                    score=max(0.0, min(1.0, obj.get("score", 0.5))),
                    domains=obj.get("domains", ["general"]),
                    reasoning=obj.get("reasoning"),
                    method="llm",
                )
        except Exception:
            pass
        return self._heuristic_complexity(text)

    def _detect_domains(self, text: str) -> list[str]:
        lower = text.lower()
        found = [d for d, kws in _DOMAIN_KEYWORDS.items() if any(k in lower for k in kws)]
        return found or ["general"]

    # ── Phase 2: MATCH (3-tier) ──

    async def _match(self, spec: TaskSpec, input_text: str) -> tuple[AgentNode | None, int]:
        # Tier 1: auction across loaded nodes
        winner = self._cluster.select_winner(spec.task)
        if winner:
            return winner, 1
        # Tier 2: scan unloaded skill catalog
        skill_match = await self._skills.find_match(input_text)
        if skill_match:
            node = self._skill_to_node(skill_match["skill"])
            return node, 2
        # Tier 3: LLM-based skill evolution (matches Amoba)
        evolved = await self._evolve_skill_for(spec)
        if evolved:
            return evolved, 3
        # Fallback: any idle node
        idle = self._cluster.find_idle()
        if idle:
            return idle, 4
        return None, 0

    def _skill_to_node(self, skill) -> AgentNode:
        from ..agent import Agent

        agent = Agent(
            provider=self._llm,
            name=f"skill:{skill.name}",
        )
        scores = {skill.name: 0.7}
        trigger = getattr(skill, "trigger", None)
        if trigger and getattr(trigger, "type", "") == "keyword":
            for kw in getattr(trigger, "keywords", []):
                scores[kw] = 0.6
        node = AgentNode(
            id=f"skill:{skill.name}",
            depth=0,
            capabilities=CapabilityProfile(
                scores=scores, tools=[t.name for t in getattr(skill, "tools", [])]
            ),
            agent=agent,
        )
        self._cluster.add_node(node)
        self._skills.mark_loaded(skill.name)
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
        if not winner:
            # Use lifecycle.mitosis() to create child node
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

    async def _evolve_skill_for(self, spec: TaskSpec) -> AgentNode | None:
        """Tier 3: LLM-based skill evolution — create a new specialized node."""
        try:
            from ..agent import Agent

            agent = Agent(provider=self._llm, name=f"evolved:{spec.task.domain}")
            node = AgentNode(
                id=agent.id,
                depth=0,
                capabilities=CapabilityProfile(
                    scores={spec.task.domain: 0.6},
                    tools=[],
                ),
                agent=agent,
            )
            self._cluster.add_node(node)
            return node
        except Exception:
            return None

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
