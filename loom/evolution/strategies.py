"""Evolution strategies - E1, E2, E3, E4"""

from __future__ import annotations

from abc import ABC, abstractmethod
from copy import deepcopy


class EvolutionStrategy(ABC):
    """Base evolution strategy."""

    @abstractmethod
    def apply(self, agent):
        """Apply one evolution step to the agent."""

    def _feedback_entries(self, agent) -> list[dict]:
        """Read feedback from the most common agent shapes in this repo."""
        feedback_loop = getattr(agent, "feedback_loop", None)
        if feedback_loop is not None and hasattr(feedback_loop, "get_feedback"):
            feedback = feedback_loop.get_feedback()
            if isinstance(feedback, list):
                return [item for item in feedback if isinstance(item, dict)]

        direct_feedback = getattr(agent, "feedback", None)
        if isinstance(direct_feedback, list):
            return [item for item in direct_feedback if isinstance(item, dict)]

        getter = getattr(agent, "get_feedback", None)
        if callable(getter):
            feedback = getter()
            if isinstance(feedback, list):
                return [item for item in feedback if isinstance(item, dict)]

        return []

    def _update_state(self, agent, key: str, value: dict) -> dict:
        """Write evolution output back onto the agent in a consistent place."""
        state = getattr(agent, "evolution_state", None)
        if not isinstance(state, dict):
            state = {}
        state[key] = value
        setattr(agent, "evolution_state", state)
        setattr(agent, key, value)
        return value


class ToolLearningStrategy(EvolutionStrategy):
    """E1: Learn which tools are reliable from execution feedback."""

    def __init__(self, success_threshold: float = 0.6, min_examples: int = 1):
        self.success_threshold = success_threshold
        self.min_examples = min_examples

    def apply(self, agent):
        feedback = self._feedback_entries(agent)
        per_tool: dict[str, dict[str, float | int | str | None]] = {}

        for item in feedback:
            tool_name = item.get("tool") or item.get("tool_name") or item.get("name")
            if not tool_name:
                continue

            stats = per_tool.setdefault(
                str(tool_name),
                {
                    "calls": 0,
                    "successes": 0,
                    "failures": 0,
                    "score_total": 0.0,
                    "score_count": 0,
                    "last_outcome": None,
                },
            )
            stats["calls"] += 1

            score = self._score(item)
            if score is not None:
                stats["score_total"] += score
                stats["score_count"] += 1

            success = self._is_success(item, score)
            if success:
                stats["successes"] += 1
                stats["last_outcome"] = "success"
            else:
                stats["failures"] += 1
                stats["last_outcome"] = "failure"

        tool_stats: dict[str, dict[str, float | int | str | None]] = {}
        for tool_name, raw in per_tool.items():
            calls = int(raw["calls"])
            successes = int(raw["successes"])
            failures = int(raw["failures"])
            score_count = int(raw["score_count"])
            avg_score = raw["score_total"] / score_count if score_count else None
            success_rate = successes / calls if calls else 0.0
            tool_stats[tool_name] = {
                "calls": calls,
                "successes": successes,
                "failures": failures,
                "success_rate": success_rate,
                "avg_score": avg_score,
                "last_outcome": raw["last_outcome"],
            }

        preferred_tools = [
            tool_name
            for tool_name, stats in sorted(
                tool_stats.items(),
                key=lambda item: (
                    item[1]["success_rate"],
                    item[1]["avg_score"] if item[1]["avg_score"] is not None else -1.0,
                    item[1]["calls"],
                ),
                reverse=True,
            )
            if stats["calls"] >= self.min_examples and stats["success_rate"] >= self.success_threshold
        ]
        discouraged_tools = [
            tool_name
            for tool_name, stats in tool_stats.items()
            if stats["calls"] >= self.min_examples and stats["failures"] > stats["successes"]
        ]

        learned = {
            "preferred_tools": preferred_tools,
            "discouraged_tools": sorted(discouraged_tools),
            "tool_stats": tool_stats,
            "feedback_count": len(feedback),
        }
        return self._update_state(agent, "tool_learning", learned)

    def _score(self, item: dict) -> float | None:
        score = item.get("score")
        if isinstance(score, (int, float)):
            return float(score)
        return None

    def _is_success(self, item: dict, score: float | None) -> bool:
        if "success" in item:
            return bool(item["success"])
        if item.get("is_error") is True:
            return False

        event_type = str(item.get("type", "")).lower()
        if event_type in {"success", "completed"}:
            return True
        if event_type in {"failure", "error", "blocked_by_policy", "permission_denied", "veto"}:
            return False

        if score is not None:
            return score >= 0.5
        return True


