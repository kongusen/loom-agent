"""Blueprint store — in-memory storage with optional file persistence."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

from ..types.blueprint import AgentBlueprint

logger = logging.getLogger(__name__)


class BlueprintStore:
    """Stores and retrieves agent blueprints."""

    def __init__(self, persist_path: Path | None = None) -> None:
        self._blueprints: dict[str, AgentBlueprint] = {}
        self._persist_path = persist_path
        if persist_path and persist_path.exists():
            self._load_from_disk()

    def save(self, bp: AgentBlueprint) -> None:
        bp.updated_at = time.time()
        self._blueprints[bp.id] = bp
        self._persist()

    def get(self, bp_id: str) -> AgentBlueprint | None:
        return self._blueprints.get(bp_id)

    def list_all(self) -> list[AgentBlueprint]:
        return list(self._blueprints.values())

    def list_descriptions(self) -> list[dict[str, str]]:
        return [
            {"name": bp.name, "description": bp.description, "domain": bp.domain}
            for bp in self._blueprints.values()
        ]

    def find_by_domain(self, domain: str) -> list[AgentBlueprint]:
        return [bp for bp in self._blueprints.values() if bp.domain == domain]

    def prune(self, min_reward: float = 0.2, min_tasks: int = 3) -> list[str]:
        """Remove blueprints with poor performance. Returns pruned IDs."""
        pruned: list[str] = []
        for bp_id, bp in list(self._blueprints.items()):
            if bp.total_tasks >= min_tasks and bp.avg_reward < min_reward:
                del self._blueprints[bp_id]
                pruned.append(bp_id)
                logger.info("Pruned blueprint %s (%s) avg_reward=%.2f", bp_id[:8], bp.name, bp.avg_reward)
        if pruned:
            self._persist()
        return pruned

    def count(self) -> int:
        return len(self._blueprints)

    # ── Persistence ──

    def _persist(self) -> None:
        if not self._persist_path:
            return
        try:
            self._persist_path.parent.mkdir(parents=True, exist_ok=True)
            data = [self._bp_to_dict(bp) for bp in self._blueprints.values()]
            self._persist_path.write_text(json.dumps(data, indent=2))
        except OSError as e:
            logger.warning("Failed to persist blueprints: %s", e)

    def _load_from_disk(self) -> None:
        try:
            data = json.loads(self._persist_path.read_text())  # type: ignore[union-attr]
            for item in data:
                bp = self._dict_to_bp(item)
                self._blueprints[bp.id] = bp
            logger.info("Loaded %d blueprints from disk", len(self._blueprints))
        except (json.JSONDecodeError, OSError, KeyError) as e:
            logger.warning("Failed to load blueprints: %s", e)

    @staticmethod
    def _bp_to_dict(bp: AgentBlueprint) -> dict:
        return {
            "id": bp.id, "name": bp.name, "description": bp.description,
            "system_prompt": bp.system_prompt, "domain": bp.domain,
            "domain_scores": bp.domain_scores, "tools_filter": bp.tools_filter,
            "created_at": bp.created_at, "updated_at": bp.updated_at,
            "generation": bp.generation, "parent_id": bp.parent_id,
            "total_spawns": bp.total_spawns, "total_tasks": bp.total_tasks,
            "avg_reward": bp.avg_reward, "reward_history": bp.reward_history,
        }

    @staticmethod
    def _dict_to_bp(d: dict) -> AgentBlueprint:
        return AgentBlueprint(
            id=d["id"], name=d["name"], description=d["description"],
            system_prompt=d["system_prompt"], domain=d.get("domain", "general"),
            domain_scores=d.get("domain_scores", {}),
            tools_filter=d.get("tools_filter", []),
            created_at=d.get("created_at", 0), updated_at=d.get("updated_at", 0),
            generation=d.get("generation", 1), parent_id=d.get("parent_id"),
            total_spawns=d.get("total_spawns", 0),
            total_tasks=d.get("total_tasks", 0),
            avg_reward=d.get("avg_reward", 0.0),
            reward_history=d.get("reward_history", []),
        )
