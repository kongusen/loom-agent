# Chapter 10 Open Questions - Experimental Examples

Minimal examples demonstrating the open questions from Chapter 10 of the hernss framework guide.

## Structure

Each question has a dedicated example file following the pattern:
```
问题 -> 观测现象 -> 实验设计 -> 证据要求
```

## Categories

### 认知可靠性 (Cognitive Reliability)
- `q1_self_perception.py` - LLM self-assessment reliability
- `q9_heartbeat_token_pressure.py` - Event surface token pressure
- `q11_skill_effort_hints.py` - Skill effort quantification
- `q13_knowledge_surface_pressure.py` - Evidence pack token management

### 调度与终止性 (Scheduling & Termination)
- `q2_dmax_setting.py` - Task-specific depth limits
- `q7_heartbeat_interval.py` - Optimal heartbeat timing
- `q12_fork_cache_optimization.py` - Multi-model cache strategy

### 协作与隔离 (Collaboration & Isolation)
- `q3_dag_coupling.py` - DAG topology write conflicts
- `q10_subagent_mcp_isolation.py` - Sub-agent MCP isolation

### 演化与治理 (Evolution & Governance)
- `q4_evolution_metrics.py` - System evolution indicators
- `q5_veto_logging.py` - Harness veto audit logs
- `q8_urgency_classification.py` - Heartbeat urgency classification

## Usage

Each example is self-contained and demonstrates:
1. The problem scenario
2. Observable phenomena
3. Experimental design
4. Evidence collection
