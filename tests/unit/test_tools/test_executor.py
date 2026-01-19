"""
Tests for Tool Executor

测试工具执行引擎的功能
"""

from unittest.mock import AsyncMock

import pytest

from loom.tools.executor import ToolExecutionResult, ToolExecutor


class TestToolExecutorInit:
    """测试 ToolExecutor 初始化"""

    def test_init_default(self):
        """测试默认初始化"""
        executor = ToolExecutor()

        assert executor.parallel_execution is True
        assert len(executor.read_only_patterns) > 0

    def test_init_with_parallel_false(self):
        """测试禁用并行执行"""
        executor = ToolExecutor(parallel_execution=False)

        assert executor.parallel_execution is False


class TestIsReadOnly:
    """测试 is_read_only 方法"""

    @pytest.mark.parametrize(
        "tool_name",
        [
            "read_file",
            "get_data",
            "list_files",
            "ls",
            "grep_pattern",
            "find_items",
            "search_db",
            "query_info",
            "fetch_url",
            "view_content",
            "READ_FILE",
            "GET_DATA",
            "LIST_FILES",
            "LS",
            "GREP_PATTERN",
        ],
    )
    def test_read_only_tools(self, tool_name):
        """测试只读工具识别"""
        executor = ToolExecutor()
        assert executor.is_read_only(tool_name) is True

    @pytest.mark.parametrize(
        "tool_name",
        [
            "write_file",
            "create_dir",
            "delete_item",
            "update_data",
            "remove_file",
            "execute_command",
            "run_bash",
        ],
    )
    def test_write_tools(self, tool_name):
        """测试写入工具识别"""
        executor = ToolExecutor()
        assert executor.is_read_only(tool_name) is False


