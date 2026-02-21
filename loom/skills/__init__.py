"""Skills — trigger-based skill activation and context injection."""

from .registry import SkillRegistry
from .provider import SkillProvider
from .activator import match_trigger, match_trigger_async

__all__ = ["SkillRegistry", "SkillProvider", "match_trigger", "match_trigger_async"]
