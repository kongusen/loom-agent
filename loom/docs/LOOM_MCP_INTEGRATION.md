# Loom Framework - MCP (Model Context Protocol) 集成设计

> **目标**: 让 Loom 无缝接入整个 MCP 生态系统，开发者可以直接使用任何 MCP Server 提供的工具

---

## 🎯 1. MCP 集成愿景

### 1.1 为什么支持 MCP？

**MCP (Model Context Protocol)** 是 Anthropic 推出的开放标准，用于：
- 📦 标准化工具定义和调用
- 🔌 实现插件的即插即用
- 🌐 构建跨平台的工具生态

**集成 MCP 的价值**:
```
Loom + MCP = 🚀
├── 直接访问 MCP 生态的所有工具
├── 开发者无需重新实现工具
├── 社区贡献的工具可直接使用
└── 与其他 AI 框架互操作
```

### 1.2 集成目标

```python
# 愿景: 开发者可以这样使用 MCP 工具

from loom import Agent
from loom.llms import OpenAI
from loom.mcp import MCPToolRegistry

# 1. 自动发现本地 MCP servers
registry = MCPToolRegistry()
await registry.discover_local_servers()

# 2. 加载指定 MCP server 的所有工具
tools = await registry.load_from_server("filesystem")
# 或者加载多个 server
tools = await registry.load_servers(["filesystem", "github", "postgres"])

# 3. 直接在 Agent 中使用
agent = Agent(
    llm=OpenAI(api_key="..."),
    tools=tools
)

result = await agent.run("Read the file config.json and create a GitHub issue")
```

---

## 🏗️ 2. MCP 适配层架构

```
┌─────────────────────────────────────────────────────┐
│                   Loom Agent                        │
│              (统一的 Agent 接口)                    │
└────────────────────┬────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────┐
│              MCP Adapter Layer                      │
│          (Loom ↔ MCP 协议转换)                      │
│                                                     │
│  ┌──────────────┐  ┌──────────────┐               │
│  │ MCPTool      │  │ MCPRegistry  │               │
│  │ Adapter      │  │ (工具注册)    │               │
│  └──────────────┘  └──────────────┘               │
│                                                     │
│  ┌──────────────┐  ┌──────────────┐               │
│  │ MCPServer    │  │ MCPTransport │               │
│  │ Manager      │  │ (通信层)      │               │
│  └──────────────┘  └──────────────┘               │
└────────────────────┬────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────┐
│              MCP Protocol                           │
│         (Anthropic 标准协议)                        │
│                                                     │
│  ┌──────────────┐  ┌──────────────┐               │
│  │ JSON-RPC 2.0 │  │ stdio/SSE    │               │
│  └──────────────┘  └──────────────┘               │
└────────────────────┬────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────┐
│           MCP Servers (External)                    │
│                                                     │
│  📦 filesystem   📦 github   📦 postgres           │
│  📦 web-browser  📦 slack    📦 google-drive       │
└─────────────────────────────────────────────────────┘
```

---

## 🔌 3. 核心组件设计

### 3.1 MCPTool - MCP 工具适配器

