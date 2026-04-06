"""06 - Self-Improvement (Evolution Strategies E1–E4)

Demonstrates all four evolution strategies on a mock agent with feedback data.

  E1 ToolLearning      — tracks tool reliability from execution history
  E2 PolicyOptimization — turns blocked actions into policy recommendations
  E3 ConstraintHardening — solidifies failure root causes into permanent constraints
  E4 AmoebaSplit        — detects when to spawn a specialist sub-agent

Run:
    python examples/06_evolution.py
"""

from loom.evolution import (
    ToolLearningStrategy,
    PolicyOptimizationStrategy,
    ConstraintHardeningStrategy,
    AmoebaSplitStrategy,
)


class MockAgent:
    """Minimal agent stub with feedback data for evolution strategies."""

    feedback = [
        {"tool": "web_search", "success": True},
        {"tool": "web_search", "success": True},
        {"tool": "web_search", "success": False},
        {"tool": "file_write", "success": False, "blocked": True, "reason": "permission denied"},
        {"tool": "file_write", "success": False, "blocked": True, "reason": "permission denied"},
        {"tool": "code_exec",  "success": True,  "domain": "python", "early_stop": False},
        {"tool": "code_exec",  "success": True,  "domain": "python", "early_stop": False},
        {"tool": "sql_query",  "success": False, "domain": "sql",    "early_stop": True},
        {"tool": "sql_query",  "success": False, "domain": "sql",    "early_stop": True},
        {"tool": "sql_query",  "success": False, "domain": "sql",    "early_stop": True},
        {"tool": "file_write", "success": False, "root_cause": "missing write permission"},
    ]


def main():
    agent = MockAgent()

    print("=== E1: Tool Learning ===")
    result = ToolLearningStrategy().apply(agent)
    for tool in result.get("preferred_tools", []):
        stats = result["tool_stats"][tool]
        print(f"  preferred: {tool}  success_rate={stats['success_rate']:.0%}")
    for tool in result.get("discouraged_tools", []):
        stats = result["tool_stats"][tool]
        print(f"  discouraged: {tool}  success_rate={stats['success_rate']:.0%}")

    print("\n=== E2: Policy Optimization ===")
    result = PolicyOptimizationStrategy().apply(agent)
    print(f"  deny             : {result['suggested_policy']['deny']}")
    print(f"  require_approval : {result['suggested_policy']['require_approval']}")
    print(f"  relax            : {result['recommend_relax']}")

    print("\n=== E3: Constraint Hardening ===")
    result = ConstraintHardeningStrategy().apply(agent)
    print(f"  Active : {list(result['active_constraints'].keys())}")
    print(f"  Stale  : {list(result['stale_constraints'].keys())}")

    print("\n=== E4: Amoeba Split ===")
    result = AmoebaSplitStrategy(split_threshold=0.5, min_samples=2).apply(agent)
    for rec in result["split_recommendations"]:
        print(f"  {rec['domain']}: ratio={rec['task_ratio']:.0%}  → {rec['recommendation']}")


main()
