"""Shell inline execution for skills"""

import re
import asyncio
from typing import Any


async def execute_inline_shell(content: str) -> str:
    """Execute inline shell commands in skill content

    Supports syntax: !`command`

    Args:
        content: Skill content with inline shell commands

    Returns:
        Content with shell commands replaced by their output

    Example:
        Input:  "Current dir: !`pwd`"
        Output: "Current dir: /Users/shan/project"
    """
    # Pattern to match !`command`
    pattern = r'!`([^`]+)`'
    matches = re.findall(pattern, content)

    if not matches:
        return content

    # Execute each command and replace
    for cmd in matches:
        try:
            result = await execute_bash_command(cmd.strip())
            content = content.replace(f'!`{cmd}`', result)
        except Exception as e:
            error_msg = f"[Error: {e}]"
            content = content.replace(f'!`{cmd}`', error_msg)

    return content


async def execute_bash_command(command: str) -> str:
    """Execute a bash command and return output

    Args:
        command: Shell command to execute

    Returns:
        Command output (stdout)
    """
    try:
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        if process.returncode == 0:
            return stdout.decode('utf-8').strip()
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
    pattern = r'!`([^`]+)`'
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
        allowed_commands = ['pwd', 'ls', 'echo', 'date', 'whoami', 'git status', 'git branch']

    pattern = r'!`([^`]+)`'
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
                content = content.replace(f'!`{cmd}`', result)
            except Exception as e:
                error_msg = f"[Error: {e}]"
                content = content.replace(f'!`{cmd}`', error_msg)
        else:
            # Replace with warning
            warning = f"[Command not allowed: {cmd_stripped}]"
            content = content.replace(f'!`{cmd}`', warning)

    return content
