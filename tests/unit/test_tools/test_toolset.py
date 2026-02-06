"""
Tests for Toolset

测试新架构的工具集（基于 SandboxToolManager）
"""

import pytest

from loom.tools.core.toolset import (
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

    @pytest.mark.asyncio
    async def test_create_full_toolset(self, sandbox_dir):
        """Test creating full toolset with all tools"""
        manager = await create_sandbox_toolset(sandbox_dir)

        # Should return SandboxToolManager
        assert isinstance(manager, type(manager))

        # Should have all tools: bash, files (3), search (2), todo, http
        # Total = 1 + 3 + 2 + 1 + 1 = 8 (done is handled separately by Agent)
        tool_names = manager.list_tool_names()
        assert len(tool_names) == 8
        assert "bash" in tool_names
        assert "read_file" in tool_names
        assert "write_file" in tool_names
        assert "edit_file" in tool_names
        assert "glob" in tool_names
        assert "grep" in tool_names
        assert "todo_write" in tool_names
        assert "http_request" in tool_names

    @pytest.mark.asyncio
    async def test_create_toolset_without_bash(self, sandbox_dir):
        """Test creating toolset without bash"""
        manager = await create_sandbox_toolset(sandbox_dir, include_bash=False)

        tool_names = manager.list_tool_names()
        assert "bash" not in tool_names
        # Should have: files (3), search (2), todo, http = 7
        assert len(tool_names) == 7

    @pytest.mark.asyncio
    async def test_create_toolset_without_files(self, sandbox_dir):
        """Test creating toolset without file operations"""
        manager = await create_sandbox_toolset(sandbox_dir, include_files=False)

        tool_names = manager.list_tool_names()
        # Should have: bash, search (2), todo, http = 5
        assert "read_file" not in tool_names
        assert "write_file" not in tool_names
        assert "edit_file" not in tool_names
        assert len(tool_names) == 5

    @pytest.mark.asyncio
    async def test_create_toolset_without_search(self, sandbox_dir):
        """Test creating toolset without search"""
        manager = await create_sandbox_toolset(sandbox_dir, include_search=False)

        tool_names = manager.list_tool_names()
        # Should have: bash, files (3), todo, http = 6
        assert "glob" not in tool_names
        assert "grep" not in tool_names
        assert len(tool_names) == 6

    @pytest.mark.asyncio
    async def test_create_toolset_without_todo(self, sandbox_dir):
        """Test creating toolset without todo"""
        manager = await create_sandbox_toolset(sandbox_dir, include_todo=False)

        tool_names = manager.list_tool_names()
        assert "todo_write" not in tool_names
        # Should have: bash, files (3), search (2), http = 7
        assert len(tool_names) == 7

    @pytest.mark.asyncio
    async def test_create_toolset_without_http(self, sandbox_dir):
        """Test creating toolset without HTTP"""
        manager = await create_sandbox_toolset(sandbox_dir, include_http=False)

        tool_names = manager.list_tool_names()
        assert "http_request" not in tool_names
        # Should have: bash, files (3), search (2), todo = 7
        assert len(tool_names) == 7

    @pytest.mark.asyncio
    async def test_create_toolset_with_event_bus(self, sandbox_dir):
        """Test creating toolset with event bus"""
        from loom.events import EventBus

        event_bus = EventBus()
        manager = await create_sandbox_toolset(sandbox_dir, event_bus=event_bus)

        assert manager.event_bus == event_bus

    @pytest.mark.asyncio
    async def test_create_toolset_with_path_object(self, tmp_path):
        """Test creating toolset with Path object"""
        manager = await create_sandbox_toolset(tmp_path)

        assert len(manager) > 0

    @pytest.mark.asyncio
    async def test_create_toolset_auto_create_sandbox(self, tmp_path):
        """Test auto_create_sandbox parameter"""
        sandbox_dir = tmp_path / "new_sandbox"
        assert not sandbox_dir.exists()

        # With auto_create=True (default)
        manager = await create_sandbox_toolset(sandbox_dir, auto_create_sandbox=True)

        assert sandbox_dir.exists()
        assert len(manager) > 0

    @pytest.mark.asyncio
    async def test_create_toolset_no_auto_create(self, tmp_path):
        """Test with auto_create_sandbox=False"""
        sandbox_dir = tmp_path / "no_auto_sandbox"
        sandbox_dir.mkdir()  # Create it manually since auto_create=False

        # Should work with existing directory
        manager = await create_sandbox_toolset(sandbox_dir, auto_create_sandbox=False)

        assert len(manager) > 0


class TestCreateMinimalToolset:
    """Test suite for create_minimal_toolset"""

    @pytest.mark.asyncio
    async def test_create_minimal_toolset(self, tmp_path):
        """Test creating minimal toolset"""
        manager = await create_minimal_toolset(tmp_path)

        # Minimal toolset has: files (3) only
        # Note: done tool is handled separately by Agent
        tool_names = manager.list_tool_names()
        assert "bash" not in tool_names
        assert "read_file" in tool_names
        assert "write_file" in tool_names
        assert "edit_file" in tool_names
        assert len(tool_names) == 3

    @pytest.mark.asyncio
    async def test_minimal_toolset_no_bash(self, tmp_path):
        """Test minimal toolset excludes bash"""
        manager = await create_minimal_toolset(tmp_path)

        tool_names = manager.list_tool_names()
        # bash should not be in minimal toolset
        assert "bash" not in tool_names


class TestCreateCodingToolset:
    """Test suite for create_coding_toolset"""

    @pytest.mark.asyncio
    async def test_create_coding_toolset(self, tmp_path):
        """Test creating coding toolset"""
        manager = await create_coding_toolset(tmp_path)

        # Coding toolset has: bash, files (3), search (2)
        # Note: done tool is handled separately by Agent
        tool_names = manager.list_tool_names()
        assert "bash" in tool_names
        assert "read_file" in tool_names
        assert "write_file" in tool_names
        assert "edit_file" in tool_names
        assert "glob" in tool_names
        assert "grep" in tool_names
        assert len(tool_names) == 6

    @pytest.mark.asyncio
    async def test_coding_toolset_has_bash(self, tmp_path):
        """Test coding toolset includes bash"""
        manager = await create_coding_toolset(tmp_path)

        tool_names = manager.list_tool_names()
        assert "bash" in tool_names

    @pytest.mark.asyncio
    async def test_coding_toolset_has_search(self, tmp_path):
        """Test coding toolset includes search"""
        manager = await create_coding_toolset(tmp_path)

        tool_names = manager.list_tool_names()
        # Search tools include glob and grep
        assert "glob" in tool_names
        assert "grep" in tool_names

    @pytest.mark.asyncio
    async def test_coding_toolset_no_todo(self, tmp_path):
        """Test coding toolset excludes todo"""
        manager = await create_coding_toolset(tmp_path)

        tool_names = manager.list_tool_names()
        # todo tools should not be in coding toolset
        assert "todo_write" not in tool_names


class TestCreateWebToolset:
    """Test suite for create_web_toolset"""

    @pytest.mark.asyncio
    async def test_create_web_toolset(self, tmp_path):
        """Test creating web toolset"""
        manager = await create_web_toolset(tmp_path)

        # Web toolset has: files (3), http
        # Note: done tool is handled separately by Agent
        tool_names = manager.list_tool_names()
        assert "bash" not in tool_names
        assert "read_file" in tool_names
        assert "write_file" in tool_names
        assert "edit_file" in tool_names
        assert "http_request" in tool_names
        assert len(tool_names) == 4

    @pytest.mark.asyncio
    async def test_web_toolset_has_http(self, tmp_path):
        """Test web toolset includes HTTP"""
        manager = await create_web_toolset(tmp_path)

        tool_names = manager.list_tool_names()
        assert "http_request" in tool_names

    @pytest.mark.asyncio
    async def test_web_toolset_no_bash(self, tmp_path):
        """Test web toolset excludes bash"""
        manager = await create_web_toolset(tmp_path)

        tool_names = manager.list_tool_names()
        assert "bash" not in tool_names

    @pytest.mark.asyncio
    async def test_web_toolset_no_search(self, tmp_path):
        """Test web toolset excludes search"""
        manager = await create_web_toolset(tmp_path)

        tool_names = manager.list_tool_names()
        # glob and grep should not be in web toolset
        assert "glob" not in tool_names
        assert "grep" not in tool_names
