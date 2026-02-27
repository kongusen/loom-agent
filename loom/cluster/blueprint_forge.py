"""Blueprint Forge — LLM-driven agent blueprint design and evolution."""

from __future__ import annotations

import json
import logging
import re
import time
from typing import TYPE_CHECKING

from ..types.blueprint import AgentBlueprint
from ..types import (
    AgentNode,
    CapabilityProfile,
    CompletionParams,
    TaskAd,
    UserMessage,
)

if TYPE_CHECKING:
    from ..types import LLMProvider
    from .blueprint_store import BlueprintStore

logger = logging.getLogger(__name__)


class BlueprintForge:
    """Designs, spawns, and evolves agent blueprints via LLM."""

    def __init__(
        self,
        llm: LLMProvider,
        store: BlueprintStore,
        evolve_threshold: float = 0.35,
        evolve_window: int = 5,
        max_blueprints: int = 50,
    ) -> None:
        self._llm = llm
        self.store = store
        self.evolve_threshold = evolve_threshold
        self.evolve_window = evolve_window
        self._max_blueprints = max_blueprints

    # ── Forge: LLM designs a new blueprint ──

    async def forge(self, task: TaskAd, context: str = "") -> AgentBlueprint:
        """Ask LLM to design a specialized agent blueprint for the task."""
        existing = self.store.list_descriptions()
        prompt = self._build_forge_prompt(task, existing, context)
        try:
            result = await self._llm.complete(
                CompletionParams(
                    messages=[UserMessage(content=prompt)],
                    temperature=0.4,
                    max_tokens=512,
                )
            )
            bp = self._parse_blueprint(result.content, task)
        except Exception as e:
            logger.warning("Forge LLM call failed, using fallback: %s", e)
            bp = self._fallback_blueprint(task)
        self.store.save(bp)
        logger.info("Forged blueprint %s (%s) for domain=%s", bp.id[:8], bp.name, bp.domain)
        return bp

    # ── Spawn: create an AgentNode from a blueprint ──

    def spawn(self, blueprint: AgentBlueprint, parent: AgentNode) -> AgentNode:
        """Instantiate an agent from a blueprint and return an AgentNode."""
        from ..agent import Agent
        from ..config import AgentConfig

        config = AgentConfig(system_prompt=blueprint.system_prompt)
        agent = Agent(
            provider=self._llm,
            config=config,
            name=f"forged:{blueprint.name}",
        )
        node = AgentNode(
            id=f"forged:{blueprint.id[:8]}",
            blueprint_id=blueprint.id,
            depth=parent.depth + 1,
            capabilities=CapabilityProfile(
                scores=dict(blueprint.domain_scores),
                tools=blueprint.tools_filter or list(parent.capabilities.tools),
            ),
            agent=agent,
        )
        blueprint.total_spawns += 1
        self.store.save(blueprint)
        return node

    # ── Evolve: improve a blueprint based on reward signals ──

    async def evolve(self, blueprint: AgentBlueprint) -> AgentBlueprint:
        """Create an improved generation of the blueprint."""
        prompt = self._build_evolve_prompt(blueprint)
        try:
            result = await self._llm.complete(
                CompletionParams(
                    messages=[UserMessage(content=prompt)],
                    temperature=0.3,
                    max_tokens=512,
                )
            )
            new_bp = self._parse_evolved_blueprint(result.content, blueprint)
        except Exception as e:
            logger.warning("Evolve LLM call failed: %s", e)
            return blueprint
        self.store.save(new_bp)
        logger.info(
            "Evolved blueprint %s → %s (gen %d)",
            blueprint.id[:8], new_bp.id[:8], new_bp.generation,
        )
        return new_bp

    # ── Match: find an existing blueprint for a task ──

    async def match(self, task: TaskAd) -> AgentBlueprint | None:
        """Semantically match a task to an existing blueprint."""
        blueprints = self.store.list_all()
        if not blueprints:
            return None
        bp_list = "\n".join(
            f"- {bp.name} (id={bp.id[:8]}): {bp.description}"
            for bp in blueprints
        )
        try:
            result = await self._llm.complete(
                CompletionParams(
                    messages=[UserMessage(content=(
                        "Given these agent blueprints:\n"
                        f"{bp_list}\n\n"
                        f"Task: {task.description}\n\n"
                        'If one matches well, reply with JSON: {{"id":"<8-char-id>"}}\n'
                        'If none match, reply: {{"id":"none"}}'
                    ))],
                    temperature=0,
                    max_tokens=64,
                )
            )
            m = re.search(r"\{[\s\S]*?\}", result.content)
            if m:
                obj = json.loads(m.group())
                bp_id_prefix = obj.get("id", "none")
                if bp_id_prefix != "none":
                    for bp in blueprints:
                        if bp.id.startswith(bp_id_prefix):
                            return bp
        except Exception:
            pass
        return None

    # ── Private: prompt builders ──

    def _build_forge_prompt(
        self, task: TaskAd, existing: list[dict[str, str]], context: str,
    ) -> str:
        existing_str = "\n".join(
            f"- {e['name']}: {e['description']}" for e in existing
        ) or "(none)"
        return (
            "You are an agent architect. Design a specialized AI agent blueprint "
            "for the task below.\n\n"
            f"Task domain: {task.domain}\n"
            f"Task description: {task.description}\n"
            f"Context: {context or '(none)'}\n\n"
            f"Existing blueprints (avoid duplicating):\n{existing_str}\n\n"
            "Design a NEW agent that fills a gap. Focus on WHY this agent "
            "should exist and what makes it uniquely suited — avoid generic "
            "instructions or stacking MUST rules.\n\n"
            "Reply ONLY with JSON:\n"
            "{\n"
            '  "name": "short-kebab-name",\n'
            '  "description": "one-line trigger description",\n'
            '  "system_prompt": "the agent system prompt (2-4 sentences)",\n'
            '  "domain": "primary-domain",\n'
            '  "domain_scores": {"domain": 0.7},\n'
            '  "tools_filter": []\n'
            "}"
        )

    def _build_evolve_prompt(self, blueprint: AgentBlueprint) -> str:
        recent = blueprint.reward_history[-10:]
        avg = sum(recent) / len(recent) if recent else 0.0
        return (
            "You are improving an underperforming agent blueprint.\n\n"
            f"Name: {blueprint.name}\n"
            f"Domain: {blueprint.domain}\n"
            f"Current description: {blueprint.description}\n"
            f"Current system_prompt: {blueprint.system_prompt}\n"
            f"Recent avg reward: {avg:.2f} (target: >=0.5)\n"
            f"Generation: {blueprint.generation}\n"
            f"Total tasks: {blueprint.total_tasks}\n\n"
            "Analyze why this agent underperforms and propose improvements. "
            "Focus on making the description more precise for routing and "
            "the system_prompt more effective. Explain WHY each change helps.\n\n"
            "Reply ONLY with JSON:\n"
            "{\n"
            '  "description": "improved trigger description",\n'
            '  "system_prompt": "improved system prompt",\n'
            '  "reasoning": "why these changes help"\n'
            "}"
        )

    # ── Private: parsers ──

    def _parse_blueprint(self, raw: str, task: TaskAd) -> AgentBlueprint:
        """Parse LLM JSON output into an AgentBlueprint."""
        m = re.search(r"\{[\s\S]*\}", raw)
        if not m:
            return self._fallback_blueprint(task)
        try:
            obj = json.loads(m.group())
        except json.JSONDecodeError:
            return self._fallback_blueprint(task)
        return AgentBlueprint(
            name=obj.get("name", task.domain),
            description=obj.get("description", task.description),
            system_prompt=obj.get("system_prompt", "You are a helpful assistant."),
            domain=obj.get("domain", task.domain),
            domain_scores=obj.get("domain_scores", {task.domain: 0.6}),
            tools_filter=obj.get("tools_filter", []),
        )

    def _fallback_blueprint(self, task: TaskAd) -> AgentBlueprint:
        """Create a minimal blueprint when LLM parsing fails."""
        return AgentBlueprint(
            name=f"{task.domain}-specialist",
            description=f"Handles {task.domain} tasks",
            system_prompt=f"You are a specialist in {task.domain}. {task.description}",
            domain=task.domain,
            domain_scores={task.domain: 0.5},
        )

    def _parse_evolved_blueprint(self, raw: str, parent: AgentBlueprint) -> AgentBlueprint:
        """Parse evolved blueprint from LLM output."""
        m = re.search(r"\{[\s\S]*\}", raw)
        desc = parent.description
        prompt = parent.system_prompt
        if m:
            try:
                obj = json.loads(m.group())
                desc = obj.get("description", desc)
                prompt = obj.get("system_prompt", prompt)
            except json.JSONDecodeError:
                pass
        return AgentBlueprint(
            name=parent.name,
            description=desc,
            system_prompt=prompt,
            domain=parent.domain,
            domain_scores=dict(parent.domain_scores),
            tools_filter=list(parent.tools_filter),
            generation=parent.generation + 1,
            parent_id=parent.id,
        )
