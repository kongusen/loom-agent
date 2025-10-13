from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union


@dataclass
class AgentConfig:
    """Definition for a sub-agent loaded from markdown frontmatter.

    Frontmatter fields supported (YAML subset):
    - name (required): agent type identifier
    - description (required): when to use this agent
    - tools: '*' or list of tool names
    - model_name: optional default model for this agent
    - color: optional UI color (ignored by Loom runtime)
    Body (markdown) is treated as system prompt.
    """

    agent_type: str
    when_to_use: str
    tools: Union[List[str], str]  # list of tool names or '*'
    system_prompt: str
    location: str  # 'built-in' | 'user' | 'project'
    color: Optional[str] = None
    model_name: Optional[str] = None


_CACHE_ACTIVE: Optional[List[AgentConfig]] = None
_CACHE_ALL: Optional[List[AgentConfig]] = None


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return path.read_text(errors="replace")


def _split_frontmatter(md: str) -> Tuple[Dict[str, str], str]:
    """Parse a minimal YAML frontmatter block.

    This supports a conservative subset sufficient for agent definitions without
    adding external dependencies:
    - key: value pairs
    - tools: '*' | [a, b] | tools:\n  - a\n  - b
    - quotes around values are optional
    """

    lines = md.splitlines()
    if not lines or not lines[0].strip().startswith("---"):
        return {}, md

    fm: Dict[str, str] = {}
    i = 1
    list_key: Optional[str] = None
    list_vals: List[str] = []

    while i < len(lines):
        line = lines[i]
        if line.strip().startswith("---"):
            i += 1
            break

        # handle list continuation (e.g., tools: then lines starting with - )
        if list_key is not None:
            if line.lstrip().startswith("- "):
                item = line.lstrip()[2:].strip().strip('"').strip("'")
                list_vals.append(item)
                i += 1
                continue
            # list ended
            fm[list_key] = ",".join(list_vals)
            list_key = None
            list_vals = []
            # fallthrough to parse current line as key

        # key: value
        if ":" in line:
            key, val = line.split(":", 1)
            key = key.strip()
            val = val.strip()
            if val == "" or val is None:
                # possible start of block list
                list_key = key
                list_vals = []
            else:
                # normalize quotes
                sval = val.strip().strip('"').strip("'")
                fm[key] = sval
        i += 1

    body = "\n".join(lines[i:]).strip()
    return fm, body


def _parse_tools(value: Optional[str]) -> Union[List[str], str]:
    if not value or value == "*":
        return "*"
    raw = value.strip()
    if raw.startswith("[") and raw.endswith("]"):
        # inline list, split by comma
        inner = raw[1:-1].strip()
        if not inner:
            return []
        items = [_.strip().strip('"').strip("'") for _ in inner.split(",")]
        return [i for i in items if i]
    # fallback: comma-separated
    if "," in raw:
        return [_.strip() for _ in raw.split(",") if _.strip()]
    return [raw]


def _scan_agent_dir(dir_path: Path, location: str) -> List[AgentConfig]:
    if not dir_path.exists() or not dir_path.is_dir():
        return []
    agents: List[AgentConfig] = []
    for f in sorted(dir_path.iterdir()):
        if not f.is_file() or not f.name.endswith(".md"):
            continue
        try:
            content = _read_text(f)
            fm, body = _split_frontmatter(content)

            name = fm.get("name") or fm.get("agent") or ""
            desc = fm.get("description") or fm.get("when") or ""
            if not name or not desc:
                # skip invalid definitions
                continue

            # prefer model_name; ignore deprecated 'model' if both set
            model_name = fm.get("model_name") or (fm.get("model") if "model_name" not in fm else None)
            tools = _parse_tools(fm.get("tools"))
            color = fm.get("color")

            agents.append(
                AgentConfig(
                    agent_type=name,
                    when_to_use=desc.replace("\\n", "\n"),
                    tools=tools,
                    system_prompt=body,
                    location=location,
                    color=color,
                    model_name=model_name,
                )
            )
        except Exception:
            # best-effort; skip malformed files
            continue
    return agents


def _builtin_agents() -> List[AgentConfig]:
    return [
        AgentConfig(
            agent_type="general-purpose",
            when_to_use=(
                "General-purpose agent for researching codebases and executing multi-step tasks"
            ),
            tools="*",
            system_prompt=(
                "You are a general-purpose agent. Use available tools appropriately.\n"
                "Be thorough and efficient."
            ),
            location="built-in",
        )
    ]


def _load_all_agents_uncached() -> Tuple[List[AgentConfig], List[AgentConfig]]:
    home = Path.home()
    cwd = Path.cwd()

    user_claude = home / ".claude" / "agents"
    user_loom = home / ".loom" / "agents"
    proj_claude = cwd / ".claude" / "agents"
    proj_loom = cwd / ".loom" / "agents"

    builtin = _builtin_agents()
    user_claude_agents = _scan_agent_dir(user_claude, "user")
    user_loom_agents = _scan_agent_dir(user_loom, "user")
    proj_claude_agents = _scan_agent_dir(proj_claude, "project")
    proj_loom_agents = _scan_agent_dir(proj_loom, "project")

    # override priority: builtin < user/.claude < user/.loom < project/.claude < project/.loom
    by_key: Dict[str, AgentConfig] = {}
    for src in (builtin, user_claude_agents, user_loom_agents, proj_claude_agents, proj_loom_agents):
        for a in src:
            by_key[a.agent_type] = a

    active = list(by_key.values())
    all_agents = [*builtin, *user_claude_agents, *user_loom_agents, *proj_claude_agents, *proj_loom_agents]
    return active, all_agents


def load_agents(force_reload: bool = False) -> Tuple[List[AgentConfig], List[AgentConfig]]:
    global _CACHE_ACTIVE, _CACHE_ALL
    if not force_reload and _CACHE_ACTIVE is not None and _CACHE_ALL is not None:
        return _CACHE_ACTIVE, _CACHE_ALL
    active, all_agents = _load_all_agents_uncached()
    _CACHE_ACTIVE, _CACHE_ALL = active, all_agents
    return active, all_agents


def get_agent_by_type(agent_type: str) -> Optional[AgentConfig]:
    active, _ = load_agents()
    for a in active:
        if a.agent_type == agent_type:
            return a
    return None


def get_available_agent_types() -> List[str]:
    active, _ = load_agents()
    return [a.agent_type for a in active]

