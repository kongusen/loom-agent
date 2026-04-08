"""Test more builtin tools"""

from loom.tools.builtin.mcp_tool import MCP_CALL_TOOL, MCP_LIST_TOOL, MCP_READ_TOOL
from loom.tools.builtin.notebook_skill_lsp_tool import (
    LSP_DIAGNOSTICS_TOOL,
    NOTEBOOK_EDIT_TOOL,
    SKILL_TOOL,
)
from loom.tools.schema import Tool


class TestMCPTools:
    """Test MCP tools"""

    def test_mcp_list_resources(self):
        """Test MCP_LIST_TOOL"""
        assert isinstance(MCP_LIST_TOOL, Tool)
        assert MCP_LIST_TOOL.definition.name == "ListMcpResources"

    def test_mcp_read_resource(self):
        """Test MCP_READ_TOOL"""
        assert isinstance(MCP_READ_TOOL, Tool)
        assert MCP_READ_TOOL.definition.name == "ReadMcpResource"

    def test_mcp_call_tool(self):
        """Test MCP_CALL_TOOL"""
        assert isinstance(MCP_CALL_TOOL, Tool)
        assert MCP_CALL_TOOL.definition.name == "MCPTool"


class TestNotebookSkillLSPTools:
    """Test Notebook, Skill, LSP tools"""

    def test_notebook_edit(self):
        """Test NOTEBOOK_EDIT_TOOL"""
        assert isinstance(NOTEBOOK_EDIT_TOOL, Tool)
        assert NOTEBOOK_EDIT_TOOL.definition.name == "NotebookEdit"

    def test_skill_invoke(self):
        """Test SKILL_TOOL"""
        assert isinstance(SKILL_TOOL, Tool)
        assert SKILL_TOOL.definition.name == "Skill"

    def test_lsp_get_diagnostics(self):
        """Test LSP_DIAGNOSTICS_TOOL"""
        assert isinstance(LSP_DIAGNOSTICS_TOOL, Tool)
        assert LSP_DIAGNOSTICS_TOOL.definition.name == "GetDiagnostics"
