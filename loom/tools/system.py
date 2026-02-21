"""System tools — shell, read_file, write_file, list_directory."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

from pydantic import BaseModel

from ..types import ToolDefinition, ToolContext
from .schema import PydanticSchema


class ShellParams(BaseModel):
    command: str
    cwd: str | None = None
    timeout: int = 30000


async def _shell_exec(params: ShellParams, ctx: ToolContext) -> dict:
    proc = await asyncio.create_subprocess_shell(
        params.command, cwd=params.cwd,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=params.timeout / 1000)
    return {"exitCode": proc.returncode, "stdout": stdout.decode(), "stderr": stderr.decode()}


shell_tool = ToolDefinition(
    name="shell", description="Execute a shell command and return stdout/stderr",
    parameters=PydanticSchema(ShellParams), execute=_shell_exec,
)


class ReadFileParams(BaseModel):
    path: str
    encoding: str = "utf-8"


async def _read_file_exec(params: ReadFileParams, ctx: ToolContext) -> dict:
    content = Path(params.path).read_text(encoding=params.encoding)
    return {"content": content}


read_file_tool = ToolDefinition(
    name="read_file", description="Read the contents of a file",
    parameters=PydanticSchema(ReadFileParams), execute=_read_file_exec,
)


class WriteFileParams(BaseModel):
    path: str
    content: str
    mkdirp: bool = True


async def _write_file_exec(params: WriteFileParams, ctx: ToolContext) -> dict:
    p = Path(params.path)
    if params.mkdirp:
        p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(params.content, encoding="utf-8")
    return {"path": str(p), "bytes": len(params.content.encode())}


write_file_tool = ToolDefinition(
    name="write_file", description="Write content to a file",
    parameters=PydanticSchema(WriteFileParams), execute=_write_file_exec,
)


class ListDirParams(BaseModel):
    path: str
    recursive: bool = False


async def _list_dir_exec(params: ListDirParams, ctx: ToolContext) -> dict:
    p = Path(params.path)
    if not params.recursive:
        return {"entries": [{"name": e.name, "type": "directory" if e.is_dir() else "file"} for e in p.iterdir()]}
    result = []
    for root, dirs, files in os.walk(params.path):
        for d in dirs:
            result.append({"path": os.path.join(root, d), "type": "directory"})
        for f in files:
            result.append({"path": os.path.join(root, f), "type": "file"})
    return {"entries": result}


list_dir_tool = ToolDefinition(
    name="list_directory", description="List files and directories at a given path",
    parameters=PydanticSchema(ListDirParams), execute=_list_dir_exec,
)
