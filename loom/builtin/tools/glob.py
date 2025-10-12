from __future__ import annotations

import glob as _glob
from pathlib import Path
from typing import Any, List

from pydantic import BaseModel, Field

from loom.interfaces.tool import BaseTool


class GlobArgs(BaseModel):
    pattern: str = Field(description="Glob 匹配模式，例如 **/*.py")
    cwd: str | None = Field(default=None, description="可选工作目录")


class GlobTool(BaseTool):
    name = "glob"
    description = "按模式匹配文件路径"
    args_schema = GlobArgs

    async def run(self, **kwargs) -> Any:
        args = self.args_schema(**kwargs)  # type: ignore
        cwd = Path(args.cwd).expanduser() if args.cwd else Path.cwd()
        paths: List[str] = [str(Path(p)) for p in _glob.glob(str(cwd / args.pattern), recursive=True)]
        return "\n".join(paths)

