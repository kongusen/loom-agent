"""
MCP Stdio Client Unit Tests

测试基于 stdio 的 MCP 客户端功能
"""

import json
from unittest.mock import AsyncMock, Mock, patch

import pytest

from loom.providers.mcp.stdio_client import StdioMCPClient


class TestStdioMCPClientInit:
    """测试 StdioMCPClient 初始化"""

    def test_init_success(self):
        """测试成功初始化"""
        client = StdioMCPClient(
            provider_id="test-provider",
            command="python",
            args=["-m", "test_server"],
            env={"TEST_VAR": "test_value"},
        )

        assert client.provider_id == "test-provider"
        assert client.command == "python"
        assert client.args == ["-m", "test_server"]
        assert client.env == {"TEST_VAR": "test_value"}
        assert client._process is None
        assert client._request_id == 0
        assert not client._connected

    def test_init_without_args(self):
        """测试没有参数时初始化"""
        client = StdioMCPClient(
            provider_id="test-provider",
            command="python",
        )

        assert client.args == []
        assert client.env is None


class TestStdioMCPClientConnect:
    """测试连接功能"""

    @pytest.mark.asyncio
    async def test_connect_success(self):
        """测试成功连接"""
        client = StdioMCPClient(
            provider_id="test-provider",
            command="python",
            args=["-c", "import sys; sys.stdin.readline()"],
        )

        mock_process = Mock()
        mock_process.stdin = AsyncMock()
        mock_process.stdout = AsyncMock()
        mock_process.stdin.drain = AsyncMock()
        mock_process.stdout.readline = AsyncMock(
            return_value=json.dumps({"jsonrpc": "2.0", "id": 1, "result": {}}).encode() + b"\n"
        )

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            await client.connect()

        assert client._connected is True
        assert client._process is not None

    @pytest.mark.asyncio
    async def test_connect_already_connected(self):
        """测试已经连接时不再重复连接"""
        client = StdioMCPClient(
            provider_id="test-provider",
            command="python",
        )
        client._connected = True

        await client.connect()

        # 应该不会创建新的进程
        assert client._process is None

    @pytest.mark.asyncio
    async def test_connect_failure(self):
        """测试连接失败"""
        client = StdioMCPClient(
            provider_id="test-provider",
            command="nonexistent_command",
        )

        with (
            patch("asyncio.create_subprocess_exec", side_effect=Exception("Command not found")),
            pytest.raises(ConnectionError, match="Failed to start"),
        ):
            await client.connect()


class TestStdioMCPClientDisconnect:
    """测试断开连接功能"""

    @pytest.mark.asyncio
    async def test_disconnect_success(self):
        """测试成功断开连接"""
        client = StdioMCPClient(
            provider_id="test-provider",
            command="python",
        )

        mock_process = Mock()
        mock_process.stdin = AsyncMock()
        mock_process.stdin.write = Mock()
        mock_process.stdin.drain = AsyncMock()
        mock_process.terminate = Mock()
        mock_process.wait = AsyncMock()
        client._process = mock_process
        client._connected = True

        await client.disconnect()

        assert client._connected is False
        mock_process.terminate.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect_not_connected(self):
        """测试未连接时断开连接"""
        client = StdioMCPClient(
            provider_id="test-provider",
            command="python",
        )

        await client.disconnect()

        # 应该不会出错
        assert client._connected is False



class TestStdioMCPClientListTools:
    """测试列出工具功能"""

    @pytest.mark.asyncio
    async def test_list_tools_success(self):
        """测试成功列出工具"""
        client = StdioMCPClient(
            provider_id="test-provider",
            command="python",
        )

        mock_process = Mock()
        mock_process.stdin = AsyncMock()
        mock_process.stdout = AsyncMock()
        mock_process.stdin.write = Mock()
        mock_process.stdin.drain = AsyncMock()
        mock_process.stdout.readline = AsyncMock(
            return_value=json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "result": {
                        "tools": [
                            {
                                "name": "test_tool",
                                "description": "Test tool",
                                "inputSchema": {"type": "object"},
                            }
                        ]
                    },
                }
            ).encode()
            + b"\n"
        )
        client._process = mock_process
        client._connected = True

        tools = await client.list_tools()

        assert len(tools) == 1
        assert tools[0].name == "test_tool"

    @pytest.mark.asyncio
    async def test_list_tools_not_connected(self):
        """测试未连接时列出工具"""
        client = StdioMCPClient(
            provider_id="test-provider",
            command="python",
        )

        with pytest.raises(RuntimeError, match="Not connected"):
            await client.list_tools()


class TestStdioMCPClientCallTool:
    """测试调用工具功能"""

    @pytest.mark.asyncio
    async def test_call_tool_success(self):
        """测试成功调用工具"""
        client = StdioMCPClient(
            provider_id="test-provider",
            command="python",
        )

        mock_process = Mock()
        mock_process.stdin = AsyncMock()
        mock_process.stdout = AsyncMock()
        mock_process.stdin.write = Mock()
        mock_process.stdin.drain = AsyncMock()
        mock_process.stdout.readline = AsyncMock(
            return_value=json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "result": {
                        "content": [{"type": "text", "text": "Tool result"}],
                        "isError": False,
                    },
                }
            ).encode()
            + b"\n"
        )
        client._process = mock_process
        client._connected = True

        result = await client.call_tool("test_tool", {"arg1": "value1"})

        assert result.is_error is False
        assert len(result.content) == 1

    @pytest.mark.asyncio
    async def test_call_tool_not_connected(self):
        """测试未连接时调用工具"""
        client = StdioMCPClient(
            provider_id="test-provider",
            command="python",
        )

        with pytest.raises(RuntimeError, match="Not connected"):
            await client.call_tool("test_tool", {})