```python
# loom/mcp/tool_adapter.py
from loom.interfaces.tool import BaseTool
from pydantic import BaseModel, create_model
from typing import Dict, Any

class MCPTool(BaseTool):
    """MCP 工具适配器 - 将 MCP Tool 转换为 Loom Tool"""

    def __init__(self, mcp_tool_spec: Dict, mcp_client: 'MCPClient'):
        """
        Args:
            mcp_tool_spec: MCP 工具定义 (JSON Schema)
            mcp_client: MCP 客户端用于实际调用
        """
        self.mcp_spec = mcp_tool_spec
        self.mcp_client = mcp_client

        # 从 MCP spec 提取元信息
        self.name = mcp_tool_spec['name']
        self.description = mcp_tool_spec.get('description', '')

        # 动态生成 Pydantic schema
        self.args_schema = self._build_pydantic_schema(
            mcp_tool_spec.get('inputSchema', {})
        )

    def _build_pydantic_schema(self, json_schema: Dict) -> BaseModel:
        """将 MCP 的 JSON Schema 转换为 Pydantic Model"""
        fields = {}
        properties = json_schema.get('properties', {})
        required = json_schema.get('required', [])

        for field_name, field_spec in properties.items():
            field_type = self._json_type_to_python(field_spec.get('type', 'string'))
            field_description = field_spec.get('description', '')

            # 构建 Field 定义
            if field_name in required:
                fields[field_name] = (field_type, Field(..., description=field_description))
            else:
                default = field_spec.get('default', None)
                fields[field_name] = (field_type, Field(default, description=field_description))

        # 动态创建 Pydantic 模型
        return create_model(
            f"{self.name.title()}Args",
            **fields
        )

    def _json_type_to_python(self, json_type: str) -> type:
        """JSON Schema 类型转 Python 类型"""
        type_mapping = {
            'string': str,
            'integer': int,
            'number': float,
            'boolean': bool,
            'array': list,
            'object': dict,
        }
        return type_mapping.get(json_type, str)

    async def run(self, **kwargs) -> Any:
        """执行 MCP 工具"""
        # 通过 MCP 客户端调用远程工具
        result = await self.mcp_client.call_tool(
            tool_name=self.name,
            arguments=kwargs
        )

        # 处理 MCP 响应
        if result.get('isError'):
            raise MCPToolError(result.get('content', [{}])[0].get('text', 'Unknown error'))

        # 提取结果内容
        content = result.get('content', [])
        if content and len(content) > 0:
            return content[0].get('text', '')

        return result

    @property
    def is_concurrency_safe(self) -> bool:
        """MCP 工具默认并发安全 (每个调用独立)"""
        return True
```

### 3.2 MCPClient - MCP 通信客户端

```python
# loom/mcp/client.py
import asyncio
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

@dataclass
class MCPServerConfig:
    """MCP Server 配置"""
    command: str  # e.g., "npx"
    args: List[str]  # e.g., ["-y", "@modelcontextprotocol/server-filesystem", "/path"]
    env: Optional[Dict[str, str]] = None


class MCPClient:
    """MCP 客户端 - 通过 stdio 与 MCP Server 通信"""

    def __init__(self, server_config: MCPServerConfig):
        self.config = server_config
        self.process = None
        self.request_id = 0
        self._response_futures = {}

    async def connect(self):
        """启动 MCP Server 子进程"""
        self.process = await asyncio.create_subprocess_exec(
            self.config.command,
            *self.config.args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=self.config.env
        )

        # 启动后台任务读取响应
        asyncio.create_task(self._read_responses())

        # 发送初始化请求
        await self._send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "loom-framework",
                "version": "2.0.0"
            }
        })

    async def disconnect(self):
        """关闭连接"""
        if self.process:
            self.process.terminate()
            await self.process.wait()

    async def list_tools(self) -> List[Dict]:
        """列出 MCP Server 提供的所有工具"""
        response = await self._send_request("tools/list", {})
        return response.get('tools', [])

    async def call_tool(self, tool_name: str, arguments: Dict) -> Dict:
        """调用 MCP 工具"""
        response = await self._send_request("tools/call", {
            "name": tool_name,
            "arguments": arguments
        })
        return response

    async def _send_request(self, method: str, params: Dict) -> Dict:
        """发送 JSON-RPC 请求"""
        self.request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": method,
            "params": params
        }

        # 创建 Future 等待响应
        future = asyncio.Future()
        self._response_futures[self.request_id] = future

        # 发送请求
        request_line = json.dumps(request) + "\n"
        self.process.stdin.write(request_line.encode())
        await self.process.stdin.drain()

        # 等待响应
        return await future

    async def _read_responses(self):
        """后台任务: 持续读取 MCP Server 响应"""
        while True:
            try:
                line = await self.process.stdout.readline()
                if not line:
                    break

                response = json.loads(line.decode())

                # 处理响应
                if 'id' in response:
                    request_id = response['id']
                    if request_id in self._response_futures:
                        future = self._response_futures.pop(request_id)
                        if 'error' in response:
                            future.set_exception(MCPError(response['error']))
                        else:
                            future.set_result(response.get('result', {}))

            except Exception as e:
                print(f"Error reading MCP response: {e}")
                break


class MCPError(Exception):
    """MCP 错误"""
    pass


class MCPToolError(Exception):
    """MCP 工具执行错误"""
    pass
```

