"""SkillLoader — load Claude-standard SKILL.md files."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from ..types import Skill

logger = logging.getLogger(__name__)

_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def _parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Parse YAML frontmatter and return (metadata, body)."""
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    raw = m.group(1)
    body = text[m.end() :]
    meta: dict[str, Any] = {}
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
            item_match = re.match(r"^\s+-\s+(.+)", line)
            if item_match is None:
                continue
            item = item_match.group(1).strip()
            existing = meta.get(current_key, "")
            if isinstance(existing, list):
                existing.append(item)
            else:
                meta[current_key] = [item]
        elif current_key and re.match(r"^\s+\S", line) and isinstance(meta.get(current_key), str):
            meta[current_key] += " " + line.strip()
    return meta, body


def _load_resources(skill_dir: Path) -> dict[str, list[str]]:
    """加载 Claude 标准资源目录：scripts/, references/, assets/"""
    resources: dict[str, list[str]] = {}
    for subdir in ["scripts", "references", "assets"]:
        dir_path = skill_dir / subdir
        if dir_path.is_dir():
            resources[subdir] = [
                str(f.relative_to(skill_dir)) for f in dir_path.rglob("*") if f.is_file()
            ]
    return resources


def _extract_tools(resources: dict[str, list[str]]) -> list[str] | None:
    """从 scripts/ 目录提取可执行工具"""
    scripts = resources.get("scripts", [])
    if not scripts:
        return None
    # 提取脚本名称作为工具名（去掉扩展名）
    return [Path(s).stem for s in scripts]


def parse_skill_md(path: Path, metadata_only: bool = False) -> Skill:
    """Parse Claude-standard SKILL.md file.

    Args:
        path: Path to SKILL.md
        metadata_only: If True, only load name/description (Layer 1)
    """
    text = path.read_text(encoding="utf-8")
    meta, body = _parse_frontmatter(text)

    skill_dir = path.parent
    name = meta.get("name", skill_dir.name)
    desc = meta.get("description", "")

    if metadata_only:
        # Layer 1: Only metadata for discovery
        return Skill(
            name=name,
            description=desc,
            instructions="",
            resources=None,
            _skill_path=path,
            _instructions_loaded=False,
        )

    # Layer 2: Full load
    resources = _load_resources(skill_dir)
    tools = _extract_tools(resources)
    return Skill(
        name=name,
        description=desc,
        instructions=body.strip(),
        resources=resources if resources else None,
        tools=tools,
        _skill_path=path,
        _instructions_loaded=True,
    )


def load_dir(path: str | Path, metadata_only: bool = False) -> list[Skill]:
    """扫描目录加载所有 SKILL.md 文件

    Args:
        path: Directory containing skills
        metadata_only: If True, only load metadata for Layer 1 discovery
    """
    root = Path(path)
    skills: list[Skill] = []
    for md in sorted(root.glob("*/SKILL.md")):
        try:
            skills.append(parse_skill_md(md, metadata_only=metadata_only))
        except Exception as e:
            logger.warning("Failed to parse %s: %s", md, e)
    top = root / "SKILL.md"
    if top.is_file():
        try:
            skills.append(parse_skill_md(top, metadata_only=metadata_only))
        except Exception as e:
            logger.warning("Failed to parse %s: %s", top, e)
    return skills


def load_git(
    url: str, target: str | Path | None = None, metadata_only: bool = False
) -> list[Skill]:
    """从 git 仓库克隆并加载技能

    Args:
        url: Git repository URL
        target: Target directory (temp dir if None)
        metadata_only: If True, only load metadata for Layer 1 discovery
    """
    import subprocess
    import tempfile

    dest = Path(target) if target else Path(tempfile.mkdtemp(prefix="loom-skills-"))
    if not (dest / ".git").exists():
        subprocess.run(
            ["git", "clone", "--depth", "1", url, str(dest)], check=True, capture_output=True
        )
    return load_dir(dest, metadata_only=metadata_only)


# API aliases for consistency
def query_skill_metadata(path: str | Path) -> list[Skill]:
    """Load only skill metadata (name + description) for discovery."""
    return load_dir(path, metadata_only=True)


def query_skill(name: str, skills: list[Skill]) -> Skill | None:
    """Query a specific skill by name from loaded skills."""
    for skill in skills:
        if skill.name == name:
            return skill
    return None


def list_skill_metadata(path: str | Path) -> list[dict[str, str]]:
    """List all skill metadata as dicts."""
    skills = query_skill_metadata(path)
    return [{"name": s.name, "description": s.description} for s in skills]


def load_skill(name: str, path: str | Path) -> Skill | None:
    """Load a specific skill with full instructions."""
    skills = load_dir(path, metadata_only=False)
    return query_skill(name, skills)
