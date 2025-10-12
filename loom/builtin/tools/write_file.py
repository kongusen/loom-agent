from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from loom.interfaces.tool import BaseTool


class WriteArgs(BaseModel):
    path: str = Field(description="文件路径")
    content: str = Field(description="写入内容")
    encoding: str = Field(default="utf-8", description="文本编码")
    overwrite: bool = Field(default=True, description="是否覆盖")


class WriteFileTool(BaseTool):
    name = "write_file"
    description = "写入文本到文件（可能覆盖）"
    args_schema = WriteArgs

    async def run(self, **kwargs) -> Any:
        args = self.args_schema(**kwargs)  # type: ignore
        p = Path(args.path).expanduser()
        if p.exists() and not args.overwrite:
            return f"File exists and overwrite=False: {p}"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(args.content, encoding=args.encoding)
        return f"Wrote {len(args.content)} chars to {str(p)}"

