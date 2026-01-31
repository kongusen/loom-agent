"""
Tests for TodoTool

测试任务管理工具功能
"""

import json
import pytest

from loom.tools.sandbox import Sandbox
from loom.tools.todo_tool import TodoTool, create_todo_tool


class TestTodoToolInit:
    """测试 TodoTool 初始化"""

    def test_init_with_sandbox(self, tmp_path):
        """测试使用沙箱初始化"""
        sandbox = Sandbox(tmp_path)
        tool = TodoTool(sandbox)

        assert tool.sandbox == sandbox
        assert tool.storage_file == ".todos.json"
        assert tool.storage_path == tmp_path / ".todos.json"

    def test_init_with_custom_storage_file(self, tmp_path):
        """测试使用自定义存储文件名"""
        sandbox = Sandbox(tmp_path)
        tool = TodoTool(sandbox, storage_file="custom.json")

        assert tool.storage_file == "custom.json"
        assert tool.storage_path == tmp_path / "custom.json"


class TestTodoToolLoadTodos:
    """测试 _load_todos 方法"""

    @pytest.fixture
    def empty_tool(self, tmp_path):
        """创建空工具实例"""
        sandbox = Sandbox(tmp_path)
        return TodoTool(sandbox)

    def test_load_todos_no_file(self, empty_tool):
        """测试加载不存在的文件"""
        todos = empty_tool._load_todos()

        assert todos == []

    def test_load_todos_empty_file(self, empty_tool):
        """测试加载空文件"""
        empty_tool.storage_path.write_text("[]")

        todos = empty_tool._load_todos()

        assert todos == []

    def test_load_todos_with_valid_data(self, empty_tool):
        """测试加载有效数据"""
        data = [
            {"content": "Task 1", "status": "pending", "activeForm": "Task 1"},
            {"content": "Task 2", "status": "completed", "activeForm": "Task 2"},
        ]
        empty_tool.storage_path.write_text(json.dumps(data))

        todos = empty_tool._load_todos()

        assert len(todos) == 2
        assert todos[0]["content"] == "Task 1"
        assert todos[1]["status"] == "completed"

    def test_load_todos_invalid_json(self, empty_tool):
        """测试加载无效 JSON"""
        empty_tool.storage_path.write_text("invalid json")

        todos = empty_tool._load_todos()

        # 应该返回空列表而不是抛出异常
        assert todos == []

    def test_load_todos_non_list_data(self, empty_tool):
        """测试加载非列表数据"""
        empty_tool.storage_path.write_text('{"key": "value"}')

        todos = empty_tool._load_todos()

        # 应该返回空列表
        assert todos == []


class TestTodoToolSaveTodos:
    """测试 _save_todos 方法"""

    @pytest.fixture
    def tool(self, tmp_path):
        """创建工具实例"""
        sandbox = Sandbox(tmp_path)
        return TodoTool(sandbox)

    def test_save_todos_creates_file(self, tool):
        """测试保存创建文件"""
        todos = [
            {"content": "Task 1", "status": "pending", "activeForm": "Task 1"},
        ]

        tool._save_todos(todos)

        assert tool.storage_path.exists()

    def test_save_todos_content(self, tool):
        """测试保存内容正确"""
        todos = [
            {"content": "Task 1", "status": "pending", "activeForm": "Task 1"},
            {"content": "Task 2", "status": "in_progress", "activeForm": "Task 2"},
        ]

        tool._save_todos(todos)

        content = tool.storage_path.read_text()
        loaded = json.loads(content)

        assert loaded == todos


