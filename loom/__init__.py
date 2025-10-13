from .components.agent import Agent
from .components.chain import Chain
from .components.router import Router
from .components.workflow import Workflow
from .llm import (
    LLMConfig,
    LLMProvider,
    LLMCapabilities,
    LLMFactory,
    ModelPool,
    ModelRegistry,
)
from .agent import agent, agent_from_env
from .tooling import tool
from .agents import AgentSpec, register_agent, list_agent_types, get_agent_by_type
from .agents.refs import AgentRef, ModelRef, agent_ref, model_ref

try:
    from importlib.metadata import version as _pkg_version

    __version__ = _pkg_version("loom-agent")
except Exception:  # pragma: no cover - best-effort
    __version__ = "0"

__all__ = [
    "Agent",
    "Chain",
    "Router",
    "Workflow",
    "LLMConfig",
    "LLMProvider",
    "LLMCapabilities",
    "LLMFactory",
    "ModelPool",
    "ModelRegistry",
    "agent",
    "tool",
    "agent_from_env",
    "AgentSpec",
    "register_agent",
    "list_agent_types",
    "get_agent_by_type",
    "AgentRef",
    "ModelRef",
    "agent_ref",
    "model_ref",
    "__version__",
]
