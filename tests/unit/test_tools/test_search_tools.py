"""
Tests for SearchTools

测试文件名和内容搜索功能
"""

import pytest

from loom.tools.builtin.search import SearchTools, create_search_tools
from loom.tools.core.sandbox import Sandbox


class TestSearchToolsInit:
    """测试 SearchTools 初始化"""

    @pytest.fixture
    def sandbox(self, tmp_path):
        """创建沙箱实例"""
        return Sandbox(tmp_path)

    def test_init_with_sandbox(self, sandbox):
        """测试使用沙箱初始化"""
        tools = SearchTools(sandbox)

        assert tools.sandbox == sandbox


class TestSearchToolsGlob:
    """测试 glob 方法"""

    @pytest.fixture
    def setup_files(self, tmp_path):
        """设置测试文件"""
        (tmp_path / "test1.py").write_text("content1")
        (tmp_path / "test2.py").write_text("content2")
        (tmp_path / "test.txt").write_text("content3")
        (tmp_path / "subdir").mkdir()
        (tmp_path / "subdir" / "nested.py").write_text("content4")

    @pytest.mark.asyncio
    async def test_glob_all_python_files(self, tmp_path, setup_files):
        """测试匹配所有 Python 文件"""
        sandbox = Sandbox(tmp_path)
        tools = SearchTools(sandbox)

        result = await tools.glob("*.py")

        assert result["success"] == "true"
        assert result["count"] == "2"  # test1.py, test2.py
        assert "test1.py" in result["files"]
        assert "test2.py" in result["files"]

    @pytest.mark.asyncio
    async def test_glob_recursive_pattern(self, tmp_path, setup_files):
        """测试递归匹配模式"""
        sandbox = Sandbox(tmp_path)
        tools = SearchTools(sandbox)

        result = await tools.glob("**/*.py")

        assert result["success"] == "true"
        assert result["count"] == "3"  # test1.py, test2.py, nested.py
        assert "subdir/nested.py" in result["files"]

    @pytest.mark.asyncio
    async def test_glob_with_max_results(self, tmp_path, setup_files):
        """测试限制结果数量"""
        sandbox = Sandbox(tmp_path)
        tools = SearchTools(sandbox)

        result = await tools.glob("**/*.py", max_results=2)

        assert result["success"] == "true"
        assert len(result["files"]) <= 2

    @pytest.mark.asyncio
    async def test_glob_no_matches(self, tmp_path):
        """测试没有匹配结果"""
        sandbox = Sandbox(tmp_path)
        tools = SearchTools(sandbox)

        result = await tools.glob("*.nonexistent")

        assert result["success"] == "true"
        assert result["count"] == "0"
        assert result["files"] == []

    @pytest.mark.asyncio
    async def test_glob_directory_only(self, tmp_path):
        """测试只匹配目录"""
        (tmp_path / "dir1").mkdir()
        (tmp_path / "dir2").mkdir()

        sandbox = Sandbox(tmp_path)
        tools = SearchTools(sandbox)

        # 匹配所有项（包括目录）
        result = await tools.glob("*")

        assert result["success"] == "true"
        assert "dir1" in result["files"]
        assert "dir2" in result["files"]


class TestSearchToolsGrep:
    """测试 grep 方法"""

    @pytest.fixture
    def setup_files(self, tmp_path):
        """设置测试文件"""
        (tmp_path / "test1.py").write_text("def hello():\n    print('world')\n")
        (tmp_path / "test2.py").write_text("# TODO: fix this\nx = 5\n")
        (tmp_path / "test3.txt").write_text("Hello World\nhello again\n")
        (tmp_path / "subdir").mkdir()
        (tmp_path / "subdir" / "nested.py").write_text("def hello():\n    pass\n")

    @pytest.mark.asyncio
    async def test_grep_case_sensitive(self, tmp_path, setup_files):
        """测试区分大小写搜索"""
        sandbox = Sandbox(tmp_path)
        tools = SearchTools(sandbox)

        result = await tools.grep("Hello", case_sensitive=True)

        assert result["success"] == "true"
        # 只匹配大写 Hello
        assert result["count"] == "1"
        assert result["matches"][0]["file"] == "test3.txt"

    @pytest.mark.asyncio
    async def test_grep_case_insensitive(self, tmp_path, setup_files):
        """测试不区分大小写搜索"""
        sandbox = Sandbox(tmp_path)
        tools = SearchTools(sandbox)

        result = await tools.grep("hello", case_sensitive=False)

        assert result["success"] == "true"
        # 应该匹配所有包含 hello 的行（不区分大小写）
        # test1.py: def hello():
        # test3.txt: Hello World
        # test3.txt: hello again
        # nested.py: def hello():
        # = 4 matches total
        assert result["count"] == "4"

    @pytest.mark.asyncio
    async def test_grep_with_file_pattern(self, tmp_path, setup_files):
        """测试使用文件模式过滤"""
        sandbox = Sandbox(tmp_path)
        tools = SearchTools(sandbox)

        result = await tools.grep("hello", file_pattern="*.py", case_sensitive=False)

        assert result["success"] == "true"
        # 只在 .py 文件中搜索
        for match in result["matches"]:
            assert match["file"].endswith(".py")

    @pytest.mark.asyncio
    async def test_grep_with_max_results(self, tmp_path, setup_files):
        """测试限制结果数量"""
        sandbox = Sandbox(tmp_path)
        tools = SearchTools(sandbox)

        result = await tools.grep("hello", case_sensitive=False, max_results=2)

        assert result["success"] == "true"
        assert len(result["matches"]) <= 2

    @pytest.mark.asyncio
    async def test_grep_regex_pattern(self, tmp_path, setup_files):
        """测试正则表达式模式"""
        sandbox = Sandbox(tmp_path)
        tools = SearchTools(sandbox)

        result = await tools.grep(r"def\s+\w+")

        assert result["success"] == "true"
        # 应该匹配 "def hello()" 在两个文件中
        assert result["count"] == "2"

    @pytest.mark.asyncio
    async def test_grep_no_matches(self, tmp_path, setup_files):
        """测试没有匹配结果"""
        sandbox = Sandbox(tmp_path)
        tools = SearchTools(sandbox)

        result = await tools.grep("nonexistent_pattern")

        assert result["success"] == "true"
        assert result["count"] == "0"
        assert result["matches"] == []

    @pytest.mark.asyncio
    async def test_grep_invalid_regex(self, tmp_path, setup_files):
        """测试无效的正则表达式"""
        sandbox = Sandbox(tmp_path)
        tools = SearchTools(sandbox)

        result = await tools.grep("[invalid(")

        assert result["success"] == "false"
        assert "error" in result
        assert "Invalid regex" in result["error"]