class TestExecuteBatch:
    """测试 execute_batch 方法"""

    @pytest.mark.asyncio
    async def test_empty_tool_calls(self):
        """测试空工具调用列表"""
        executor = ToolExecutor()
        executor_func = AsyncMock()

        result = await executor.execute_batch([], executor_func)

        assert result == []

    @pytest.mark.asyncio
    async def test_single_tool_call(self):
        """测试单个工具调用"""
        executor = ToolExecutor()
        executor_func = AsyncMock(return_value="result1")

        tool_calls = [{"name": "read_file", "arguments": {"path": "/test"}}]

        result = await executor.execute_batch(tool_calls, executor_func)

        assert len(result) == 1
        assert result[0].index == 0
        assert result[0].name == "read_file"
        assert result[0].result == "result1"
        assert result[0].error is False

    @pytest.mark.asyncio
    async def test_multiple_read_only_tools_parallel(self):
        """测试多个只读工具并行执行"""
        import asyncio

        executor = ToolExecutor(parallel_execution=True)

        async def mock_executor(name, args):
            await asyncio.sleep(0.1)
            return f"result_{name}"

        tool_calls = [
            {"name": "read_file1", "arguments": {}},
            {"name": "read_file2", "arguments": {}},
            {"name": "read_file3", "arguments": {}},
        ]

        result = await executor.execute_batch(tool_calls, mock_executor)

        assert len(result) == 3
        assert result[0].result == "result_read_file1"
        assert result[1].result == "result_read_file2"
        assert result[2].result == "result_read_file3"

    @pytest.mark.asyncio
    async def test_write_then_read_tools(self):
        """测试写入工具后跟读取工具（覆盖lines 115-116）"""
        import asyncio

        executor = ToolExecutor(parallel_execution=True)

        call_order = []

        async def mock_executor(name, args):
            call_order.append(name)
            await asyncio.sleep(0.01)
            return f"result_{name}"

        # 写入工具后跟读取工具 - 这会触发lines 115-116
        tool_calls = [
            {"name": "write_file", "arguments": {}},  # 写入
            {"name": "read_file", "arguments": {}},  # 读取 - 触发关闭写入组
            {"name": "read_data", "arguments": {}},  # 读取
        ]

        result = await executor.execute_batch(tool_calls, mock_executor)

        assert len(result) == 3
        # 写入工具应该先执行
        assert call_order[0] == "write_file"
        # 读取工具应该在其后执行

    @pytest.mark.asyncio
    async def test_write_tools_sequential(self):
        """测试写入工具串行执行"""
        import asyncio

        executor = ToolExecutor(parallel_execution=True)

        call_order = []

        async def mock_executor(name, args):
            call_order.append(name)
            return f"result_{name}"

        tool_calls = [
            {"name": "write_file1", "arguments": {}},
            {"name": "write_file2", "arguments": {}},
        ]

        result = await executor.execute_batch(tool_calls, mock_executor)

        assert len(result) == 2
        assert call_order == ["write_file1", "write_file2"]

    @pytest.mark.asyncio
    async def test_parallel_disabled(self):
        """测试禁用并行执行时所有工具串行执行"""
        import asyncio

        executor = ToolExecutor(parallel_execution=False)

        call_order = []

        async def mock_executor(name, args):
            call_order.append(name)
            return f"result_{name}"

        tool_calls = [
            {"name": "read_file1", "arguments": {}},
            {"name": "read_file2", "arguments": {}},
        ]

        result = await executor.execute_batch(tool_calls, mock_executor)

        assert len(result) == 2
        assert call_order == ["read_file1", "read_file2"]

    @pytest.mark.asyncio
    async def test_read_then_write_tools(self):
        """测试读取工具后跟写入工具"""
        import asyncio

        executor = ToolExecutor(parallel_execution=True)

        call_order = []

        async def mock_executor(name, args):
            call_order.append(name)
            return f"result_{name}"

        tool_calls = [
            {"name": "read_file", "arguments": {}},
            {"name": "write_file", "arguments": {}},
        ]

        result = await executor.execute_batch(tool_calls, mock_executor)

        assert len(result) == 2
        # 读取工具可以并行，写入工具应该在其后串行执行

    @pytest.mark.asyncio
    async def test_mixed_read_write_read_tools(self):
        """测试混合读写工具 - 读、写、读模式"""
        import asyncio

        executor = ToolExecutor(parallel_execution=True)

        call_order = []

        async def mock_executor(name, args):
            call_order.append(name)
            await asyncio.sleep(0.01)
            return f"result_{name}"

        # 读、写、读模式 - 第二个读工具触发lines 115-116
        tool_calls = [
            {"name": "read_file1", "arguments": {}},  # 读取
            {"name": "write_file", "arguments": {}},  # 写入
            {"name": "read_file2", "arguments": {}},  # 读取 - 触发lines 115-116
        ]

        result = await executor.execute_batch(tool_calls, mock_executor)

        assert len(result) == 3
        # 第一个读取先执行
        assert call_order[0] == "read_file1"
        # 然后是写入
        assert call_order[1] == "write_file"
        # 最后是第二个读取

    @pytest.mark.asyncio
    async def test_tool_execution_error(self):
        """测试工具执行错误处理"""
        executor = ToolExecutor()

        async def mock_executor(name, args):
            if name == "error_tool":
                raise ValueError("Test error")
            return f"result_{name}"

        tool_calls = [
            {"name": "read_file", "arguments": {}},
            {"name": "error_tool", "arguments": {}},
            {"name": "read_data", "arguments": {}},
        ]

        result = await executor.execute_batch(tool_calls, mock_executor)

        assert len(result) == 3
        assert result[0].error is False
        assert result[1].error is True
        assert "Test error" in result[1].result
        assert result[2].error is False

    @pytest.mark.asyncio
    async def test_results_in_original_order(self):
        """测试结果按原始顺序返回"""
        import asyncio

        executor = ToolExecutor(parallel_execution=True)

        async def mock_executor(name, args):
            # 不同工具有不同的延迟
            delays = {"read_file3": 0.05, "read_file1": 0.01, "read_file2": 0.02}
            delay = delays.get(name, 0)
            await asyncio.sleep(delay)
            return f"result_{name}"

        tool_calls = [
            {"name": "read_file1", "arguments": {}},
            {"name": "read_file2", "arguments": {}},
            {"name": "read_file3", "arguments": {}},
        ]

        result = await executor.execute_batch(tool_calls, mock_executor)

        assert len(result) == 3
        assert result[0].name == "read_file1"
        assert result[1].name == "read_file2"
        assert result[2].name == "read_file3"

    @pytest.mark.asyncio
    async def test_consecutive_write_groups(self):
        """测试连续的写入工具组"""
        executor = ToolExecutor(parallel_execution=True)

        call_order = []

        async def mock_executor(name, args):
            call_order.append(name)
            return f"result_{name}"

        tool_calls = [
            {"name": "write_file1", "arguments": {}},
            {"name": "write_file2", "arguments": {}},
            {"name": "write_file3", "arguments": {}},
        ]

        result = await executor.execute_batch(tool_calls, mock_executor)

        assert len(result) == 3
        assert call_order == ["write_file1", "write_file2", "write_file3"]

    @pytest.mark.asyncio
    async def test_write_between_reads(self):
        """测试读取工具之间有写入工具"""
        import asyncio

        executor = ToolExecutor(parallel_execution=True)

        call_order = []

        async def mock_executor(name, args):
            call_order.append(name)
            await asyncio.sleep(0.01)
            return f"result_{name}"

        tool_calls = [
            {"name": "read_file1", "arguments": {}},
            {"name": "read_file2", "arguments": {}},
            {"name": "write_file", "arguments": {}},  # 写入分隔读取组
            {"name": "read_file3", "arguments": {}},
            {"name": "read_file4", "arguments": {}},
        ]

        result = await executor.execute_batch(tool_calls, mock_executor)

        assert len(result) == 5
        assert result[0].name == "read_file1"
        assert result[4].name == "read_file4"
