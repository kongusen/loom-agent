"""Open Questions Examples - Runner

运行所有开放问题实验的主入口
"""

import asyncio
from q1_self_perception import experiment_self_perception, analyze_bias
from q2_dmax_setting import experiment_dmax_by_task
from q3_dag_coupling import experiment_dag_write_conflicts
from q4_evolution_metrics import experiment_evolution_metrics
from q5_veto_logging import experiment_veto_logging
from q7_heartbeat_interval import experiment_heartbeat_interval
from q8_urgency_classification import experiment_urgency_classification
from q9_heartbeat_token_pressure import experiment_token_pressure
from q10_subagent_mcp_isolation import experiment_mcp_isolation
from q11_skill_effort_hints import experiment_effort_hints
from q12_fork_cache_optimization import experiment_cache_optimization
from q13_knowledge_surface_pressure import experiment_evidence_strategies

async def run_all_experiments():
    print("Running Chapter 10 Open Questions Experiments\n")

    experiments = {
        "Q1 - Self Perception": experiment_self_perception,
        "Q2 - d_max Setting": experiment_dmax_by_task,
        "Q3 - DAG Coupling": experiment_dag_write_conflicts,
        "Q4 - Evolution Metrics": experiment_evolution_metrics,
        "Q5 - Veto Logging": experiment_veto_logging,
        "Q7 - Heartbeat Interval": experiment_heartbeat_interval,
        "Q8 - Urgency Classification": experiment_urgency_classification,
        "Q9 - Token Pressure": experiment_token_pressure,
        "Q10 - MCP Isolation": experiment_mcp_isolation,
        "Q11 - Effort Hints": experiment_effort_hints,
        "Q12 - Cache Optimization": experiment_cache_optimization,
        "Q13 - Knowledge Surface": experiment_evidence_strategies,
    }

    for name, experiment in experiments.items():
        print(f"\n{'='*60}")
        print(f"Running: {name}")
        print('='*60)
        try:
            result = await experiment()
            print(f"✓ Completed: {name}")
        except Exception as e:
            print(f"✗ Failed: {name} - {e}")

if __name__ == "__main__":
    asyncio.run(run_all_experiments())
