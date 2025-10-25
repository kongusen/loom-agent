from __future__ import annotations

import re
from pathlib import Path
from typing import Any, List

from pydantic import BaseModel, Field

from loom.interfaces.tool import BaseTool


class GrepArgs(BaseModel):
    pattern: str = Field(description="正则表达式")
    path: str | None = Field(default=None, description="目标文件")
    glob_pattern: str | None = Field(default=None, description="Glob 模式（与 path 二选一）")
    flags: str | None = Field(default="", description="i=IGNORECASE, m=MULTILINE")
    encoding: str = Field(default="utf-8")


class GrepTool(BaseTool):
    name = "grep"
    description = "在文件或文件集内检索正则匹配"
    args_schema = GrepArgs

    # 🆕 Loom 2.0 - Orchestration attributes
    is_read_only = True
    category = "general"

    async def run(self, **kwargs) -> Any:
        args = self.args_schema(**kwargs)  # type: ignore
        flags = 0
        if args.flags:
            if "i" in args.flags:
                flags |= re.IGNORECASE
            if "m" in args.flags:
                flags |= re.MULTILINE
        regex = re.compile(args.pattern, flags)

        files: List[Path] = []
        if args.path:
            files = [Path(args.path).expanduser()]
        elif args.glob_pattern:
            from glob import glob

            files = [Path(p) for p in glob(args.glob_pattern, recursive=True)]
        else:
            return "必须提供 path 或 glob_pattern"

        matches: List[str] = []
        for f in files:
            if not f.exists() or not f.is_file():
                continue
            try:
                for i, line in enumerate(f.read_text(encoding=args.encoding, errors="replace").splitlines(), 1):
                    if regex.search(line):
                        matches.append(f"{f}:{i}: {line}")
            except Exception as e:
                matches.append(f"{f}: <error {e}>")
        return "\n".join(matches)

