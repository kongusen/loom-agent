"""
Extended tests for builtin tool modules: file.py, http.py, bash.py

Covers tool definition creation, execution, error handling, and edge cases.
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from loom.tools.builtin.bash import BashTool, create_bash_tool
from loom.tools.builtin.file import FileTools, create_file_tools
from loom.tools.builtin.http import HTTPTool, create_http_tool
from loom.tools.core.sandbox import Sandbox, SandboxViolation


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sandbox(tmp_path):
    """Create a real Sandbox rooted at tmp_path."""
    return Sandbox(tmp_path)


@pytest.fixture
def sandbox_with_file(sandbox, tmp_path):
    """Sandbox with a pre-existing file."""
    f = tmp_path / "hello.txt"
    f.write_text("hello world", encoding="utf-8")
    return sandbox


@pytest.fixture
def mock_sandbox():
    """A MagicMock sandbox for isolation tests."""
    sb = MagicMock(spec=Sandbox)
    sb.root_dir = "/fake/sandbox"
    return sb


# ===========================================================================
# FileTools
# ===========================================================================


class TestCreateFileTools:
    """Tests for create_file_tools definition factory."""

    def test_returns_three_tools(self, sandbox):
        tools = create_file_tools(sandbox)
        assert len(tools) == 3

    def test_tool_types(self, sandbox):
        tools = create_file_tools(sandbox)
        for t in tools:
            assert t["type"] == "function"

    def test_tool_names(self, sandbox):
        tools = create_file_tools(sandbox)
        names = [t["function"]["name"] for t in tools]
        assert "read_file" in names
        assert "write_file" in names
        assert "edit_file" in names

    def test_read_file_schema(self, sandbox):
        tools = create_file_tools(sandbox)
        read_tool = next(t for t in tools if t["function"]["name"] == "read_file")
        params = read_tool["function"]["parameters"]
        assert params["type"] == "object"
        assert "file_path" in params["properties"]
        assert params["required"] == ["file_path"]

    def test_write_file_schema(self, sandbox):
        tools = create_file_tools(sandbox)
        write_tool = next(t for t in tools if t["function"]["name"] == "write_file")
        params = write_tool["function"]["parameters"]
        assert "file_path" in params["properties"]
        assert "content" in params["properties"]
        assert set(params["required"]) == {"file_path", "content"}

    def test_edit_file_schema(self, sandbox):
        tools = create_file_tools(sandbox)
        edit_tool = next(t for t in tools if t["function"]["name"] == "edit_file")
        params = edit_tool["function"]["parameters"]
        assert "file_path" in params["properties"]
        assert "old_string" in params["properties"]
        assert "new_string" in params["properties"]
        assert set(params["required"]) == {"file_path", "old_string", "new_string"}

    def test_executors_are_callable(self, sandbox):
        tools = create_file_tools(sandbox)
        for t in tools:
            assert callable(t["_executor"])

    def test_description_contains_sandbox_root(self, sandbox):
        tools = create_file_tools(sandbox)
        for t in tools:
            assert str(sandbox.root_dir) in t["function"]["description"]


class TestFileToolsReadFile:
    """Tests for FileTools.read_file execution."""

    async def test_read_existing_file(self, sandbox_with_file):
        ft = FileTools(sandbox_with_file)
        result = await ft.read_file("hello.txt")
        assert result["success"] == "true"
        assert result["content"] == "hello world"

    async def test_read_file_not_found(self, sandbox):
        ft = FileTools(sandbox)
        result = await ft.read_file("nonexistent.txt")
        assert result["success"] == "false"
        assert "not found" in result["error"].lower()

    async def test_read_file_sandbox_violation(self, mock_sandbox):
        mock_sandbox.safe_read.side_effect = SandboxViolation("outside sandbox")
        ft = FileTools(mock_sandbox)
        result = await ft.read_file("../../etc/passwd")
        assert result["success"] == "false"
        assert "sandbox violation" in result["error"].lower()

    async def test_read_file_generic_error(self, mock_sandbox):
        mock_sandbox.safe_read.side_effect = PermissionError("permission denied")
        ft = FileTools(mock_sandbox)
        result = await ft.read_file("secret.txt")
        assert result["success"] == "false"
        assert "read error" in result["error"].lower()

    async def test_read_file_empty_content(self, sandbox, tmp_path):
        (tmp_path / "empty.txt").write_text("", encoding="utf-8")
        ft = FileTools(sandbox)
        result = await ft.read_file("empty.txt")
        assert result["success"] == "true"
        assert result["content"] == ""


class TestFileToolsWriteFile:
    """Tests for FileTools.write_file execution."""

    async def test_write_new_file(self, sandbox, tmp_path):
        ft = FileTools(sandbox)
        result = await ft.write_file("output.txt", "data")
        assert result["success"] == "true"
        assert (tmp_path / "output.txt").read_text(encoding="utf-8") == "data"

    async def test_write_creates_parent_dirs(self, sandbox, tmp_path):
        ft = FileTools(sandbox)
        result = await ft.write_file("sub/dir/file.txt", "nested")
        assert result["success"] == "true"
        assert (tmp_path / "sub" / "dir" / "file.txt").read_text(encoding="utf-8") == "nested"

    async def test_write_overwrites_existing(self, sandbox_with_file, tmp_path):
        ft = FileTools(sandbox_with_file)
        result = await ft.write_file("hello.txt", "overwritten")
        assert result["success"] == "true"
        assert (tmp_path / "hello.txt").read_text(encoding="utf-8") == "overwritten"

    async def test_write_sandbox_violation(self, mock_sandbox):
        mock_sandbox.safe_write.side_effect = SandboxViolation("outside sandbox")
        ft = FileTools(mock_sandbox)
        result = await ft.write_file("/etc/passwd", "bad")
        assert result["success"] == "false"
        assert "sandbox violation" in result["error"].lower()

    async def test_write_generic_error(self, mock_sandbox):
        mock_sandbox.safe_write.side_effect = OSError("disk full")
        ft = FileTools(mock_sandbox)
        result = await ft.write_file("file.txt", "data")
        assert result["success"] == "false"
        assert "write error" in result["error"].lower()

    async def test_write_empty_content(self, sandbox, tmp_path):
        ft = FileTools(sandbox)
        result = await ft.write_file("blank.txt", "")
        assert result["success"] == "true"
        assert (tmp_path / "blank.txt").read_text(encoding="utf-8") == ""


class TestFileToolsEditFile:
    """Tests for FileTools.edit_file execution."""

    async def test_edit_replaces_string(self, sandbox_with_file, tmp_path):
        ft = FileTools(sandbox_with_file)
        result = await ft.edit_file("hello.txt", "world", "universe")
        assert result["success"] == "true"
        assert result["replacements"] == "1"
        assert (tmp_path / "hello.txt").read_text(encoding="utf-8") == "hello universe"

    async def test_edit_multiple_occurrences(self, sandbox, tmp_path):
        (tmp_path / "repeat.txt").write_text("aaa", encoding="utf-8")
        ft = FileTools(sandbox)
        result = await ft.edit_file("repeat.txt", "a", "b")
        assert result["success"] == "true"
        assert result["replacements"] == "3"
        assert (tmp_path / "repeat.txt").read_text(encoding="utf-8") == "bbb"

    async def test_edit_string_not_found(self, sandbox_with_file):
        ft = FileTools(sandbox_with_file)
        result = await ft.edit_file("hello.txt", "nonexistent", "replacement")
        assert result["success"] == "false"
        assert "not found" in result["error"].lower()

    async def test_edit_file_not_found(self, sandbox):
        ft = FileTools(sandbox)
        result = await ft.edit_file("missing.txt", "a", "b")
        assert result["success"] == "false"
        assert "not found" in result["error"].lower()

    async def test_edit_sandbox_violation(self, mock_sandbox):
        mock_sandbox.safe_read.side_effect = SandboxViolation("outside sandbox")
        ft = FileTools(mock_sandbox)
        result = await ft.edit_file("../../etc/passwd", "root", "hacked")
        assert result["success"] == "false"
        assert "sandbox violation" in result["error"].lower()

    async def test_edit_generic_error(self, mock_sandbox):
        mock_sandbox.safe_read.side_effect = IOError("read failure")
        ft = FileTools(mock_sandbox)
        result = await ft.edit_file("file.txt", "a", "b")
        assert result["success"] == "false"
        assert "edit error" in result["error"].lower()

    async def test_edit_empty_old_string_replaces(self, sandbox_with_file, tmp_path):
        """Empty old_string matches everywhere (Python str.replace behaviour)."""
        ft = FileTools(sandbox_with_file)
        result = await ft.edit_file("hello.txt", "", "X")
        assert result["success"] == "true"
        # str.replace("", "X") inserts X between every char and at boundaries
        content = (tmp_path / "hello.txt").read_text(encoding="utf-8")
        assert "X" in content


# ===========================================================================
# HTTPTool
# ===========================================================================


class TestCreateHTTPTool:
    """Tests for create_http_tool definition factory."""

    def test_tool_type(self):
        tool = create_http_tool()
        assert tool["type"] == "function"

    def test_tool_name(self):
        tool = create_http_tool()
        assert tool["function"]["name"] == "http_request"

    def test_tool_schema_required(self):
        tool = create_http_tool()
        params = tool["function"]["parameters"]
        assert params["required"] == ["url"]

    def test_tool_schema_properties(self):
        tool = create_http_tool()
        props = tool["function"]["parameters"]["properties"]
        assert "url" in props
        assert "method" in props
        assert "headers" in props
        assert "body" in props

    def test_method_enum(self):
        tool = create_http_tool()
        method_prop = tool["function"]["parameters"]["properties"]["method"]
        assert set(method_prop["enum"]) == {"GET", "POST", "PUT", "DELETE", "PATCH"}

    def test_custom_timeout_in_description(self):
        tool = create_http_tool(timeout=60.0)
        assert "60.0" in tool["function"]["description"]

    def test_executor_is_callable(self):
        tool = create_http_tool()
        assert callable(tool["_executor"])


class TestHTTPToolInit:
    """Tests for HTTPTool.__init__."""

    def test_default_timeout(self):
        tool = HTTPTool()
        assert tool.timeout == 30.0

    def test_custom_timeout(self):
        tool = HTTPTool(timeout=120.0)
        assert tool.timeout == 120.0


class TestHTTPToolRequest:
    """Tests for HTTPTool.request execution."""

    async def test_successful_get(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.text = '{"ok": true}'

        mock_client = AsyncMock()
        mock_client.request.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        tool = HTTPTool()
        with patch("loom.tools.builtin.http.httpx") as mock_httpx:
            mock_httpx.AsyncClient.return_value = mock_client
            mock_httpx.TimeoutException = Exception
            result = await tool.request("https://example.com")

        assert result["success"] == "true"
        assert result["status_code"] == "200"
        assert result["body"] == '{"ok": true}'

    async def test_post_with_json_body(self):
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.headers = {}
        mock_response.text = "created"

        mock_client = AsyncMock()
        mock_client.request.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        tool = HTTPTool()
        body = json.dumps({"key": "value"})
        with patch("loom.tools.builtin.http.httpx") as mock_httpx:
            mock_httpx.AsyncClient.return_value = mock_client
            mock_httpx.TimeoutException = Exception
            result = await tool.request(
                "https://example.com/api",
                method="POST",
                headers={"Authorization": "Bearer token"},
                body=body,
            )

        assert result["success"] == "true"
        assert result["status_code"] == "201"
        # Verify json kwarg was used (not content)
        call_kwargs = mock_client.request.call_args[1]
        assert call_kwargs["json"] == {"key": "value"}

    async def test_post_with_non_json_body(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.text = "ok"

        mock_client = AsyncMock()
        mock_client.request.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        tool = HTTPTool()
        with patch("loom.tools.builtin.http.httpx") as mock_httpx:
            mock_httpx.AsyncClient.return_value = mock_client
            mock_httpx.TimeoutException = Exception
            result = await tool.request(
                "https://example.com",
                method="POST",
                body="plain text body, not json",
            )

        assert result["success"] == "true"
        call_kwargs = mock_client.request.call_args[1]
        assert call_kwargs["content"] == "plain text body, not json"
        assert "json" not in call_kwargs

    async def test_4xx_response_is_not_success(self):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.headers = {}
        mock_response.text = "Not Found"

        mock_client = AsyncMock()
        mock_client.request.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        tool = HTTPTool()
        with patch("loom.tools.builtin.http.httpx") as mock_httpx:
            mock_httpx.AsyncClient.return_value = mock_client
            mock_httpx.TimeoutException = Exception
            result = await tool.request("https://example.com/missing")

        assert result["success"] == "false"
        assert result["status_code"] == "404"

    async def test_5xx_response_is_not_success(self):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.headers = {}
        mock_response.text = "Internal Server Error"

        mock_client = AsyncMock()
        mock_client.request.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        tool = HTTPTool()
        with patch("loom.tools.builtin.http.httpx") as mock_httpx:
            mock_httpx.AsyncClient.return_value = mock_client
            mock_httpx.TimeoutException = Exception
            result = await tool.request("https://example.com/error")

        assert result["success"] == "false"
        assert result["status_code"] == "500"

    async def test_timeout_error(self):
        tool = HTTPTool(timeout=5.0)

        with patch("loom.tools.builtin.http.httpx") as mock_httpx:
            timeout_exc_class = type("TimeoutException", (Exception,), {})
            mock_httpx.TimeoutException = timeout_exc_class

            mock_client = AsyncMock()
            mock_client.request.side_effect = timeout_exc_class("timed out")
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_httpx.AsyncClient.return_value = mock_client

            result = await tool.request("https://slow.example.com")

        assert result["success"] == "false"
        assert "timed out" in result["error"].lower()

    async def test_generic_request_error(self):
        tool = HTTPTool()

        with patch("loom.tools.builtin.http.httpx") as mock_httpx:
            timeout_exc_class = type("TimeoutException", (Exception,), {})
            mock_httpx.TimeoutException = timeout_exc_class

            mock_client = AsyncMock()
            mock_client.request.side_effect = ConnectionError("connection refused")
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_httpx.AsyncClient.return_value = mock_client

            result = await tool.request("https://down.example.com")

        assert result["success"] == "false"
        assert "http request error" in result["error"].lower()

    async def test_httpx_not_available(self):
        tool = HTTPTool()
        with patch("loom.tools.builtin.http.HTTPX_AVAILABLE", False):
            result = await tool.request("https://example.com")

        assert result["success"] == "false"
        assert "httpx" in result["error"].lower()

    async def test_custom_timeout_per_request(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.text = "ok"

        mock_client = AsyncMock()
        mock_client.request.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        tool = HTTPTool(timeout=10.0)
        with patch("loom.tools.builtin.http.httpx") as mock_httpx:
            mock_httpx.AsyncClient.return_value = mock_client
            mock_httpx.TimeoutException = Exception
            await tool.request("https://example.com", timeout=60.0)

        # AsyncClient was called with the per-request timeout
        mock_httpx.AsyncClient.assert_called_once_with(timeout=60.0)

    async def test_method_uppercased(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.text = "ok"

        mock_client = AsyncMock()
        mock_client.request.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        tool = HTTPTool()
        with patch("loom.tools.builtin.http.httpx") as mock_httpx:
            mock_httpx.AsyncClient.return_value = mock_client
            mock_httpx.TimeoutException = Exception
            await tool.request("https://example.com", method="delete")

        call_kwargs = mock_client.request.call_args[1]
        assert call_kwargs["method"] == "DELETE"

    async def test_no_headers_or_body(self):
        """When headers and body are None, they should not appear in kwargs."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.text = ""

        mock_client = AsyncMock()
        mock_client.request.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        tool = HTTPTool()
        with patch("loom.tools.builtin.http.httpx") as mock_httpx:
            mock_httpx.AsyncClient.return_value = mock_client
            mock_httpx.TimeoutException = Exception
            await tool.request("https://example.com")

        call_kwargs = mock_client.request.call_args[1]
        assert "headers" not in call_kwargs
        assert "json" not in call_kwargs
        assert "content" not in call_kwargs


