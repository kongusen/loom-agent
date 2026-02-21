"""Skills — trigger-based skill activation and context injection."""

from .activator import match_trigger, match_trigger_async
from .provider import SkillProvider
from .registry import SkillRegistry

__all__ = ["SkillRegistry", "SkillProvider", "match_trigger", "match_trigger_async"]