class TestTodoToolWriteTodos:
    """测试 write_todos 方法"""

    @pytest.fixture
    def tool(self, tmp_path):
        """创建工具实例"""
        sandbox = Sandbox(tmp_path)
        return TodoTool(sandbox)

    @pytest.mark.asyncio
    async def test_write_todos_valid(self, tool):
        """测试写入有效的任务列表"""
        todos = [
            {"content": "Task 1", "status": "pending", "activeForm": "Doing task 1"},
            {"content": "Task 2", "status": "in_progress", "activeForm": "Doing task 2"},
        ]

        result = await tool.write_todos(todos)

        assert result["success"] == "true"
        assert result["count"] == "2"
        assert "Saved 2 todos" in result["message"]

    @pytest.mark.asyncio
    async def test_write_todos_missing_content(self, tool):
        """测试缺少 content 字段"""
        todos = [
            {"status": "pending", "activeForm": "Task"},
        ]

        result = await tool.write_todos(todos)

        assert result["success"] == "false"
        assert "error" in result
        assert "content" in result["error"]

    @pytest.mark.asyncio
    async def test_write_todos_missing_status(self, tool):
        """测试缺少 status 字段"""
        todos = [
            {"content": "Task", "activeForm": "Doing task"},
        ]

        result = await tool.write_todos(todos)

        assert result["success"] == "false"
        assert "error" in result
        assert "status" in result["error"]

    @pytest.mark.asyncio
    async def test_write_todos_invalid_status(self, tool):
        """测试无效的状态值"""
        todos = [
            {"content": "Task", "status": "invalid_status", "activeForm": "Task"},
        ]

        result = await tool.write_todos(todos)

        assert result["success"] == "false"
        assert "error" in result
        assert "Invalid status" in result["error"]

    @pytest.mark.asyncio
    async def test_write_todos_valid_statuses(self, tool):
        """测试所有有效状态"""
        for status in ["pending", "in_progress", "completed"]:
            todos = [
                {"content": "Task", "status": status, "activeForm": "Task"},
            ]

            result = await tool.write_todos(todos)

            assert result["success"] == "true"

    @pytest.mark.asyncio
    async def test_write_todos_empty_list(self, tool):
        """测试写入空列表"""
        result = await tool.write_todos([])

        assert result["success"] == "true"
        assert result["count"] == "0"

    @pytest.mark.asyncio
    async def test_write_todos_overwrites_existing(self, tool):
        """测试覆盖现有数据"""
        # 先写入一些数据
        todos1 = [{"content": "Old", "status": "pending", "activeForm": "Old"}]
        await tool.write_todos(todos1)

        # 再写入新数据
        todos2 = [{"content": "New", "status": "completed", "activeForm": "New"}]
        await tool.write_todos(todos2)

        # 验证只有新数据存在
        loaded = tool._load_todos()
        assert len(loaded) == 1
        assert loaded[0]["content"] == "New"


class TestTodoToolReadTodos:
    """测试 read_todos 方法"""

    @pytest.fixture
    def tool(self, tmp_path):
        """创建工具实例"""
        sandbox = Sandbox(tmp_path)
        return TodoTool(sandbox)

    @pytest.mark.asyncio
    async def test_read_todos_no_file(self, tool):
        """测试读取不存在的文件"""
        result = await tool.read_todos()

        assert result["success"] == "true"
        assert result["todos"] == []
        assert result["count"] == "0"

    @pytest.mark.asyncio
    async def test_read_todos_with_data(self, tool):
        """测试读取有数据的文件"""
        # 先写入数据
        todos = [
            {"content": "Task 1", "status": "pending", "activeForm": "Task 1"},
            {"content": "Task 2", "status": "completed", "activeForm": "Task 2"},
        ]
        await tool.write_todos(todos)

        # 读取数据
        result = await tool.read_todos()

        assert result["success"] == "true"
        assert result["count"] == "2"
        assert len(result["todos"]) == 2
        assert result["todos"][0]["content"] == "Task 1"


class TestCreateTodoTool:
    """测试 create_todo_tool 函数"""

    def test_create_todo_tool_returns_dict(self, tmp_path):
        """测试返回字典"""
        sandbox = Sandbox(tmp_path)
        tool = create_todo_tool(sandbox)

        assert isinstance(tool, dict)

    def test_create_todo_tool_structure(self, tmp_path):
        """测试工具结构"""
        sandbox = Sandbox(tmp_path)
        tool = create_todo_tool(sandbox)

        assert tool["type"] == "function"
        assert "function" in tool
        assert tool["function"]["name"] == "todo_write"

    def test_create_todo_tool_has_executor(self, tmp_path):
        """测试有执行器"""
        sandbox = Sandbox(tmp_path)
        tool = create_todo_tool(sandbox)

        assert "_executor" in tool
        assert callable(tool["_executor"])

    def test_create_todo_tool_parameters(self, tmp_path):
        """测试参数定义"""
        sandbox = Sandbox(tmp_path)
        tool = create_todo_tool(sandbox)

        params = tool["function"]["parameters"]

        assert params["type"] == "object"
        assert "todos" in params["properties"]
        assert "todos" in params["required"]

        todos_param = params["properties"]["todos"]
        assert todos_param["type"] == "array"
        assert "items" in todos_param

    def test_create_todo_tool_description_has_path(self, tmp_path):
        """测试描述包含沙箱路径"""
        sandbox = Sandbox(tmp_path)
        tool = create_todo_tool(sandbox)

        description = tool["function"]["description"]
        assert str(tmp_path) in description

    @pytest.mark.asyncio
    async def test_executor_works(self, tmp_path):
        """测试执行器可以工作"""
        sandbox = Sandbox(tmp_path)
        tool = create_todo_tool(sandbox)

        executor = tool["_executor"]
        todos = [{"content": "Test", "status": "pending", "activeForm": "Testing"}]

        result = await executor(todos)

        assert result["success"] == "true"