# ===========================================================================
# BashTool
# ===========================================================================


class TestCreateBashTool:
    """Tests for create_bash_tool definition factory."""

    def test_tool_type(self, sandbox):
        tool = create_bash_tool(sandbox)
        assert tool["type"] == "function"

    def test_tool_name(self, sandbox):
        tool = create_bash_tool(sandbox)
        assert tool["function"]["name"] == "bash"

    def test_tool_schema(self, sandbox):
        tool = create_bash_tool(sandbox)
        params = tool["function"]["parameters"]
        assert params["type"] == "object"
        assert "command" in params["properties"]
        assert params["required"] == ["command"]

    def test_description_contains_sandbox_root(self, sandbox):
        tool = create_bash_tool(sandbox)
        assert str(sandbox.root_dir) in tool["function"]["description"]

    def test_description_contains_timeout(self, sandbox):
        tool = create_bash_tool(sandbox, timeout=45.0)
        assert "45.0" in tool["function"]["description"]

    def test_executor_is_callable(self, sandbox):
        tool = create_bash_tool(sandbox)
        assert callable(tool["_executor"])


class TestBashToolInit:
    """Tests for BashTool.__init__."""

    def test_default_timeout(self, sandbox):
        bt = BashTool(sandbox)
        assert bt.timeout == 30.0

    def test_custom_timeout(self, sandbox):
        bt = BashTool(sandbox, timeout=120.0)
        assert bt.timeout == 120.0

    def test_sandbox_stored(self, sandbox):
        bt = BashTool(sandbox)
        assert bt.sandbox is sandbox