class TestSearchToolsBinaryFileHandling:
    """测试二进制文件处理"""

    @pytest.mark.asyncio
    async def test_grep_skips_binary_files(self, tmp_path):
        """测试跳过二进制文件"""
        # 创建一个二进制文件
        (tmp_path / "binary.dat").write_bytes(b"\x00\x01\x02\x03\xff\xfe")
        (tmp_path / "text.txt").write_text("Hello World")

        sandbox = Sandbox(tmp_path)
        tools = SearchTools(sandbox)

        result = await tools.grep("Hello")

        # 应该只返回文本文件的匹配
        assert result["success"] == "true"
        assert result["count"] == "1"
        assert result["matches"][0]["file"] == "text.txt"

    @pytest.mark.asyncio
    async def test_grep_skips_directories(self, tmp_path):
        """测试跳过目录"""
        (tmp_path / "dir1").mkdir()
        (tmp_path / "dir1" / "subdir").mkdir()

        sandbox = Sandbox(tmp_path)
        tools = SearchTools(sandbox)

        result = await tools.grep("anything")

        # 目录应该被跳过，不会导致错误
        assert result["success"] == "true"
        assert result["count"] == "0"


class TestCreateSearchTools:
    """测试 create_search_tools 函数"""

    def test_create_search_tools_returns_list(self, tmp_path):
        """测试返回工具列表"""
        sandbox = Sandbox(tmp_path)
        tools = create_search_tools(sandbox)

        assert isinstance(tools, list)
        assert len(tools) == 2

    def test_create_search_tools_has_glob(self, tmp_path):
        """测试包含 glob 工具"""
        sandbox = Sandbox(tmp_path)
        tools = create_search_tools(sandbox)

        tool_names = [t["function"]["name"] for t in tools]
        assert "glob" in tool_names

    def test_create_search_tools_has_grep(self, tmp_path):
        """测试包含 grep 工具"""
        sandbox = Sandbox(tmp_path)
        tools = create_search_tools(sandbox)

        tool_names = [t["function"]["name"] for t in tools]
        assert "grep" in tool_names

    def test_create_search_tools_glob_has_executor(self, tmp_path):
        """测试 glob 工具有执行器"""
        sandbox = Sandbox(tmp_path)
        tools = create_search_tools(sandbox)

        glob_tool = next(t for t in tools if t["function"]["name"] == "glob")
        assert "_executor" in glob_tool
        assert callable(glob_tool["_executor"])

    def test_create_search_tools_grep_has_executor(self, tmp_path):
        """测试 grep 工具有执行器"""
        sandbox = Sandbox(tmp_path)
        tools = create_search_tools(sandbox)

        grep_tool = next(t for t in tools if t["function"]["name"] == "grep")
        assert "_executor" in grep_tool
        assert callable(grep_tool["_executor"])

    def test_create_search_tools_glob_parameters(self, tmp_path):
        """测试 glob 工具参数定义"""
        sandbox = Sandbox(tmp_path)
        tools = create_search_tools(sandbox)

        glob_tool = next(t for t in tools if t["function"]["name"] == "glob")
        params = glob_tool["function"]["parameters"]

        assert params["type"] == "object"
        assert "pattern" in params["properties"]
        assert "max_results" in params["properties"]
        assert "pattern" in params["required"]

    def test_create_search_tools_grep_parameters(self, tmp_path):
        """测试 grep 工具参数定义"""
        sandbox = Sandbox(tmp_path)
        tools = create_search_tools(sandbox)

        grep_tool = next(t for t in tools if t["function"]["name"] == "grep")
        params = grep_tool["function"]["parameters"]

        assert params["type"] == "object"
        assert "pattern" in params["properties"]
        assert "file_pattern" in params["properties"]
        assert "max_results" in params["properties"]
        assert "case_sensitive" in params["properties"]
        assert "pattern" in params["required"]
