"""Test tool operations - file, shell, task, web, agent, notebook, mcp, skill"""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, AsyncMock

from loom.tools.builtin.file_operations import (
    read_file, write_file, edit_file, glob_files, grep_files,
)
from loom.tools.builtin.shell_operations import bash
from loom.tools.builtin.task_operations import (
    task_create, task_update, task_list, task_get, _tasks, Task,
)
from loom.tools.builtin.web_operations import web_search
from loom.tools.builtin.agent_operations import spawn_agent, ask_user
from loom.tools.builtin.mcp_operations import mcp_list_resources, mcp_read_resource, mcp_call_tool
from loom.tools.builtin.skill_operations import skill_invoke, skill_discover
from loom.tools.builtin.notebook_operations import notebook_edit


# ── File Operations ──

class TestReadFile:
    @pytest.mark.asyncio
    async def test_read_existing_file(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("line1\nline2\nline3\n")
            path = f.name
        try:
            result = await read_file(path)
            assert result["content"] == "line1\nline2\nline3\n"
            assert result["total_lines"] == 3
            assert result["num_lines"] == 3
        finally:
            Path(path).unlink()

    @pytest.mark.asyncio
    async def test_read_with_offset(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("line1\nline2\nline3\n")
            path = f.name
        try:
            result = await read_file(path, offset=2)
            assert result["start_line"] == 2
            assert "line2" in result["content"]
            assert "line1" not in result["content"]
        finally:
            Path(path).unlink()

    @pytest.mark.asyncio
    async def test_read_with_limit(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("line1\nline2\nline3\nline4\nline5\n")
            path = f.name
        try:
            result = await read_file(path, offset=1, limit=2)
            assert result["num_lines"] == 2
        finally:
            Path(path).unlink()

    @pytest.mark.asyncio
    async def test_read_nonexistent_file(self):
        with pytest.raises(FileNotFoundError):
            await read_file("/nonexistent/file.txt")


class TestWriteFile:
    @pytest.mark.asyncio
    async def test_write_new_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = str(Path(tmpdir) / "new_file.txt")
            result = await write_file(path, "hello world")
            assert result["status"] == "written"
            assert Path(path).read_text() == "hello world"

    @pytest.mark.asyncio
    async def test_write_creates_parent_dirs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = str(Path(tmpdir) / "sub" / "dir" / "file.txt")
            result = await write_file(path, "content")
            assert result["status"] == "written"
            assert Path(path).exists()

    @pytest.mark.asyncio
    async def test_overwrite_existing(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("old")
            path = f.name
        try:
            await write_file(path, "new")
            assert Path(path).read_text() == "new"
        finally:
            Path(path).unlink()


class TestEditFile:
    @pytest.mark.asyncio
    async def test_edit_replace(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("hello world")
            path = f.name
        try:
            result = await edit_file(path, "hello", "goodbye")
            assert result["status"] == "edited"
            assert Path(path).read_text() == "goodbye world"
        finally:
            Path(path).unlink()

    @pytest.mark.asyncio
    async def test_edit_replace_all(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("aaa bbb aaa")
            path = f.name
        try:
            result = await edit_file(path, "aaa", "ccc", replace_all=True)
            assert result["status"] == "edited"
            assert Path(path).read_text() == "ccc bbb ccc"
        finally:
            Path(path).unlink()

    @pytest.mark.asyncio
    async def test_edit_multiple_without_replace_all(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("aaa bbb aaa")
            path = f.name
        try:
            with pytest.raises(ValueError, match="Found 2 matches"):
                await edit_file(path, "aaa", "ccc")
        finally:
            Path(path).unlink()

    @pytest.mark.asyncio
    async def test_edit_string_not_found(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("hello")
            path = f.name
        try:
            with pytest.raises(ValueError, match="String not found"):
                await edit_file(path, "nonexistent", "new")
        finally:
            Path(path).unlink()

    @pytest.mark.asyncio
    async def test_edit_nonexistent_file(self):
        with pytest.raises(FileNotFoundError):
            await edit_file("/nonexistent/file.txt", "old", "new")


class TestGlobFiles:
    @pytest.mark.asyncio
    async def test_glob_finds_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "a.py").write_text("a")
            (Path(tmpdir) / "b.py").write_text("b")
            (Path(tmpdir) / "c.txt").write_text("c")

            result = await glob_files("*.py", tmpdir)
            assert result["num_files"] == 2
            assert result["truncated"] is False

    @pytest.mark.asyncio
    async def test_glob_no_matches(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = await glob_files("*.xyz", tmpdir)
            assert result["num_files"] == 0


class TestGrepFiles:
    @pytest.mark.asyncio
    async def test_grep_finds_matches(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "test.py").write_text("hello world\nfoo bar\nhello again")

            result = await grep_files("hello", tmpdir, "*.py")
            assert result["num_matches"] == 2

    @pytest.mark.asyncio
    async def test_grep_no_matches(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "test.py").write_text("hello world")

            result = await grep_files("nonexistent_pattern", tmpdir)
            assert result["num_matches"] == 0


# ── Shell Operations ──

class TestBash:
    @pytest.mark.asyncio
    async def test_simple_command(self):
        result = await bash("echo hello")
        assert result["exit_code"] == 0
        assert "hello" in result["stdout"]

    @pytest.mark.asyncio
    async def test_command_with_stderr(self):
        result = await bash("echo error >&2")
        assert result["exit_code"] == 0
        assert "error" in result["stderr"]

    @pytest.mark.asyncio
    async def test_failing_command(self):
        result = await bash("exit 1")
        assert result["exit_code"] == 1

    @pytest.mark.asyncio
    async def test_timeout(self):
        with pytest.raises(TimeoutError):
            await bash("sleep 10", timeout=100)


# ── Task Operations ──

class TestTaskOperations:
    @pytest.mark.asyncio
    async def test_task_create(self):
        # Reset global state
        import loom.tools.builtin.task_operations as task_mod
        task_mod._tasks.clear()
        task_mod._task_counter = 0

        result = await task_create("Test task", "A description")
        assert result["status"] == "created"
        assert "task_id" in result

    @pytest.mark.asyncio
    async def test_task_update(self):
        import loom.tools.builtin.task_operations as task_mod
        task_mod._tasks.clear()
        task_mod._task_counter = 0

        created = await task_create("Test", "Desc")
        task_id = created["task_id"]
        result = await task_update(task_id, "completed")
        assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_task_update_not_found(self):
        import loom.tools.builtin.task_operations as task_mod
        task_mod._tasks.clear()

        with pytest.raises(ValueError, match="Task not found"):
            await task_update("nonexistent", "done")

    @pytest.mark.asyncio
    async def test_task_list(self):
        import loom.tools.builtin.task_operations as task_mod
        task_mod._tasks.clear()
        task_mod._task_counter = 0

        await task_create("Task 1", "Desc 1")
        await task_create("Task 2", "Desc 2")
        result = await task_list()
        assert result["count"] == 2

    @pytest.mark.asyncio
    async def test_task_list_empty(self):
        import loom.tools.builtin.task_operations as task_mod
        task_mod._tasks.clear()
        task_mod._task_counter = 0

        result = await task_list()
        assert result["count"] == 0

    @pytest.mark.asyncio
    async def test_task_get(self):
        import loom.tools.builtin.task_operations as task_mod
        task_mod._tasks.clear()
        task_mod._task_counter = 0

        created = await task_create("My task", "Details here")
        task_id = created["task_id"]
        result = await task_get(task_id)
        assert result["subject"] == "My task"
        assert result["description"] == "Details here"
        assert result["status"] == "pending"

    @pytest.mark.asyncio
    async def test_task_get_not_found(self):
        import loom.tools.builtin.task_operations as task_mod
        task_mod._tasks.clear()

        with pytest.raises(ValueError, match="Task not found"):
            await task_get("nonexistent")


# ── Web Operations ──

class TestWebSearch:
    @pytest.mark.asyncio
    async def test_web_search_placeholder(self):
        result = await web_search("test query")
        assert result["query"] == "test query"
        assert result["results"] == []


# ── Agent Operations ──

class TestSpawnAgent:
    @pytest.mark.asyncio
    async def test_spawn(self):
        result = await spawn_agent("do something", depth=2)
        assert result["status"] == "spawned"
        assert result["depth"] == 2
        assert result["task"] == "do something"


class TestAskUser:
    @pytest.mark.asyncio
    async def test_ask_user(self):
        result = await ask_user("What to do?", ["a", "b"])
        assert result["question"] == "What to do?"
        assert result["options"] == ["a", "b"]
        assert result["answer"] is None


# ── MCP Operations ──

class TestMcpOperations:
    @pytest.mark.asyncio
    async def test_list_resources(self):
        result = await mcp_list_resources(server="test_server")
        assert result["server"] == "test_server"
        assert result["resources"] == []

    @pytest.mark.asyncio
    async def test_read_resource(self):
        result = await mcp_read_resource(server="s", uri="file:///test")
        assert result["server"] == "s"
        assert result["uri"] == "file:///test"

    @pytest.mark.asyncio
    async def test_call_tool(self):
        result = await mcp_call_tool(server="s", tool_name="t", arguments={"a": 1})
        assert result["server"] == "s"
        assert result["tool"] == "t"


# ── Skill Operations ──

class TestSkillOperations:
    @pytest.mark.asyncio
    async def test_skill_invoke(self):
        result = await skill_invoke("python_expert", args="debug this")
        assert result["skill"] == "python_expert"
        assert result["args"] == "debug this"
        assert result["result"] is None

    @pytest.mark.asyncio
    async def test_skill_discover(self):
        result = await skill_discover()
        assert result["skills"] == []


# ── Notebook Operations ──

class TestNotebookEdit:
    @pytest.mark.asyncio
    async def test_edit_cell(self):
        notebook = {
            "cells": [
                {"id": "cell_1", "source": ["old code"], "cell_type": "code"},
                {"id": "cell_2", "source": ["other"], "cell_type": "markdown"},
            ]
        }
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ipynb', delete=False) as f:
            json.dump(notebook, f)
            path = f.name

        try:
            result = await notebook_edit(path, "cell_1", "new code line 1\nnew code line 2")
            assert result["status"] == "edited"
            assert result["cell_id"] == "cell_1"

            with open(path) as f:
                updated = json.load(f)
            assert updated["cells"][0]["source"] == ["new code line 1", "new code line 2"]
        finally:
            Path(path).unlink()

    @pytest.mark.asyncio
    async def test_edit_cell_not_found(self):
        notebook = {"cells": [{"id": "cell_1", "source": ["code"]}]}
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ipynb', delete=False) as f:
            json.dump(notebook, f)
            path = f.name

        try:
            result = await notebook_edit(path, "nonexistent", "new code")
            # Cell not found, but no error raised (just no change)
            assert result["status"] == "edited"
        finally:
            Path(path).unlink()