class TestBashToolExecute:
    """Tests for BashTool.execute."""

    async def test_simple_echo(self, sandbox):
        bt = BashTool(sandbox)
        result = await bt.execute("echo hello")
        assert result["success"] == "true"
        assert result["stdout"].strip() == "hello"
        assert result["returncode"] == "0"

    async def test_command_with_stderr(self, sandbox):
        bt = BashTool(sandbox)
        result = await bt.execute("echo error >&2")
        assert "error" in result["stderr"]

    async def test_failing_command(self, sandbox):
        bt = BashTool(sandbox)
        result = await bt.execute("exit 1")
        assert result["success"] == "false"
        assert result["returncode"] == "1"

    async def test_nonzero_exit_code(self, sandbox):
        bt = BashTool(sandbox)
        result = await bt.execute("exit 42")
        assert result["success"] == "false"
        assert result["returncode"] == "42"

    async def test_timeout(self, sandbox):
        bt = BashTool(sandbox, timeout=0.5)
        result = await bt.execute("sleep 10")
        assert result["success"] == "false"
        assert "timed out" in result["stderr"].lower()
        assert result["returncode"] == "-1"

    async def test_per_call_timeout(self, sandbox):
        bt = BashTool(sandbox, timeout=60.0)
        result = await bt.execute("sleep 10", timeout=0.5)
        assert result["success"] == "false"
        assert "timed out" in result["stderr"].lower()

    async def test_working_directory_is_sandbox_root(self, sandbox):
        bt = BashTool(sandbox)
        result = await bt.execute("pwd")
        assert result["success"] == "true"
        assert result["stdout"].strip() == str(sandbox.root_dir)

    async def test_multiline_output(self, sandbox):
        bt = BashTool(sandbox)
        result = await bt.execute("echo line1; echo line2; echo line3")
        assert result["success"] == "true"
        lines = result["stdout"].strip().split("\n")
        assert len(lines) == 3

    async def test_empty_command(self, sandbox):
        bt = BashTool(sandbox)
        result = await bt.execute("")
        # Empty command should succeed with empty output
        assert result["returncode"] == "0"

    async def test_command_with_special_characters(self, sandbox):
        bt = BashTool(sandbox)
        result = await bt.execute("echo 'hello \"world\"'")
        assert result["success"] == "true"
        assert 'hello "world"' in result["stdout"]

    async def test_pipe_command(self, sandbox):
        bt = BashTool(sandbox)
        result = await bt.execute("echo 'abc' | tr 'a' 'x'")
        assert result["success"] == "true"
        assert result["stdout"].strip() == "xbc"

    async def test_execution_error_handled(self, sandbox):
        """Simulate an exception during subprocess creation."""
        bt = BashTool(sandbox)
        with patch("asyncio.create_subprocess_shell", side_effect=OSError("spawn failed")):
            result = await bt.execute("echo test")
        assert result["success"] == "false"
        assert "execution error" in result["stderr"].lower()
        assert result["returncode"] == "-1"