class PolicyOptimizationStrategy(EvolutionStrategy):
    """E2: Turn policy-related feedback into concrete recommendations."""

    def __init__(self, min_block_events: int = 1, risk_threshold: int = 1):
        self.min_block_events = min_block_events
        self.risk_threshold = risk_threshold

    def apply(self, agent):
        feedback = self._feedback_entries(agent)
        baseline = self._baseline_policy(agent)
        per_tool: dict[str, dict[str, int]] = {}

        for item in feedback:
            tool_name = item.get("tool") or item.get("tool_name") or item.get("name")
            if not tool_name:
                continue

            stats = per_tool.setdefault(
                str(tool_name),
                {"blocked": 0, "approvals": 0, "risky": 0, "successes": 0, "failures": 0},
            )
            event_type = str(item.get("type", "")).lower()
            success = item.get("success")

            if event_type in {"blocked_by_policy", "permission_denied", "veto"}:
                stats["blocked"] += 1
            if event_type in {"policy_override", "approval_required", "approved"}:
                stats["approvals"] += 1
            if item.get("risk") in {"high", "critical"} or item.get("severity") in {"high", "critical"}:
                stats["risky"] += 1
            if success is True or event_type in {"success", "completed"}:
                stats["successes"] += 1
            if success is False or event_type in {"failure", "error"}:
                stats["failures"] += 1

        recommend_deny = set(baseline["deny"])
        recommend_require_approval = set(baseline["require_approval"])
        recommend_relax = set()

        for tool_name, stats in per_tool.items():
            if stats["risky"] >= self.risk_threshold:
                recommend_deny.add(tool_name)
                recommend_require_approval.discard(tool_name)
                continue

            if stats["blocked"] >= self.min_block_events and stats["successes"] > 0:
                recommend_relax.add(tool_name)

            if stats["blocked"] >= self.min_block_events or stats["approvals"] > 0:
                recommend_require_approval.add(tool_name)

            if stats["failures"] > stats["successes"] + 1:
                recommend_require_approval.add(tool_name)

        suggested_policy = deepcopy(baseline)
        suggested_policy["deny"] = sorted(recommend_deny)
        suggested_policy["require_approval"] = sorted(recommend_require_approval - recommend_deny)

        recommendations = {
            "baseline_policy": baseline,
            "suggested_policy": suggested_policy,
            "recommend_relax": sorted(recommend_relax - recommend_deny),
            "policy_signals": per_tool,
            "feedback_count": len(feedback),
        }
        return self._update_state(agent, "policy_optimization", recommendations)

    def _baseline_policy(self, agent) -> dict[str, list[str]]:
        policy = getattr(agent, "policy", None)
        if policy is None:
            return {"deny": [], "require_approval": []}

        if isinstance(policy, dict):
            return {
                "deny": list(policy.get("deny", [])),
                "require_approval": list(policy.get("require_approval", [])),
            }

        return {
            "deny": list(getattr(policy, "deny", [])),
            "require_approval": list(getattr(policy, "require_approval", [])),
        }


class ConstraintHardeningStrategy(EvolutionStrategy):
    """E3: Harden constraints from failure root causes → Ψ.constraints ∪ {κ_new}.

    Ratchet-risk mitigation: also audits existing constraints for staleness
    (no recent violations) so the constraint set doesn't grow unboundedly.
    """

    def __init__(self, stale_after: int = 20):
        # A constraint is considered stale if it hasn't been triggered in
        # the last `stale_after` feedback entries.
        self.stale_after = stale_after

    def apply(self, agent):
        feedback = self._feedback_entries(agent)
        existing: dict[str, dict] = dict(
            getattr(agent, "hardened_constraints", {}) or {}
        )

        # Collect failure root causes → candidate new constraints
        for item in feedback:
            if item.get("success") is False or item.get("is_error"):
                cause = item.get("root_cause") or item.get("error") or item.get("reason")
                tool = item.get("tool") or item.get("tool_name")
                if cause and tool:
                    key = f"{tool}:{cause}"
                    if key not in existing:
                        existing[key] = {"tool": tool, "cause": cause, "hits": 0, "last_seen": 0}
                    existing[key]["hits"] += 1
                    existing[key]["last_seen"] = len(feedback)

        # Audit: mark stale constraints (no hit in last `stale_after` entries)
        cutoff = max(0, len(feedback) - self.stale_after)
        active, stale = {}, {}
        for key, c in existing.items():
            (stale if c["last_seen"] < cutoff and c["hits"] > 0 else active)[key] = c

        result = {
            "active_constraints": active,
            "stale_constraints": stale,
            "total": len(existing),
            "feedback_count": len(feedback),
        }
        return self._update_state(agent, "hardened_constraints", result)


class AmoebaSplitStrategy(EvolutionStrategy):
    """E4: Recommend spawning a specialist sub-agent when task_ratio(d) > θ_split.

    Detects when a particular task domain causes persistent early_stop events,
    suggesting the current agent is not the right shape for that work.
    """

    def __init__(self, split_threshold: float = 0.4, min_samples: int = 3):
        self.split_threshold = split_threshold
        self.min_samples = min_samples

    def apply(self, agent):
        feedback = self._feedback_entries(agent)
        domain_counts: dict[str, dict[str, int]] = {}

        for item in feedback:
            domain = item.get("domain") or item.get("task_type") or item.get("goal_type")
            if not domain:
                continue
            stats = domain_counts.setdefault(str(domain), {"total": 0, "early_stop": 0})
            stats["total"] += 1
            if item.get("early_stop") or item.get("type") == "early_stop":
                stats["early_stop"] += 1

        split_recommendations = []
        for domain, stats in domain_counts.items():
            if stats["total"] < self.min_samples:
                continue
            ratio = stats["early_stop"] / stats["total"]
            if ratio > self.split_threshold:
                split_recommendations.append({
                    "domain": domain,
                    "task_ratio": round(ratio, 3),
                    "total": stats["total"],
                    "early_stop": stats["early_stop"],
                    "recommendation": f"spawn specialist sub-agent for domain '{domain}'",
                })

        result = {
            "split_recommendations": split_recommendations,
            "domain_stats": domain_counts,
            "feedback_count": len(feedback),
        }
        return self._update_state(agent, "amoeba_split", result)
