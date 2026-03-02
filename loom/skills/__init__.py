"""Skills — trigger-based skill activation and context injection."""

from .activator import match_trigger, match_trigger_async
from .catalog_provider import SkillCatalogProvider
from .loader import load_dir, load_git, parse_skill_md
from .provider import SkillProvider
from .registry import SkillRegistry

__all__ = [
    "SkillCatalogProvider",
    "SkillProvider",
    "SkillRegistry",
    "load_dir",
    "load_git",
    "match_trigger",
    "match_trigger_async",
    "parse_skill_md",
]
