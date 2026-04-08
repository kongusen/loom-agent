"""Test workflow and config tools"""

from loom.tools.builtin.workflow_config_tool import (
    CONFIG_GET_TOOL,
    CONFIG_SET_TOOL,
    ENTER_PLAN_TOOL,
    ENTER_WORKTREE_TOOL,
    EXIT_PLAN_TOOL,
)
from loom.tools.schema import Tool


class TestWorkflowTools:
    """Test workflow tools"""

    def test_enter_plan_mode(self):
        """Test ENTER_PLAN_TOOL"""
        assert isinstance(ENTER_PLAN_TOOL, Tool)
        assert ENTER_PLAN_TOOL.definition.name == "EnterPlanMode"

    def test_exit_plan_mode(self):
        """Test EXIT_PLAN_TOOL"""
        assert isinstance(EXIT_PLAN_TOOL, Tool)
        assert EXIT_PLAN_TOOL.definition.name == "ExitPlanMode"

    def test_enter_worktree(self):
        """Test ENTER_WORKTREE_TOOL"""
        assert isinstance(ENTER_WORKTREE_TOOL, Tool)
        assert ENTER_WORKTREE_TOOL.definition.name == "EnterWorktree"


class TestConfigTools:
    """Test config tools"""

    def test_config_get(self):
        """Test CONFIG_GET_TOOL"""
        assert isinstance(CONFIG_GET_TOOL, Tool)
        assert CONFIG_GET_TOOL.definition.name == "ConfigGet"

    def test_config_set(self):
        """Test CONFIG_SET_TOOL"""
        assert isinstance(CONFIG_SET_TOOL, Tool)
        assert CONFIG_SET_TOOL.definition.name == "ConfigSet"
