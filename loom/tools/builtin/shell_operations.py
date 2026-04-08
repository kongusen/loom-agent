"""Shell 操作工具"""

import asyncio
from contextlib import suppress
from typing import Any


async def bash(command: str, timeout: int = 120000) -> dict[str, Any]:
    """执行 bash 命令"""
    proc = None
    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            shell=True
        )

        stdout, stderr = await asyncio.wait_for(
            proc.communicate(),
            timeout=timeout / 1000
        )

        return {
            "command": command,
            "stdout": stdout.decode('utf-8', errors='replace'),
            "stderr": stderr.decode('utf-8', errors='replace'),
            "exit_code": proc.returncode
        }
    except TimeoutError as e:
        if proc:
            with suppress(ProcessLookupError):
                proc.kill()
            with suppress(Exception):
                await proc.wait()
        raise TimeoutError(f"Command timed out after {timeout}ms") from e