### 3.3 MCPToolRegistry - MCP 工具注册中心

```python
# loom/mcp/registry.py
from typing import List, Dict, Optional
from pathlib import Path
import json

class MCPToolRegistry:
    """MCP 工具注册中心 - 管理 MCP Servers 和 Tools"""

    def __init__(self, config_path: Optional[str] = None):
        """
        Args:
            config_path: MCP 配置文件路径 (默认: ~/.loom/mcp.json)
        """
        self.config_path = config_path or Path.home() / ".loom" / "mcp.json"
        self.servers: Dict[str, MCPClient] = {}
        self.tools: Dict[str, MCPTool] = {}

    async def discover_local_servers(self):
        """自动发现本地安装的 MCP Servers"""
        # 读取配置文件
        if not self.config_path.exists():
            print(f"No MCP config found at {self.config_path}")
            return

        with open(self.config_path) as f:
            config = json.load(f)

        # 加载配置的 servers
        for server_name, server_config in config.get('mcpServers', {}).items():
            await self.add_server(server_name, server_config)

    async def add_server(self, name: str, config: Dict):
        """添加 MCP Server"""
        # 创建客户端
        server_config = MCPServerConfig(
            command=config['command'],
            args=config.get('args', []),
            env=config.get('env')
        )

        client = MCPClient(server_config)
        await client.connect()

        self.servers[name] = client

        # 加载该 server 的所有工具
        await self._load_server_tools(name, client)

    async def _load_server_tools(self, server_name: str, client: MCPClient):
        """从 MCP Server 加载工具"""
        tools_spec = await client.list_tools()

        for tool_spec in tools_spec:
            tool = MCPTool(mcp_tool_spec=tool_spec, mcp_client=client)
            self.tools[f"{server_name}:{tool.name}"] = tool

    async def load_from_server(self, server_name: str) -> List[MCPTool]:
        """加载指定 server 的所有工具"""
        return [
            tool for key, tool in self.tools.items()
            if key.startswith(f"{server_name}:")
        ]

    async def load_servers(self, server_names: List[str]) -> List[MCPTool]:
        """加载多个 server 的工具"""
        tools = []
        for server_name in server_names:
            tools.extend(await self.load_from_server(server_name))
        return tools

    async def get_tool(self, tool_identifier: str) -> Optional[MCPTool]:
        """获取指定工具

        Args:
            tool_identifier: "server_name:tool_name" 或 "tool_name"
        """
        if tool_identifier in self.tools:
            return self.tools[tool_identifier]

        # 如果没有指定 server，尝试查找第一个匹配的工具
        for key, tool in self.tools.items():
            if key.endswith(f":{tool_identifier}"):
                return tool

        return None

    async def list_all_tools(self) -> Dict[str, List[str]]:
        """列出所有可用工具 (按 server 分组)"""
        grouped = {}
        for key in self.tools.keys():
            server_name, tool_name = key.split(':', 1)
            if server_name not in grouped:
                grouped[server_name] = []
            grouped[server_name].append(tool_name)
        return grouped

    async def close(self):
        """关闭所有 MCP 连接"""
        for client in self.servers.values():
            await client.disconnect()
```

### 3.4 配置文件示例

```json
// ~/.loom/mcp.json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/Users/username/projects"]
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_TOKEN": "ghp_xxxxxxxxxxxxx"
      }
    },
    "postgres": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres"],
      "env": {
        "DATABASE_URL": "postgresql://user:pass@localhost/db"
      }
    },
    "slack": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-slack"],
      "env": {
        "SLACK_BOT_TOKEN": "xoxb-xxxxxxxxxxxxx"
      }
    }
  }
}
```

---

## 🚀 4. 使用示例

### 4.1 基础用法 - 自动发现