# ===========================================================================
# register_*_to_manager functions
# ===========================================================================


class TestRegisterFileToolsToManager:
    """Tests for register_file_tools_to_manager."""

    async def test_registers_three_tools(self, sandbox):
        from loom.tools.builtin.file import register_file_tools_to_manager

        manager = AsyncMock()
        manager.sandbox = sandbox
        await register_file_tools_to_manager(manager)
        assert manager.register_tool.call_count == 3
        registered_names = [call.args[0] for call in manager.register_tool.call_args_list]
        assert "read_file" in registered_names
        assert "write_file" in registered_names
        assert "edit_file" in registered_names

    async def test_raises_when_manager_unavailable(self):
        from loom.tools.builtin.file import register_file_tools_to_manager

        with patch("loom.tools.builtin.file.SandboxToolManager", None), patch(
            "loom.tools.builtin.file.ToolScope", None
        ):
            with pytest.raises(ImportError):
                await register_file_tools_to_manager(MagicMock())


class TestRegisterHTTPToolToManager:
    """Tests for register_http_tool_to_manager."""

    async def test_registers_http_tool(self):
        from loom.tools.builtin.http import register_http_tool_to_manager

        manager = AsyncMock()
        await register_http_tool_to_manager(manager, timeout=15.0)
        manager.register_tool.assert_called_once()
        assert manager.register_tool.call_args.args[0] == "http_request"

    async def test_raises_when_manager_unavailable(self):
        from loom.tools.builtin.http import register_http_tool_to_manager

        with patch("loom.tools.builtin.http.SandboxToolManager", None), patch(
            "loom.tools.builtin.http.ToolScope", None
        ):
            with pytest.raises(ImportError):
                await register_http_tool_to_manager(MagicMock())


class TestRegisterBashToolToManager:
    """Tests for register_bash_tool_to_manager."""

    async def test_registers_bash_tool(self, sandbox):
        from loom.tools.builtin.bash import register_bash_tool_to_manager

        manager = AsyncMock()
        manager.sandbox = sandbox
        await register_bash_tool_to_manager(manager, timeout=20.0)
        manager.register_tool.assert_called_once()
        assert manager.register_tool.call_args.args[0] == "bash"

    async def test_raises_when_manager_unavailable(self):
        from loom.tools.builtin.bash import register_bash_tool_to_manager

        with patch("loom.tools.builtin.bash.SandboxToolManager", None), patch(
            "loom.tools.builtin.bash.ToolScope", None
        ):
            with pytest.raises(ImportError):
                await register_bash_tool_to_manager(MagicMock())
