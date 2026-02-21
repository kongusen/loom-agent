"""Coverage-boost tests for tools/system.py."""

from loom.tools.system import (
    ListDirParams,
    ReadFileParams,
    ShellParams,
    WriteFileParams,
    _list_dir_exec,
    _read_file_exec,
    _shell_exec,
    _write_file_exec,
)
from loom.types import ToolContext


def _ctx():
    return ToolContext(agent_id="test")


class TestReadFileTool:
    async def test_read_file(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello world")
        result = await _read_file_exec(ReadFileParams(path=str(f)), _ctx())
        assert result["content"] == "hello world"


class TestWriteFileTool:
    async def test_write_file(self, tmp_path):
        f = tmp_path / "out.txt"
        result = await _write_file_exec(WriteFileParams(path=str(f), content="data"), _ctx())
        assert result["bytes"] == 4
        assert f.read_text() == "data"

    async def test_write_file_mkdirp(self, tmp_path):
        f = tmp_path / "sub" / "deep" / "out.txt"
        await _write_file_exec(WriteFileParams(path=str(f), content="nested"), _ctx())
        assert f.read_text() == "nested"


class TestListDirTool:
    async def test_list_dir(self, tmp_path):
        (tmp_path / "a.txt").write_text("a")
        (tmp_path / "sub").mkdir()
        result = await _list_dir_exec(ListDirParams(path=str(tmp_path)), _ctx())
        names = {e["name"] for e in result["entries"]}
        assert "a.txt" in names
        assert "sub" in names

    async def test_list_dir_recursive(self, tmp_path):
        (tmp_path / "sub").mkdir()
        (tmp_path / "sub" / "b.txt").write_text("b")
        result = await _list_dir_exec(ListDirParams(path=str(tmp_path), recursive=True), _ctx())
        assert len(result["entries"]) >= 2


class TestShellTool:
    async def test_shell_echo(self):
        result = await _shell_exec(ShellParams(command="echo hello"), _ctx())
        assert result["exitCode"] == 0
        assert "hello" in result["stdout"]