```python
# example_mcp_01_auto_discovery.py
from loom import Agent
from loom.llms import OpenAI
from loom.mcp import MCPToolRegistry

async def main():
    # 1. 创建注册中心
    registry = MCPToolRegistry()

    # 2. 自动发现本地配置的 MCP servers
    await registry.discover_local_servers()

    # 3. 查看可用工具
    all_tools = await registry.list_all_tools()
    print("Available MCP Tools:")
    for server, tools in all_tools.items():
        print(f"  [{server}]: {', '.join(tools)}")

    # 4. 加载所有工具
    tools = list(registry.tools.values())

    # 5. 创建 Agent
    agent = Agent(
        llm=OpenAI(api_key="..."),
        tools=tools
    )

    # 6. 使用
    result = await agent.run(
        "Read the file README.md and summarize it"
    )
    print(result)

    # 7. 清理
    await registry.close()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

### 4.2 选择性加载

```python
# example_mcp_02_selective_loading.py
from loom import Agent
from loom.llms import OpenAI
from loom.mcp import MCPToolRegistry

async def main():
    registry = MCPToolRegistry()
    await registry.discover_local_servers()

    # 只加载文件系统和 GitHub 工具
    tools = await registry.load_servers(["filesystem", "github"])

    agent = Agent(
        llm=OpenAI(api_key="..."),
        tools=tools
    )

    result = await agent.run(
        "Read config.json and create a GitHub issue about the config update"
    )

    await registry.close()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

### 4.3 混合使用 (Loom 原生工具 + MCP 工具)

```python
# example_mcp_03_hybrid.py
from loom import Agent
from loom.llms import OpenAI
from loom.tools import Calculator, WebSearch  # Loom 原生工具
from loom.mcp import MCPToolRegistry

async def main():
    # 加载 MCP 工具
    registry = MCPToolRegistry()
    await registry.discover_local_servers()
    mcp_tools = await registry.load_servers(["filesystem", "postgres"])

    # 混合使用
    all_tools = [
        Calculator(),      # Loom 原生工具
        WebSearch(),       # Loom 原生工具
        *mcp_tools         # MCP 工具
    ]

    agent = Agent(
        llm=OpenAI(api_key="..."),
        tools=all_tools
    )

    result = await agent.run(
        "Query the database for sales data, calculate the average, "
        "and save the result to report.txt"
    )

    await registry.close()
```

### 4.4 动态添加 MCP Server

```python
# example_mcp_04_dynamic.py
from loom.mcp import MCPToolRegistry

async def main():
    registry = MCPToolRegistry()

    # 动态添加一个新的 MCP server
    await registry.add_server("custom-api", {
        "command": "node",
        "args": ["./my-custom-mcp-server.js"],
        "env": {"API_KEY": "xxx"}
    })

    # 使用新添加的工具
    tools = await registry.load_from_server("custom-api")
    print(f"Loaded {len(tools)} tools from custom-api")

    await registry.close()
```

### 4.5 工具命名空间管理

```python
# example_mcp_05_namespaces.py
from loom.mcp import MCPToolRegistry

async def main():
    registry = MCPToolRegistry()
    await registry.discover_local_servers()

    # 使用完整标识符获取工具
    file_read = await registry.get_tool("filesystem:read_file")
    github_create_issue = await registry.get_tool("github:create_issue")

    # 或使用简短名称 (会返回第一个匹配)
    read_tool = await registry.get_tool("read_file")

    print(f"Tool: {file_read.name}")
    print(f"Description: {file_read.description}")
```

---

## 🎨 5. 高级特性

### 5.1 MCP 工具过滤器

```python
# loom/mcp/filters.py
from typing import List, Callable

class MCPToolFilter:
    """MCP 工具过滤器"""

    @staticmethod
    def by_server(server_names: List[str]) -> Callable:
        """按 server 名称过滤"""
        def filter_fn(tool: MCPTool) -> bool:
            return any(tool.name.startswith(f"{s}:") for s in server_names)
        return filter_fn

    @staticmethod
    def by_category(categories: List[str]) -> Callable:
        """按分类过滤"""
        def filter_fn(tool: MCPTool) -> bool:
            tool_category = tool.mcp_spec.get('category', '')
            return tool_category in categories
        return filter_fn

    @staticmethod
    def exclude_dangerous() -> Callable:
        """排除危险工具 (删除、执行等)"""
        dangerous_keywords = ['delete', 'remove', 'execute', 'run', 'drop']

        def filter_fn(tool: MCPTool) -> bool:
            return not any(kw in tool.name.lower() for kw in dangerous_keywords)
        return filter_fn


# 使用示例
from loom.mcp import MCPToolRegistry
from loom.mcp.filters import MCPToolFilter

registry = MCPToolRegistry()
await registry.discover_local_servers()

# 只加载安全的文件系统工具
safe_tools = [
    tool for tool in await registry.load_from_server("filesystem")
    if MCPToolFilter.exclude_dangerous()(tool)
]
```

