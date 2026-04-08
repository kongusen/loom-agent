"""Tests for shell execution helpers used by the skill system."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from loom.ecosystem.shell_exec import (
    execute_bash_command,
    execute_inline_shell,
    execute_inline_shell_safe,
    has_inline_shell_commands,
)
from loom.ecosystem.skill import ShellConfig


class TestShellExec:
    @pytest.mark.asyncio
    async def test_execute_inline_shell_returns_original_content_when_no_commands(self):
        content = "Plain content with no shell command."
        assert await execute_inline_shell(content) == content

    @pytest.mark.asyncio
    async def test_execute_inline_shell_replaces_multiple_commands(self):
        calls: list[tuple[str, object | None]] = []

        async def fake_execute(command: str, shell_config: object | None = None) -> str:
            calls.append((command, shell_config))
            if command == "pwd":
                return "/tmp/project"
            return "tester"

        with patch(
            "loom.ecosystem.shell_exec.execute_bash_command",
            new=fake_execute,
        ):
            result = await execute_inline_shell("Dir: !`pwd` User: !`whoami`")

        assert result == "Dir: /tmp/project User: tester"
        assert calls == [("pwd", None), ("whoami", None)]

    @pytest.mark.asyncio
    async def test_execute_inline_shell_replaces_errors(self):
        async def fake_execute(command: str, shell_config: object | None = None) -> str:
            _ = command
            _ = shell_config
            raise RuntimeError("boom")

        with patch(
            "loom.ecosystem.shell_exec.execute_bash_command",
            new=fake_execute,
        ):
            result = await execute_inline_shell("Run: !`pwd`")

        assert result == "Run: [Error: boom]"

    @pytest.mark.asyncio
    async def test_execute_bash_command_uses_custom_shell_config(self):
        config = ShellConfig(
            command="/bin/sh",
            args=["-c"],
            env={"CUSTOM_FLAG": "enabled"},
            timeout=5,
        )
        output = await execute_bash_command("printf %s \"$CUSTOM_FLAG\"", config)
        assert output == "enabled"

    @pytest.mark.asyncio
    async def test_execute_bash_command_timeout_kills_and_waits(self):
        class FakeProcess:
            def __init__(self) -> None:
                self.kill = MagicMock()
                self.returncode = None
                self.wait_called = False

            async def communicate(self) -> tuple[bytes, bytes]:
                return b"", b""

            async def wait(self) -> None:
                self.wait_called = True

        process = FakeProcess()

        async def fake_create_subprocess_shell(*args, **kwargs):
            _ = args
            _ = kwargs
            return process

        async def fake_wait_for(awaitable, timeout):
            close = getattr(awaitable, "close", None)
            if callable(close):
                close()
            _ = timeout
            raise TimeoutError

        with patch(
            "loom.ecosystem.shell_exec.asyncio.create_subprocess_shell",
            new=fake_create_subprocess_shell,
        ), patch(
            "loom.ecosystem.shell_exec.asyncio.wait_for",
            new=fake_wait_for,
        ):
            result = await execute_bash_command("sleep 10")

        assert "timed out" in result
        process.kill.assert_called_once()
        assert process.wait_called is True

    def test_has_inline_shell_commands_detects_pattern(self):
        assert has_inline_shell_commands("Run !`pwd` now") is True
        assert has_inline_shell_commands("Nothing to run") is False

    @pytest.mark.asyncio
    async def test_execute_inline_shell_safe_blocks_disallowed_commands(self):
        result = await execute_inline_shell_safe("Try !`rm -rf /tmp/x`", allowed_commands=["pwd"])
        assert result == "Try [Command not allowed: rm -rf /tmp/x]"

    @pytest.mark.asyncio
    async def test_execute_inline_shell_safe_runs_allowed_commands(self):
        async def fake_execute(command: str, shell_config: object | None = None) -> str:
            _ = command
            _ = shell_config
            return "hello"

        with patch(
            "loom.ecosystem.shell_exec.execute_bash_command",
            new=fake_execute,
        ):
            result = await execute_inline_shell_safe("Say !`echo hello`", allowed_commands=["echo"])

        assert result == "Say hello"
