from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List


DEFAULT_DIR = Path.home() / ".loom"
DEFAULT_PATH = DEFAULT_DIR / "config.json"


@dataclass
class PermissionStore:
    """Persistent allow-list for tools (framework capability).

    Schema stored at ~/.loom/config.json:
    {
      "allowed_tools": ["*" | "tool_name", ...]
    }
    """

    allowed_tools: List[str] = field(default_factory=list)
    path: Path = DEFAULT_PATH

    @classmethod
    def load_default(cls) -> "PermissionStore":
        try:
            if DEFAULT_PATH.exists():
                data = json.loads(DEFAULT_PATH.read_text(encoding="utf-8"))
                allowed = data.get("allowed_tools", [])
                if isinstance(allowed, list):
                    return cls(allowed_tools=[str(x) for x in allowed], path=DEFAULT_PATH)
        except Exception:
            pass
        return cls(path=DEFAULT_PATH)

    def is_allowed(self, tool_name: str) -> bool:
        if "*" in self.allowed_tools:
            return True
        return tool_name in self.allowed_tools

    def grant(self, tool_name: str) -> None:
        if tool_name not in self.allowed_tools:
            self.allowed_tools.append(tool_name)
            self.allowed_tools.sort()

    def revoke(self, tool_name: str) -> None:
        try:
            self.allowed_tools.remove(tool_name)
        except ValueError:
            pass

    def save(self) -> None:
        try:
            DEFAULT_DIR.mkdir(parents=True, exist_ok=True)
            data = {"allowed_tools": self.allowed_tools}
            self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
        except Exception:
            # best-effort; ignore IO failures
            pass

