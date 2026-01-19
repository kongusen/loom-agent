"""
MCP HTTP Client Unit Tests

测试基于 HTTP 的 MCP 客户端功能
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from loom.providers.mcp.http_client import HttpMCPClient


class TestHttpMCPClientInit:
    """测试 HttpMCPClient 初始化"""

    def test_init_success(self):
        """测试成功初始化"""
        with patch("loom.providers.mcp.http_client.HTTPX_AVAILABLE", True):
            client = HttpMCPClient(
                provider_id="test-provider",
                base_url="http://localhost:8000",
                headers={"Authorization": "Bearer token"},
                timeout=60.0,
            )

            assert client.provider_id == "test-provider"
            assert client.base_url == "http://localhost:8000"
            assert client.headers == {"Authorization": "Bearer token"}
            assert client.timeout == 60.0
            assert client._client is None
            assert client._request_id == 0
            assert not client._connected

    def test_init_without_httpx(self):
        """测试没有 httpx 时初始化失败"""
        with patch("loom.providers.mcp.http_client.HTTPX_AVAILABLE", False):
            with pytest.raises(ImportError, match="httpx is required"):
                HttpMCPClient(
                    provider_id="test-provider",
                    base_url="http://localhost:8000",
                )

    def test_init_strips_trailing_slash(self):
        """测试初始化时移除 URL 末尾的斜杠"""
        with patch("loom.providers.mcp.http_client.HTTPX_AVAILABLE", True):
            client = HttpMCPClient(
                provider_id="test-provider",
                base_url="http://localhost:8000/",
            )
            assert client.base_url == "http://localhost:8000"


class TestHttpMCPClientConnect:
    """测试连接功能"""

    @pytest.mark.asyncio
    async def test_connect_success(self):
        """测试成功连接"""
        with patch("loom.providers.mcp.http_client.HTTPX_AVAILABLE", True):
            client = HttpMCPClient(
                provider_id="test-provider",
                base_url="http://localhost:8000",
            )

            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.json.return_value = {"result": {}}
            mock_response.raise_for_status = Mock()
            mock_client.post = AsyncMock(return_value=mock_response)

            with patch("httpx.AsyncClient", return_value=mock_client):
                await client.connect()

            assert client._connected is True
            assert client._client is not None
            mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_already_connected(self):
        """测试已经连接时不再重复连接"""
        with patch("loom.providers.mcp.http_client.HTTPX_AVAILABLE", True):
            client = HttpMCPClient(
                provider_id="test-provider",
                base_url="http://localhost:8000",
            )
            client._connected = True

            await client.connect()

            # 应该不会创建新的客户端
            assert client._client is None

    @pytest.mark.asyncio
    async def test_connect_failure(self):
        """测试连接失败"""
        with patch("loom.providers.mcp.http_client.HTTPX_AVAILABLE", True):
            client = HttpMCPClient(
                provider_id="test-provider",
                base_url="http://localhost:8000",
            )

            mock_client = AsyncMock()
            mock_client.post = AsyncMock(side_effect=Exception("Connection failed"))

            with patch("httpx.AsyncClient", return_value=mock_client):
                with pytest.raises(ConnectionError, match="Failed to connect"):
                    await client.connect()

            assert client._connected is False


class TestHttpMCPClientDisconnect:
    """测试断开连接功能"""

    @pytest.mark.asyncio
    async def test_disconnect_success(self):
        """测试成功断开连接"""
        with patch("loom.providers.mcp.http_client.HTTPX_AVAILABLE", True):
            client = HttpMCPClient(
                provider_id="test-provider",
                base_url="http://localhost:8000",
            )

            mock_client = AsyncMock()
            client._client = mock_client
            client._connected = True

            await client.disconnect()

            assert client._connected is False
            assert client._client is None
            mock_client.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect_not_connected(self):
        """测试未连接时断开连接"""
        with patch("loom.providers.mcp.http_client.HTTPX_AVAILABLE", True):
            client = HttpMCPClient(
                provider_id="test-provider",
                base_url="http://localhost:8000",
            )

            await client.disconnect()

            # 应该不会出错
            assert client._connected is False


class TestHttpMCPClientListTools:
    """测试列出工具功能"""

    @pytest.mark.asyncio
    async def test_list_tools_success(self):
        """测试成功列出工具"""
        with patch("loom.providers.mcp.http_client.HTTPX_AVAILABLE", True):
            client = HttpMCPClient(
                provider_id="test-provider",
                base_url="http://localhost:8000",
            )

            mock_response = Mock()
            mock_response.json.return_value = {
                "result": {
                    "tools": [
                        {
                            "name": "test_tool",
                            "description": "Test tool",
                            "inputSchema": {"type": "object"},
                        }
                    ]
                }
            }
            mock_response.raise_for_status = Mock()

            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            client._client = mock_client
            client._connected = True

            tools = await client.list_tools()

            assert len(tools) == 1
            assert tools[0].name == "test_tool"
            assert tools[0].description == "Test tool"

    @pytest.mark.asyncio
    async def test_list_tools_not_connected(self):
        """测试未连接时列出工具"""
        with patch("loom.providers.mcp.http_client.HTTPX_AVAILABLE", True):
            client = HttpMCPClient(
                provider_id="test-provider",
                base_url="http://localhost:8000",
            )

            with pytest.raises(RuntimeError, match="Not connected"):
                await client.list_tools()


class TestHttpMCPClientCallTool:
    """测试调用工具功能"""

    @pytest.mark.asyncio
    async def test_call_tool_success(self):
        """测试成功调用工具"""
        with patch("loom.providers.mcp.http_client.HTTPX_AVAILABLE", True):
            client = HttpMCPClient(
                provider_id="test-provider",
                base_url="http://localhost:8000",
            )

            mock_response = Mock()
            mock_response.json.return_value = {
                "result": {
                    "content": [{"type": "text", "text": "Tool result"}],
                    "isError": False,
                }
            }
            mock_response.raise_for_status = Mock()

            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            client._client = mock_client
            client._connected = True

            result = await client.call_tool("test_tool", {"arg1": "value1"})

            assert result.is_error is False
            assert len(result.content) == 1

    @pytest.mark.asyncio
    async def test_call_tool_not_connected(self):
        """测试未连接时调用工具"""
        with patch("loom.providers.mcp.http_client.HTTPX_AVAILABLE", True):
            client = HttpMCPClient(
                provider_id="test-provider",
                base_url="http://localhost:8000",
            )

            with pytest.raises(RuntimeError, match="Not connected"):
                await client.call_tool("test_tool", {})


class TestHttpMCPClientListResources:
    """测试列出资源功能"""

    @pytest.mark.asyncio
    async def test_list_resources_success(self):
        """测试成功列出资源"""
        with patch("loom.providers.mcp.http_client.HTTPX_AVAILABLE", True):
            client = HttpMCPClient(
                provider_id="test-provider",
                base_url="http://localhost:8000",
            )

            mock_response = Mock()
            mock_response.json.return_value = {
                "result": {
                    "resources": [
                        {
                            "uri": "file:///test.txt",
                            "name": "test.txt",
                            "mimeType": "text/plain",
                            "description": "Test file",
                        }
                    ]
                }
            }
            mock_response.raise_for_status = Mock()

            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            client._client = mock_client
            client._connected = True

            resources = await client.list_resources()

            assert len(resources) == 1
            assert resources[0].uri == "file:///test.txt"
            assert resources[0].name == "test.txt"

    @pytest.mark.asyncio
    async def test_list_resources_not_connected(self):
        """测试未连接时列出资源"""
        with patch("loom.providers.mcp.http_client.HTTPX_AVAILABLE", True):
            client = HttpMCPClient(
                provider_id="test-provider",
                base_url="http://localhost:8000",
            )

            with pytest.raises(RuntimeError, match="Not connected"):
                await client.list_resources()


class TestHttpMCPClientReadResource:
    """测试读取资源功能"""

    @pytest.mark.asyncio
    async def test_read_resource_success(self):
        """测试成功读取资源"""
        with patch("loom.providers.mcp.http_client.HTTPX_AVAILABLE", True):
            client = HttpMCPClient(
                provider_id="test-provider",
                base_url="http://localhost:8000",
            )

            mock_response = Mock()
            mock_response.json.return_value = {
                "result": {
                    "contents": [{"text": "Resource content"}]
                }
            }
            mock_response.raise_for_status = Mock()

            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            client._client = mock_client
            client._connected = True

            content = await client.read_resource("file:///test.txt")

            assert content == "Resource content"

    @pytest.mark.asyncio
    async def test_read_resource_empty(self):
        """测试读取空资源"""
        with patch("loom.providers.mcp.http_client.HTTPX_AVAILABLE", True):
            client = HttpMCPClient(
                provider_id="test-provider",
                base_url="http://localhost:8000",
            )

            mock_response = Mock()
            mock_response.json.return_value = {"result": {"contents": []}}
            mock_response.raise_for_status = Mock()

            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            client._client = mock_client
            client._connected = True

            content = await client.read_resource("file:///test.txt")

            assert content == ""

    @pytest.mark.asyncio
    async def test_read_resource_non_dict_content(self):
        """测试读取非字典格式的资源内容"""
        with patch("loom.providers.mcp.http_client.HTTPX_AVAILABLE", True):
            client = HttpMCPClient(
                provider_id="test-provider",
                base_url="http://localhost:8000",
            )

            mock_response = Mock()
            # 返回非字典格式的内容（例如字符串）
            mock_response.json.return_value = {
                "result": {"contents": ["string content instead of dict"]}
            }
            mock_response.raise_for_status = Mock()

            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            client._client = mock_client
            client._connected = True

            content = await client.read_resource("file:///test.txt")

            assert content == ""

    @pytest.mark.asyncio
    async def test_read_resource_not_connected(self):
        """测试未连接时读取资源"""
        with patch("loom.providers.mcp.http_client.HTTPX_AVAILABLE", True):
            client = HttpMCPClient(
                provider_id="test-provider",
                base_url="http://localhost:8000",
            )

            with pytest.raises(RuntimeError, match="Not connected"):
                await client.read_resource("file:///test.txt")


class TestHttpMCPClientListPrompts:
    """测试列出提示功能"""

    @pytest.mark.asyncio
    async def test_list_prompts_success(self):
        """测试成功列出提示"""
        with patch("loom.providers.mcp.http_client.HTTPX_AVAILABLE", True):
            client = HttpMCPClient(
                provider_id="test-provider",
                base_url="http://localhost:8000",
            )

            mock_response = Mock()
            mock_response.json.return_value = {
                "result": {
                    "prompts": [
                        {
                            "name": "test_prompt",
                            "description": "Test prompt",
                            "arguments": [{"name": "arg1", "description": "Argument 1"}],
                        }
                    ]
                }
            }
            mock_response.raise_for_status = Mock()

            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            client._client = mock_client
            client._connected = True

            prompts = await client.list_prompts()

            assert len(prompts) == 1
            assert prompts[0].name == "test_prompt"
            assert prompts[0].description == "Test prompt"

    @pytest.mark.asyncio
    async def test_list_prompts_not_connected(self):
        """测试未连接时列出提示"""
        with patch("loom.providers.mcp.http_client.HTTPX_AVAILABLE", True):
            client = HttpMCPClient(
                provider_id="test-provider",
                base_url="http://localhost:8000",
            )

            with pytest.raises(RuntimeError, match="Not connected"):
                await client.list_prompts()


class TestHttpMCPClientGetPrompt:
    """测试获取提示功能"""

    @pytest.mark.asyncio
    async def test_get_prompt_success(self):
        """测试成功获取提示"""
        with patch("loom.providers.mcp.http_client.HTTPX_AVAILABLE", True):
            client = HttpMCPClient(
                provider_id="test-provider",
                base_url="http://localhost:8000",
            )

            mock_response = Mock()
            mock_response.json.return_value = {
                "result": {
                    "messages": [
                        {"content": {"text": "Message 1"}},
                        {"content": {"text": "Message 2"}},
                    ]
                }
            }
            mock_response.raise_for_status = Mock()

            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            client._client = mock_client
            client._connected = True

            prompt = await client.get_prompt("test_prompt", {"arg1": "value1"})

            assert "Message 1" in prompt
            assert "Message 2" in prompt

    @pytest.mark.asyncio
    async def test_get_prompt_empty(self):
        """测试获取空提示"""
        with patch("loom.providers.mcp.http_client.HTTPX_AVAILABLE", True):
            client = HttpMCPClient(
                provider_id="test-provider",
                base_url="http://localhost:8000",
            )

            mock_response = Mock()
            mock_response.json.return_value = {"result": {"messages": []}}
            mock_response.raise_for_status = Mock()

            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            client._client = mock_client
            client._connected = True

            prompt = await client.get_prompt("test_prompt", {})

            assert prompt == ""

    @pytest.mark.asyncio
    async def test_get_prompt_not_connected(self):
        """测试未连接时获取提示"""
        with patch("loom.providers.mcp.http_client.HTTPX_AVAILABLE", True):
            client = HttpMCPClient(
                provider_id="test-provider",
                base_url="http://localhost:8000",
            )

            with pytest.raises(RuntimeError, match="Not connected"):
                await client.get_prompt("test_prompt", {})


class TestHttpMCPClientSendRequest:
    """测试发送请求功能"""

    @pytest.mark.asyncio
    async def test_send_request_success(self):
        """测试成功发送请求"""
        with patch("loom.providers.mcp.http_client.HTTPX_AVAILABLE", True):
            client = HttpMCPClient(
                provider_id="test-provider",
                base_url="http://localhost:8000",
            )

            mock_response = Mock()
            mock_response.json.return_value = {"result": {"key": "value"}}
            mock_response.raise_for_status = Mock()

            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            client._client = mock_client

            result = await client._send_request("test/method", {"param": "value"})

            assert result == {"key": "value"}
            assert client._request_id == 1

    @pytest.mark.asyncio
    async def test_send_request_with_error(self):
        """测试请求返回错误"""
        with patch("loom.providers.mcp.http_client.HTTPX_AVAILABLE", True):
            client = HttpMCPClient(
                provider_id="test-provider",
                base_url="http://localhost:8000",
            )

            mock_response = Mock()
            mock_response.json.return_value = {
                "error": {"message": "Test error", "code": -1}
            }
            mock_response.raise_for_status = Mock()

            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            client._client = mock_client

            with pytest.raises(RuntimeError, match="MCP error: Test error"):
                await client._send_request("test/method", {})

    @pytest.mark.asyncio
    async def test_send_request_with_string_error(self):
        """测试请求返回字符串格式的错误"""
        with patch("loom.providers.mcp.http_client.HTTPX_AVAILABLE", True):
            client = HttpMCPClient(
                provider_id="test-provider",
                base_url="http://localhost:8000",
            )

            mock_response = Mock()
            # 返回字符串格式的错误而不是字典
            mock_response.json.return_value = {"error": "Simple error message"}
            mock_response.raise_for_status = Mock()

            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            client._client = mock_client

            with pytest.raises(RuntimeError, match="MCP error: Simple error message"):
                await client._send_request("test/method", {})

    @pytest.mark.asyncio
    async def test_send_request_no_client(self):
        """测试没有客户端时发送请求"""
        with patch("loom.providers.mcp.http_client.HTTPX_AVAILABLE", True):
            client = HttpMCPClient(
                provider_id="test-provider",
                base_url="http://localhost:8000",
            )

            with pytest.raises(RuntimeError, match="Client not available"):
                await client._send_request("test/method", {})

    @pytest.mark.asyncio
    async def test_send_request_non_dict_result(self):
        """测试返回非字典结果"""
        with patch("loom.providers.mcp.http_client.HTTPX_AVAILABLE", True):
            client = HttpMCPClient(
                provider_id="test-provider",
                base_url="http://localhost:8000",
            )

            mock_response = Mock()
            mock_response.json.return_value = {"result": "not a dict"}
            mock_response.raise_for_status = Mock()

            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            client._client = mock_client

            result = await client._send_request("test/method", {})

            assert result == {}