class TestStdioMCPClientListResources:
    """测试列出资源功能"""

    @pytest.mark.asyncio
    async def test_list_resources_success(self):
        """测试成功列出资源"""
        client = StdioMCPClient(
            provider_id="test-provider",
            command="python",
        )

        mock_process = Mock()
        mock_process.stdin = AsyncMock()
        mock_process.stdout = AsyncMock()
        mock_process.stdin.write = Mock()
        mock_process.stdin.drain = AsyncMock()
        mock_process.stdout.readline = AsyncMock(
            return_value=json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "result": {
                        "resources": [
                            {
                                "uri": "file:///test.txt",
                                "name": "test.txt",
                                "mimeType": "text/plain",
                                "description": "Test file",
                            }
                        ]
                    },
                }
            ).encode()
            + b"\n"
        )
        client._process = mock_process
        client._connected = True

        resources = await client.list_resources()

        assert len(resources) == 1
        assert resources[0].uri == "file:///test.txt"

    @pytest.mark.asyncio
    async def test_list_resources_not_connected(self):
        """测试未连接时列出资源"""
        client = StdioMCPClient(
            provider_id="test-provider",
            command="python",
        )

        with pytest.raises(RuntimeError, match="Not connected"):
            await client.list_resources()


class TestStdioMCPClientReadResource:
    """测试读取资源功能"""

    @pytest.mark.asyncio
    async def test_read_resource_success(self):
        """测试成功读取资源"""
        client = StdioMCPClient(
            provider_id="test-provider",
            command="python",
        )

        mock_process = Mock()
        mock_process.stdin = AsyncMock()
        mock_process.stdout = AsyncMock()
        mock_process.stdin.write = Mock()
        mock_process.stdin.drain = AsyncMock()
        mock_process.stdout.readline = AsyncMock(
            return_value=json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "result": {"contents": [{"text": "Resource content"}]},
                }
            ).encode()
            + b"\n"
        )
        client._process = mock_process
        client._connected = True

        content = await client.read_resource("file:///test.txt")

        assert content == "Resource content"

    @pytest.mark.asyncio
    async def test_read_resource_not_connected(self):
        """测试未连接时读取资源"""
        client = StdioMCPClient(
            provider_id="test-provider",
            command="python",
        )

        with pytest.raises(RuntimeError, match="Not connected"):
            await client.read_resource("file:///test.txt")


class TestStdioMCPClientSendRequest:
    """测试发送请求功能"""

    @pytest.mark.asyncio
    async def test_send_request_success(self):
        """测试成功发送请求"""
        client = StdioMCPClient(
            provider_id="test-provider",
            command="python",
        )

        mock_process = Mock()
        mock_process.stdin = AsyncMock()
        mock_process.stdout = AsyncMock()
        mock_process.stdin.write = Mock()
        mock_process.stdin.drain = AsyncMock()
        mock_process.stdout.readline = AsyncMock(
            return_value=json.dumps({"jsonrpc": "2.0", "id": 1, "result": {"key": "value"}}).encode()
            + b"\n"
        )
        client._process = mock_process

        result = await client._send_request("test/method", {"param": "value"})

        assert result == {"key": "value"}
        assert client._request_id == 1

    @pytest.mark.asyncio
    async def test_send_request_no_process(self):
        """测试没有进程时发送请求"""
        client = StdioMCPClient(
            provider_id="test-provider",
            command="python",
        )

        with pytest.raises(RuntimeError, match="Process not available"):
            await client._send_request("test/method", {})

    @pytest.mark.asyncio
    async def test_send_request_no_response(self):
        """测试没有响应"""
        client = StdioMCPClient(
            provider_id="test-provider",
            command="python",
        )

        mock_process = Mock()
        mock_process.stdin = AsyncMock()
        mock_process.stdout = AsyncMock()
        mock_process.stdin.write = Mock()
        mock_process.stdin.drain = AsyncMock()
        mock_process.stdout.readline = AsyncMock(return_value=b"")
        client._process = mock_process

        with pytest.raises(RuntimeError, match="No response"):
            await client._send_request("test/method", {})

    @pytest.mark.asyncio
    async def test_send_request_with_error(self):
        """测试请求返回错误"""
        client = StdioMCPClient(
            provider_id="test-provider",
            command="python",
        )

        mock_process = Mock()
        mock_process.stdin = AsyncMock()
        mock_process.stdout = AsyncMock()
        mock_process.stdin.write = Mock()
        mock_process.stdin.drain = AsyncMock()
        mock_process.stdout.readline = AsyncMock(
            return_value=json.dumps(
                {"jsonrpc": "2.0", "id": 1, "error": {"message": "Test error", "code": -1}}
            ).encode()
            + b"\n"
        )
        client._process = mock_process

        with pytest.raises(RuntimeError, match="MCP error: Test error"):
            await client._send_request("test/method", {})


class TestStdioMCPClientSendNotification:
    """测试发送通知功能"""

    @pytest.mark.asyncio
    async def test_send_notification_success(self):
        """测试成功发送通知"""
        client = StdioMCPClient(
            provider_id="test-provider",
            command="python",
        )

        mock_process = Mock()
        mock_process.stdin = AsyncMock()
        mock_process.stdin.write = Mock()
        mock_process.stdin.drain = AsyncMock()
        client._process = mock_process

        await client._send_notification("test/notification", {"param": "value"})

        mock_process.stdin.write.assert_called_once()
        mock_process.stdin.drain.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_notification_no_process(self):
        """测试没有进程时发送通知"""
        client = StdioMCPClient(
            provider_id="test-provider",
            command="python",
        )

        # 应该不会抛出异常
        await client._send_notification("test/notification", {})