### 5.2 MCP 工具权限管理

```python
# loom/mcp/permissions.py
class MCPPermissionManager:
    """MCP 工具权限管理"""

    def __init__(self):
        self.rules = {
            "filesystem:read_file": "allow",
            "filesystem:write_file": "ask",
            "filesystem:delete_file": "deny",
            "github:create_issue": "allow",
            "postgres:*": "ask",  # 所有数据库操作需要确认
            "*:delete*": "deny",   # 所有删除操作拒绝
        }

    def check_permission(self, tool: MCPTool) -> str:
        """检查工具权限"""
        # 精确匹配
        if tool.name in self.rules:
            return self.rules[tool.name]

        # 通配符匹配
        for pattern, permission in self.rules.items():
            if self._match_pattern(tool.name, pattern):
                return permission

        return "deny"  # 默认拒绝

    def _match_pattern(self, name: str, pattern: str) -> bool:
        """通配符模式匹配"""
        import re
        regex = pattern.replace('*', '.*')
        return bool(re.match(f'^{regex}$', name))


# 集成到 Agent
from loom import Agent
from loom.mcp import MCPToolRegistry
from loom.mcp.permissions import MCPPermissionManager

registry = MCPToolRegistry()
await registry.discover_local_servers()
tools = list(registry.tools.values())

agent = Agent(
    llm=OpenAI(api_key="..."),
    tools=tools,
    permission_manager=MCPPermissionManager()
)
```

### 5.3 MCP 工具缓存

```python
# loom/mcp/cache.py
from typing import Dict, Any
import hashlib
import json

class MCPToolCache:
    """MCP 工具结果缓存 - 避免重复调用"""

    def __init__(self, ttl: int = 300):
        """
        Args:
            ttl: 缓存过期时间 (秒)
        """
        self.cache: Dict[str, Any] = {}
        self.ttl = ttl

    def get_cache_key(self, tool_name: str, arguments: Dict) -> str:
        """生成缓存键"""
        data = f"{tool_name}:{json.dumps(arguments, sort_keys=True)}"
        return hashlib.md5(data.encode()).hexdigest()

    def get(self, tool_name: str, arguments: Dict) -> Any:
        """获取缓存"""
        key = self.get_cache_key(tool_name, arguments)
        if key in self.cache:
            cached = self.cache[key]
            import time
            if time.time() - cached['time'] < self.ttl:
                return cached['result']
        return None

    def set(self, tool_name: str, arguments: Dict, result: Any):
        """设置缓存"""
        key = self.get_cache_key(tool_name, arguments)
        import time
        self.cache[key] = {'result': result, 'time': time.time()}


# 使用缓存的 MCPTool
class CachedMCPTool(MCPTool):
    def __init__(self, mcp_tool_spec: Dict, mcp_client: 'MCPClient', cache: MCPToolCache):
        super().__init__(mcp_tool_spec, mcp_client)
        self.cache = cache

    async def run(self, **kwargs) -> Any:
        # 检查缓存
        cached = self.cache.get(self.name, kwargs)
        if cached is not None:
            return cached

        # 执行工具
        result = await super().run(**kwargs)

        # 缓存结果
        self.cache.set(self.name, kwargs, result)

        return result
```

---

## 📊 6. MCP 集成架构总览

