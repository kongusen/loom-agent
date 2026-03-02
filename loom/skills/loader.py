"""SkillLoader — load Anthropic-format SKILL.md files into Skill objects."""

from __future__ import annotations

import logging
import re
import subprocess
from pathlib import Path
from typing import Any

from ..types import Skill, SkillTrigger

logger = logging.getLogger(__name__)

_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_YAML_KV_RE = re.compile(r"^(\w[\w-]*):\s*(.+)$", re.MULTILINE)
_YAML_LIST_ITEM_RE = re.compile(r"^\s+-\s+(.+)$", re.MULTILINE)


def _parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Parse YAML frontmatter and return (metadata, body)."""
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    raw = m.group(1)
    body = text[m.end():]
    meta: dict[str, Any] = {}
    # Parse simple key: value pairs and list items
    lines = raw.split("\n")
    current_key = ""
    for line in lines:
        kv = re.match(r"^(\w[\w-]*):\s*(.*)", line)
        if kv:
            current_key = kv.group(1)
            val = kv.group(2).strip()
            if val and not val.startswith("|"):
                meta[current_key] = val
            elif not val or val == "|":
                meta[current_key] = ""
        elif current_key and re.match(r"^\s+-\s+", line):
            item = re.match(r"^\s+-\s+(.+)", line).group(1).strip()
            existing = meta.get(current_key, "")
            if isinstance(existing, list):
                existing.append(item)
            else:
                meta[current_key] = [item]
        elif current_key and re.match(r"^\s+\S", line) and isinstance(meta.get(current_key), str):
            meta[current_key] += " " + line.strip()
    return meta, body


def parse_skill_md(path: Path) -> Skill:
    """Parse a single SKILL.md file into a Skill object."""
    text = path.read_text(encoding="utf-8")
    meta, body = _parse_frontmatter(text)
    name = meta.get("name", path.parent.name)
    desc = meta.get("description", "")
    # Build keyword trigger from description words
    keywords = list(re.findall(r"\w{4,}", f"{name} {desc}".lower()))[:10]
    trigger = SkillTrigger(type="keyword", keywords=keywords) if keywords else None
    return Skill(
        name=name,
        description=desc,
        instructions=body.strip(),
        trigger=trigger,
    )


def load_dir(path: str | Path) -> list[Skill]:
    """Scan directory for */SKILL.md and top-level SKILL.md, return Skill list."""
    root = Path(path)
    skills: list[Skill] = []
    for md in sorted(root.glob("*/SKILL.md")):
        try:
            skills.append(parse_skill_md(md))
        except Exception as e:
            logger.warning("Failed to parse %s: %s", md, e)
    # Also check root-level SKILL.md
    top = root / "SKILL.md"
    if top.is_file():
        try:
            skills.append(parse_skill_md(top))
        except Exception as e:
            logger.warning("Failed to parse %s: %s", top, e)
    return skills


def load_git(url: str, target: str | Path | None = None) -> list[Skill]:
    """Clone a git repo and load all skills from it."""
    import tempfile

    dest = Path(target) if target else Path(tempfile.mkdtemp(prefix="loom-skills-"))
    if not (dest / ".git").exists():
        subprocess.run(
            ["git", "clone", "--depth", "1", url, str(dest)],
            check=True,
            capture_output=True,
        )
    return load_dir(dest)
