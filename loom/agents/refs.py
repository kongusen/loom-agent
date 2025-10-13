from __future__ import annotations

from dataclasses import dataclass
from typing import Union


@dataclass(frozen=True)
class AgentRef:
    agent_type: str


def agent_ref(agent_type: str) -> AgentRef:
    return AgentRef(agent_type=agent_type)


@dataclass(frozen=True)
class ModelRef:
    name: str


def model_ref(name: str) -> ModelRef:
    return ModelRef(name=name)


# Back-compat typing helper for convenience
AgentReferenceLike = Union[str, AgentRef]
ModelReferenceLike = Union[str, ModelRef]