```
┌───────────────────────────────────────────────────────────┐
│                    Developer Code                         │
│                                                           │
│  agent = Agent(llm=OpenAI(), tools=mcp_tools)            │
│  await agent.run("Use MCP tools to solve task")         │
└─────────────────────────┬─────────────────────────────────┘
                          │
┌─────────────────────────▼─────────────────────────────────┐
│                  Loom Core Framework                      │
│                                                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │  Agent   │→ │ Executor │→ │ Pipeline │              │
│  └──────────┘  └──────────┘  └──────────┘              │
└─────────────────────────┬─────────────────────────────────┘
                          │
┌─────────────────────────▼─────────────────────────────────┐
│              Loom MCP Adapter (loom.mcp)                  │
│                                                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  MCPTool     │  │ MCPRegistry  │  │ MCPClient    │  │
│  │  (Adapter)   │  │ (Discovery)  │  │ (Transport)  │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│                                                           │
│  Features:                                                │
│  • Schema Conversion (JSON Schema → Pydantic)            │
│  • Tool Caching                                           │
│  • Permission Management                                  │
│  • Error Handling                                         │
└─────────────────────────┬─────────────────────────────────┘
                          │ JSON-RPC over stdio
┌─────────────────────────▼─────────────────────────────────┐
│                  MCP Servers (External)                   │
│                                                           │
│  📦 @modelcontextprotocol/server-filesystem              │
│  📦 @modelcontextprotocol/server-github                  │
│  📦 @modelcontextprotocol/server-postgres                │
│  📦 Community MCP Servers                                │
└───────────────────────────────────────────────────────────┘
```

---

## 🌟 7. 优势与特性

### 7.1 核心优势

✅ **即插即用**: 无需重新实现工具，直接使用 MCP 生态
✅ **类型安全**: 自动将 JSON Schema 转换为 Pydantic 模型
✅ **命名空间**: `server:tool` 格式避免命名冲突
✅ **权限控制**: 与 Loom 的权限系统无缝集成
✅ **缓存优化**: 自动缓存工具调用结果
✅ **混合使用**: Loom 原生工具 + MCP 工具可以共存

### 7.2 与 LangChain MCP 集成对比

| 特性 | Loom MCP | LangChain MCP |
|------|----------|---------------|
| 自动发现 | ✅ 支持配置文件 | ❌ 手动配置 |
| 类型安全 | ✅ Pydantic 自动生成 | ⚠️  部分支持 |
| 命名空间 | ✅ `server:tool` | ❌ 无 |
| 工具过滤 | ✅ 内置过滤器 | ❌ 需手动实现 |
| 权限管理 | ✅ 统一权限系统 | ❌ 无 |
| 缓存 | ✅ 内置缓存 | ❌ 无 |

---

## 📦 8. 包结构

```
loom/
├── mcp/                      # MCP 集成模块
│   ├── __init__.py
│   ├── tool_adapter.py       # MCPTool 适配器
│   ├── client.py             # MCPClient (JSON-RPC)
│   ├── registry.py           # MCPToolRegistry
│   ├── filters.py            # 工具过滤器
│   ├── permissions.py        # 权限管理
│   ├── cache.py              # 工具缓存
│   └── exceptions.py         # MCP 异常
│
└── builtin/
    └── mcp_servers/          # 常用 MCP Server 配置模板
        ├── filesystem.json
        ├── github.json
        └── postgres.json
```

---

## 🚀 9. 快速开始指南

### Step 1: 安装 MCP Servers

```bash
# 安装常用 MCP servers (通过 npx)
npx -y @modelcontextprotocol/server-filesystem
npx -y @modelcontextprotocol/server-github
```

### Step 2: 配置 MCP

```bash
# 创建配置文件
mkdir -p ~/.loom
cat > ~/.loom/mcp.json << EOF
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "$HOME/projects"]
    }
  }
}
EOF
```

### Step 3: 使用 MCP 工具

```python
from loom import Agent
from loom.llms import OpenAI
from loom.mcp import MCPToolRegistry

async def main():
    # 自动发现并加载
    registry = MCPToolRegistry()
    await registry.discover_local_servers()
    tools = list(registry.tools.values())

    # 创建 Agent
    agent = Agent(llm=OpenAI(api_key="..."), tools=tools)

    # 使用
    result = await agent.run("List all Python files in the project")
    print(result)

    await registry.close()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

---

## 🎯 10. 总结

通过 MCP 集成，Loom 获得了：

1. **🌍 生态接入**: 直接访问整个 MCP 工具生态
2. **⚡ 快速扩展**: 无需实现工具，社区贡献即可使用
3. **🔒 安全可控**: 统一的权限和过滤机制
4. **🎨 灵活组合**: Loom 原生 + MCP 混合使用
5. **🚀 开发者友好**: 自动发现、类型安全、简单 API

**Loom + MCP = Agent 开发的完美组合！** 🎉
