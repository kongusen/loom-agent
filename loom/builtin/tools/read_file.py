from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from loom.interfaces.tool import BaseTool


class ReadArgs(BaseModel):
    path: str = Field(description="文件路径")
    max_bytes: int | None = Field(default=200_000, description="最大读取字节数，默认200KB")
    encoding: str = Field(default="utf-8", description="文本编码")


class ReadFileTool(BaseTool):
    name = "read_file"
    description = "读取文本文件内容"
    args_schema = ReadArgs

    # 🆕 Loom 2.0 - Orchestration attributes
    is_read_only = True
    category = "general"

    async def run(self, **kwargs) -> Any:
        args = self.args_schema(**kwargs)  # type: ignore
        p = Path(args.path).expanduser()
        data = p.read_bytes()
        if args.max_bytes is not None and len(data) > args.max_bytes:
            data = data[: args.max_bytes]
        try:
            return data.decode(args.encoding, errors="replace")
        except Exception:
            return data.decode("utf-8", errors="replace")

