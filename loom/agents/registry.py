from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Union


@dataclass
class AgentSpec:
    """Programmatic agent definition for Loom.

    This enables framework-first agent configuration without on-disk files.

    Fields:
    - agent_type: identifier used by Task tool (subagent_type)
    - description: when to use this agent (for docs/UX; not enforced)
    - system_instructions: system prompt injected when this agent is used
    - tools: '*' or list of tool names that this agent may use
    - model_name: optional model override for this agent
    """

    agent_type: str
    description: str
    system_instructions: str
    tools: Union[List[str], str] = "*"
    model_name: Optional[str] = None


_AGENTS: Dict[str, AgentSpec] = {}


def register_agent(spec: AgentSpec) -> AgentSpec:
    """Register or override an agent spec in memory.

    The most recent registration wins for a given agent_type.
    """

    _AGENTS[spec.agent_type] = spec
    return spec


def get_agent_by_type(agent_type: str) -> Optional[AgentSpec]:
    return _AGENTS.get(agent_type)


def list_agent_types() -> List[str]:
    return list(_AGENTS.keys())


def clear_agents() -> None:
    _AGENTS.clear()
