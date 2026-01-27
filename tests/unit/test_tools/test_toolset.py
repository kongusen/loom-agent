"""
Tests for Toolset
"""

import pytest

from loom.tools.toolset import (
    create_coding_toolset,
    create_minimal_toolset,
    create_sandbox_toolset,
    create_web_toolset,
)


class TestCreateSandboxToolset:
    """Test suite for create_sandbox_toolset"""

    @pytest.fixture
    def sandbox_dir(self, tmp_path):
        """Create a temporary sandbox directory"""
        return tmp_path / "sandbox"

    def test_create_full_toolset(self, sandbox_dir):
        """Test creating full toolset with all tools"""
        tools = create_sandbox_toolset(sandbox_dir)

        # Should have all tools: bash, files (3), search (2), todo, http, done
        # bash=1, file_operations=3, search=2, todo=1, http=1, done=1
        assert len(tools) == 9

    def test_create_toolset_without_bash(self, sandbox_dir):
        """Test creating toolset without bash"""
        tools = create_sandbox_toolset(sandbox_dir, include_bash=False)

        # Should have: files (3), search (2), todo, http, done = 8
        assert len(tools) == 8

    def test_create_toolset_without_files(self, sandbox_dir):
        """Test creating toolset without file operations"""
        tools = create_sandbox_toolset(sandbox_dir, include_files=False)

        # Should have: bash, search (2), todo, http, done = 6
        assert len(tools) == 6

    def test_create_toolset_without_search(self, sandbox_dir):
        """Test creating toolset without search"""
        tools = create_sandbox_toolset(sandbox_dir, include_search=False)

        # Should have: bash, files (3), todo, http, done = 7
        assert len(tools) == 7

    def test_create_toolset_without_todo(self, sandbox_dir):
        """Test creating toolset without todo"""
        tools = create_sandbox_toolset(sandbox_dir, include_todo=False)

        # Should have: bash, files (3), search (2), http, done = 8
        assert len(tools) == 8

    def test_create_toolset_without_http(self, sandbox_dir):
        """Test creating toolset without HTTP"""
        tools = create_sandbox_toolset(sandbox_dir, include_http=False)

        # Should have: bash, files (3), search (2), todo, done = 8
        assert len(tools) == 8

    def test_create_toolset_without_done(self, sandbox_dir):
        """Test creating toolset without done"""
        tools = create_sandbox_toolset(sandbox_dir, include_done=False)

        # Should have: bash, files (3), search (2), todo, http = 8
        assert len(tools) == 8

    def test_create_toolset_only_done(self, sandbox_dir):
        """Test creating toolset with only done tool"""
        tools = create_sandbox_toolset(
            sandbox_dir,
            include_bash=False,
            include_files=False,
            include_search=False,
            include_todo=False,
            include_http=False,
            include_done=True,
        )

        assert len(tools) == 1
        assert tools[0]["function"]["name"] == "done"

    def test_create_toolset_with_custom_timeouts(self, sandbox_dir):
        """Test creating toolset with custom timeouts"""
        tools = create_sandbox_toolset(sandbox_dir, bash_timeout=60.0, http_timeout=120.0)

        # Should create without errors
        assert len(tools) > 0

    def test_create_toolset_with_path_object(self, tmp_path):
        """Test creating toolset with Path object"""
        tools = create_sandbox_toolset(tmp_path)

        assert len(tools) > 0

    def test_create_toolset_auto_create_sandbox(self, tmp_path):
        """Test auto_create_sandbox parameter"""
        sandbox_dir = tmp_path / "new_sandbox"
        assert not sandbox_dir.exists()

        # With auto_create=True (default)
        tools = create_sandbox_toolset(sandbox_dir, auto_create_sandbox=True)

        assert sandbox_dir.exists()
        assert len(tools) > 0

    def test_create_toolset_no_auto_create(self, tmp_path):
        """Test with auto_create_sandbox=False"""
        sandbox_dir = tmp_path / "no_auto_sandbox"
        sandbox_dir.mkdir()  # Create it manually since auto_create=False

        # Should work with existing directory
        tools = create_sandbox_toolset(sandbox_dir, auto_create_sandbox=False)

        assert len(tools) > 0

    def test_tool_names(self, sandbox_dir):
        """Test that expected tool names are present"""
        tools = create_sandbox_toolset(sandbox_dir)
        tool_names = [t["function"]["name"] for t in tools]

        assert "bash" in tool_names
        assert "done" in tool_names
        # HTTP and todo tools might have different names
        assert any("http" in name.lower() for name in tool_names)
        assert any("todo" in name.lower() for name in tool_names)


