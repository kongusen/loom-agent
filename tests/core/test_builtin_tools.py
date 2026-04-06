"""Test builtin tools"""

import pytest
from loom.tools.builtin.tools_file import READ_TOOL, WRITE_TOOL, EDIT_TOOL, GLOB_TOOL, GREP_TOOL
from loom.tools.builtin.tools_shell_web import BASH_TOOL, WEB_FETCH_TOOL, WEB_SEARCH_TOOL
from loom.tools.builtin.tools_agent_task import TASK_TOOL, ASK_USER_TOOL
from loom.tools.schema import Tool


class TestBuiltinTools:
    """Test builtin tools"""

    def test_read_tool(self):
        """Test READ_TOOL"""
        assert isinstance(READ_TOOL, Tool)
        assert READ_TOOL.definition.name == "Read"
        assert READ_TOOL.definition.is_read_only

    def test_write_tool(self):
        """Test WRITE_TOOL"""
        assert isinstance(WRITE_TOOL, Tool)
        assert WRITE_TOOL.definition.name == "Write"
        assert not WRITE_TOOL.definition.is_read_only

    def test_edit_tool(self):
        """Test EDIT_TOOL"""
        assert isinstance(EDIT_TOOL, Tool)
        assert EDIT_TOOL.definition.name == "Edit"

    def test_glob_tool(self):
        """Test GLOB_TOOL"""
        assert isinstance(GLOB_TOOL, Tool)
        assert GLOB_TOOL.definition.name == "Glob"

    def test_grep_tool(self):
        """Test GREP_TOOL"""
        assert isinstance(GREP_TOOL, Tool)
        assert GREP_TOOL.definition.name == "Grep"

    def test_bash_tool(self):
        """Test BASH_TOOL"""
        assert isinstance(BASH_TOOL, Tool)
        assert BASH_TOOL.definition.name == "Bash"

    def test_web_fetch_tool(self):
        """Test WEB_FETCH_TOOL"""
        assert isinstance(WEB_FETCH_TOOL, Tool)
        assert WEB_FETCH_TOOL.definition.name == "WebFetch"

    def test_web_search_tool(self):
        """Test WEB_SEARCH_TOOL"""
        assert isinstance(WEB_SEARCH_TOOL, Tool)
        assert WEB_SEARCH_TOOL.definition.name == "WebSearch"

    def test_task_tool(self):
        """Test TASK_TOOL"""
        assert isinstance(TASK_TOOL, Tool)
        assert TASK_TOOL.definition.name == "Task"

    def test_ask_user_tool(self):
        """Test ASK_USER_TOOL"""
        assert isinstance(ASK_USER_TOOL, Tool)
        assert ASK_USER_TOOL.definition.name == "AskUserQuestion"
