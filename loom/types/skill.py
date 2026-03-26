"""Skill type definition."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class Skill:
    """Skill definition with progressive loading support."""

    name: str = ""
    description: str = ""
    instructions: str = ""
    resources: dict[str, list[str]] | None = None

    # Progressive loading
    _skill_path: Path | None = None
    _instructions_loaded: bool = True

    def load_instructions(self) -> None:
        """Lazy load full instructions if not yet loaded."""
        if self._instructions_loaded or not self._skill_path:
            return
        path = Path(self._skill_path)
        if path.exists():
            text = path.read_text(encoding="utf-8")
            import re
            m = re.match(r"\A---\s*\n.*?\n---\s*\n", text, re.DOTALL)
            self.instructions = text[m.end() :].strip() if m else text.strip()
            self._instructions_loaded = True