class TestCreateMinimalToolset:
    """Test suite for create_minimal_toolset"""

    def test_create_minimal_toolset(self, tmp_path):
        """Test creating minimal toolset"""
        tools = create_minimal_toolset(tmp_path)

        # Should have: files (3) + done = 4
        assert len(tools) == 4

    def test_minimal_toolset_has_done(self, tmp_path):
        """Test minimal toolset includes done tool"""
        tools = create_minimal_toolset(tmp_path)
        tool_names = [t["function"]["name"] for t in tools]

        assert "done" in tool_names

    def test_minimal_toolset_no_bash(self, tmp_path):
        """Test minimal toolset excludes bash"""
        tools = create_minimal_toolset(tmp_path)
        tool_names = [t["function"]["name"] for t in tools]

        # bash should not be in minimal toolset
        assert "bash" not in tool_names


class TestCreateCodingToolset:
    """Test suite for create_coding_toolset"""

    def test_create_coding_toolset(self, tmp_path):
        """Test creating coding toolset"""
        tools = create_coding_toolset(tmp_path)

        # Should have: bash, files (3), search (2), done = 7
        assert len(tools) == 7

    def test_coding_toolset_has_bash(self, tmp_path):
        """Test coding toolset includes bash"""
        tools = create_coding_toolset(tmp_path)
        tool_names = [t["function"]["name"] for t in tools]

        assert "bash" in tool_names

    def test_coding_toolset_has_search(self, tmp_path):
        """Test coding toolset includes search"""
        tools = create_coding_toolset(tmp_path)
        tool_names = [t["function"]["name"] for t in tools]

        # Search tools include glob and grep
        assert "glob" in tool_names or "grep" in tool_names

    def test_coding_toolset_no_todo(self, tmp_path):
        """Test coding toolset excludes todo"""
        tools = create_coding_toolset(tmp_path)
        tool_names = [t["function"]["name"] for t in tools]

        # todo tools should not be in coding toolset
        assert not any("todo" in name.lower() for name in tool_names)


class TestCreateWebToolset:
    """Test suite for create_web_toolset"""

    def test_create_web_toolset(self, tmp_path):
        """Test creating web toolset"""
        tools = create_web_toolset(tmp_path)

        # Should have: files (3), http, done = 5
        assert len(tools) == 5

    def test_web_toolset_has_http(self, tmp_path):
        """Test web toolset includes HTTP"""
        tools = create_web_toolset(tmp_path)
        tool_names = [t["function"]["name"] for t in tools]

        # HTTP tool might have different name
        assert any("http" in name.lower() for name in tool_names)

    def test_web_toolset_no_bash(self, tmp_path):
        """Test web toolset excludes bash"""
        tools = create_web_toolset(tmp_path)
        tool_names = [t["function"]["name"] for t in tools]

        assert "bash" not in tool_names

    def test_web_toolset_no_search(self, tmp_path):
        """Test web toolset excludes search"""
        tools = create_web_toolset(tmp_path)
        tool_names = [t["function"]["name"] for t in tools]

        # glob and grep should not be in web toolset
        assert "glob" not in tool_names
        assert "grep" not in tool_names
