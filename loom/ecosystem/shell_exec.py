"""Shell inline execution for skills"""

import asyncio
import re
from contextlib import suppress
from typing import Any


async def execute_inline_shell(content: str, shell_config: Any = None) -> str:
    """Execute inline shell commands in skill content

    Supports syntax: !`command`

    Args:
        content: Skill content with inline shell commands
        shell_config: Optional ShellConfig object for custom shell settings

    Returns:
        Content with shell commands replaced by their output

    Example:
        Input:  "Current dir: !`pwd`"
        Output: "Current dir: /Users/shan/project"
    """
    # Pattern to match !`command`
    pattern = r"!`([^`]+)`"
    matches = re.findall(pattern, content)

    if not matches:
        return content

    # Execute each command and replace
    for cmd in matches:
        try:
            result = await execute_bash_command(cmd.strip(), shell_config)
            content = content.replace(f"!`{cmd}`", result)
        except Exception as e:
            error_msg = f"[Error: {e}]"
            content = content.replace(f"!`{cmd}`", error_msg)

    return content


async def execute_bash_command(command: str, shell_config: Any = None) -> str:
    """Execute a bash command and return output

    Args:
        command: Shell command to execute
        shell_config: Optional ShellConfig object for custom shell settings

    Returns:
        Command output (stdout)
    """
    try:
        # Use custom shell config if provided
        if shell_config:
            shell_cmd = shell_config.command
            shell_args = shell_config.args if isinstance(shell_config.args, list) else []
            timeout = shell_config.timeout

            # Merge custom env with current env
            import os

            env = os.environ.copy()
            if shell_config.env:
                env.update(shell_config.env)

            # Build full command
            if shell_args:
                full_command = [shell_cmd] + shell_args + [command]
            else:
                full_command = [shell_cmd, command]

            process = await asyncio.create_subprocess_exec(
                *full_command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
        else:
            # Default shell execution
            timeout = 30
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
        except TimeoutError:
            with suppress(ProcessLookupError):
                process.kill()
            with suppress(Exception):
                await process.wait()
            return f"[Error: Command timed out after {timeout}s]"

        if process.returncode == 0:
            return stdout.decode("utf-8").strip()
        else:
            return f"[Error: {stderr.decode('utf-8').strip()}]"

    except Exception as e:
        return f"[Error: {str(e)}]"


def has_inline_shell_commands(content: str) -> bool:
    """Check if content contains inline shell commands

    Args:
        content: Skill content

    Returns:
        True if content has !`...` patterns
    """
    pattern = r"!`([^`]+)`"
    return bool(re.search(pattern, content))


async def execute_inline_shell_safe(content: str, allowed_commands: list[str] | None = None) -> str:
    """Execute inline shell commands with safety checks

    Args:
        content: Skill content
        allowed_commands: List of allowed command prefixes (e.g., ['ls', 'pwd', 'git'])

    Returns:
        Content with safe commands executed
    """
    if allowed_commands is None:
        # Default safe commands
        allowed_commands = ["pwd", "ls", "echo", "date", "whoami", "git status", "git branch"]

    pattern = r"!`([^`]+)`"
    matches = re.findall(pattern, content)

    if not matches:
        return content

    for cmd in matches:
        cmd_stripped = cmd.strip()

        # Check if command is allowed
        is_allowed = any(cmd_stripped.startswith(allowed) for allowed in allowed_commands)

        if is_allowed:
            try:
                result = await execute_bash_command(cmd_stripped)
                content = content.replace(f"!`{cmd}`", result)
            except Exception as e:
                error_msg = f"[Error: {e}]"
                content = content.replace(f"!`{cmd}`", error_msg)
        else:
            # Replace with warning
            warning = f"[Command not allowed: {cmd_stripped}]"
            content = content.replace(f"!`{cmd}`", warning)

    return content
