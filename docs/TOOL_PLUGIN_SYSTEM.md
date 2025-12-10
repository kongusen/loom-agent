# Tool Plugin System Documentation

loom-agent 工具插件系统完整指南

**版本**: 0.1.0
**最后更新**: 2024-12-10

---

## 目录

1. [概述](#概述)
2. [快速开始](#快速开始)
3. [核心概念](#核心概念)
4. [创建插件](#创建插件)
5. [使用插件](#使用插件)
6. [API 参考](#api-参考)
7. [最佳实践](#最佳实践)
8. [示例](#示例)

---

## 概述

loom-agent 工具插件系统允许您扩展框架功能，通过创建和安装自定义工具插件。

### 特性

✅ **灵活的插件架构** - 基于标准 Python 模块
✅ **简单的API** - 清晰的接口，易于上手
✅ **插件生命周期管理** - 安装、启用、禁用、卸载
✅ **自动验证** - 元数据验证和安全检查
✅ **插件发现** - 自动发现目录中的所有插件
✅ **标签和搜索** - 按标签、作者搜索插件
✅ **版本管理** - 语义化版本控制

---

## 快速开始

### 1. 安装示例插件

```python
from loom.plugins import ToolPluginManager

# 创建插件管理器
manager = ToolPluginManager()

# 从文件安装插件
await manager.install_from_file("plugins/weather_plugin.py")

# 使用插件工具
weather_tool = manager.get_tool("weather")
result = await weather_tool.run(location="San Francisco")
print(result)
```

### 2. 创建自定义插件

创建文件 `my_plugin.py`:

```python
from pydantic import BaseModel, Field
from loom.interfaces.tool import BaseTool
from loom.plugins import ToolPluginMetadata

# 1. 定义插件元数据
PLUGIN_METADATA = ToolPluginMetadata(
    name="my-plugin",
    version="1.0.0",
    author="Your Name <you@example.com>",
    description="My awesome plugin",
    tags=["utility", "demo"],
)

# 2. 定义工具输入
class MyToolInput(BaseModel):
    value: str = Field(..., description="Input value")

# 3. 定义工具
class MyTool(BaseTool):
    name = "my_tool"
    description = "My custom tool"
    args_schema = MyToolInput

    async def run(self, value: str, **kwargs) -> str:
        return f"Processed: {value}"
```

### 3. 使用自定义插件

```python
from loom.plugins import ToolPluginManager

manager = ToolPluginManager()

# 安装插件
await manager.install_from_file("my_plugin.py", enable=True)

# 使用工具
tool = manager.get_tool("my_tool")
result = await tool.run(value="test")
print(result)  # "Processed: test"
```

---

## 核心概念

### 插件组件层次

```
ToolPluginManager (高级管理)
    │
    ├── ToolPluginRegistry (注册表)
    │   └── 管理已注册的插件
    │
    └── ToolPluginLoader (加载器)
        └── 从文件/模块加载插件

ToolPlugin (插件包装器)
    ├── ToolPluginMetadata (元数据)
    └── Tool Class (工具实现)
```

### 插件生命周期

```
1. LOADED     - 插件已加载，但未启用
2. ENABLED    - 插件已启用，工具可用
3. DISABLED   - 插件已禁用，工具不可用
4. ERROR      - 插件有错误
```

### 插件结构

每个插件文件必须包含：

1. **PLUGIN_METADATA** (必需) - `ToolPluginMetadata` 实例
2. **Tool Class** (必需) - 继承自 `BaseTool` 的工具类
3. **Input Schema** (推荐) - Pydantic 模型定义输入参数

---

## 创建插件

### 最小插件示例

```python
from pydantic import BaseModel, Field
from loom.interfaces.tool import BaseTool
from loom.plugins import ToolPluginMetadata

PLUGIN_METADATA = ToolPluginMetadata(
    name="hello-plugin",
    version="1.0.0",
    author="Demo",
    description="Hello world plugin"
)

class HelloInput(BaseModel):
    name: str = Field(..., description="Name to greet")

class HelloTool(BaseTool):
    name = "hello"
    description = "Say hello"
    args_schema = HelloInput

    async def run(self, name: str, **kwargs) -> str:
        return f"Hello, {name}!"
```

### 完整插件示例

```python
from pydantic import BaseModel, Field
from loom.interfaces.tool import BaseTool
from loom.plugins import ToolPluginMetadata

# 元数据（完整）
PLUGIN_METADATA = ToolPluginMetadata(
    name="advanced-plugin",
    version="1.2.3",
    author="Developer <dev@example.com>",
    description="Advanced plugin with all features",
    homepage="https://github.com/user/plugin",
    license="MIT",
    dependencies=["requests>=2.28.0"],  # 依赖包
    loom_min_version="0.1.0",
    tags=["network", "api", "utility"],
    tool_names=[]  # 自动填充
)

# 输入模式
class AdvancedInput(BaseModel):
    url: str = Field(..., description="URL to fetch")
    method: str = Field("GET", description="HTTP method")
    timeout: int = Field(30, description="Timeout in seconds")

# 工具实现
class AdvancedTool(BaseTool):
    name = "advanced_tool"
    description = "Advanced HTTP request tool"
    args_schema = AdvancedInput

    # 编排属性
    is_read_only = False
    category = "network"
    requires_confirmation = False

    async def run(
        self,
        url: str,
        method: str = "GET",
        timeout: int = 30,
        **kwargs
    ) -> str:
        import requests

        try:
            response = requests.request(
                method=method,
                url=url,
                timeout=timeout
            )
            return f"Status: {response.status_code}\n{response.text}"
        except Exception as e:
            return f"Error: {str(e)}"
```

### 元数据验证规则

#### 插件名称 (name)
- 必须是小写字母开头
- 只能包含小写字母、数字和连字符
- 示例: `"my-plugin"`, `"http-client-v2"`
- ❌ 错误: `"MyPlugin"`, `"my_plugin"`, `"123plugin"`

#### 版本 (version)
- 必须遵循语义化版本 (Semantic Versioning)
- 格式: `MAJOR.MINOR.PATCH`
- 示例: `"1.0.0"`, `"2.3.1"`, `"0.1.0"`
- ❌ 错误: `"1.0"`, `"v1.0.0"`, `"1.0.0-beta"`

#### 依赖 (dependencies)
- 使用 pip 包名称和版本约束
- 示例: `["requests>=2.28.0", "pydantic>=2.0.0"]`

---

## 使用插件

### 使用 ToolPluginManager (推荐)

```python
from loom.plugins import ToolPluginManager

# 创建管理器
manager = ToolPluginManager(plugin_dir="./plugins")

# 安装插件
await manager.install_from_file("plugins/my_plugin.py", enable=True)

# 发现并安装所有插件
plugins = await manager.discover_and_install("./plugins", enable=True)

# 获取工具
tool = manager.get_tool("my_tool")

# 使用工具
result = await tool.run(param="value")

# 列出已安装插件
for plugin in manager.list_installed():
    print(f"{plugin.metadata.name} v{plugin.metadata.version}")

# 启用/禁用插件
manager.disable("my-plugin")
manager.enable("my-plugin")

# 卸载插件
manager.uninstall("my-plugin")

# 获取统计信息
stats = manager.get_stats()
print(f"Total plugins: {stats['total_plugins']}")
print(f"Enabled: {stats['enabled']}")
```

### 使用 ToolPluginRegistry

```python
from loom.plugins import ToolPluginRegistry, ToolPlugin, ToolPluginMetadata

# 创建注册表
registry = ToolPluginRegistry()

# 创建插件
metadata = ToolPluginMetadata(
    name="test-plugin",
    version="1.0.0",
    author="Test",
    description="Test plugin"
)
plugin = ToolPlugin(tool_class=MyTool, metadata=metadata)

# 注册插件
registry.register(plugin)
plugin.enable()

# 获取工具
tool = registry.get_tool("my_tool")

# 搜索插件
finance_plugins = registry.search_by_tag("finance")
loom_plugins = registry.search_by_author("Loom Team")

# 列出插件（带过滤）
from loom.plugins import PluginStatus

enabled = registry.list_plugins(status_filter=PluginStatus.ENABLED)
disabled = registry.list_plugins(status_filter=PluginStatus.DISABLED)

# 启用/禁用
registry.enable_plugin("my-plugin")
registry.disable_plugin("my-plugin")

# 卸载
registry.unregister("my-plugin")
```

### 使用 ToolPluginLoader

```python
from loom.plugins import ToolPluginLoader, ToolPluginRegistry

registry = ToolPluginRegistry()
loader = ToolPluginLoader(registry=registry)

# 从文件加载
plugin = await loader.load_from_file("plugins/my_plugin.py", auto_register=True)

# 从模块加载
plugin = await loader.load_from_module("my_package.my_plugin", auto_register=True)

# 发现目录中的所有插件
plugins = await loader.discover_plugins("./plugins", auto_register=True)
print(f"Discovered {len(plugins)} plugins")
```

---

## API 参考

### ToolPluginMetadata

```python
@dataclass
class ToolPluginMetadata:
    name: str                          # 插件名称 (必需)
    version: str                       # 版本 (必需)
    author: str                        # 作者 (必需)
    description: str                   # 描述 (必需)
    homepage: Optional[str] = None     # 主页 URL
    license: str = "MIT"               # 许可证
    dependencies: List[str] = []       # 依赖包
    loom_min_version: str = "0.1.0"    # 最低 loom 版本
    tags: List[str] = []               # 标签
    tool_names: List[str] = []         # 工具名称（自动填充）

    def to_dict() -> Dict[str, Any]
    def to_json() -> str
    @classmethod
    def from_dict(data: Dict[str, Any]) -> ToolPluginMetadata
    @classmethod
    def from_json(json_str: str) -> ToolPluginMetadata
```

### ToolPlugin

```python
@dataclass
class ToolPlugin:
    tool_class: Type[BaseTool]         # 工具类
    metadata: ToolPluginMetadata       # 元数据
    status: PluginStatus = LOADED      # 状态
    error_message: Optional[str] = None

    def create_tool(**kwargs) -> BaseTool
    def enable() -> None
    def disable() -> None
    def set_error(error_message: str) -> None
```

### ToolPluginRegistry

```python
class ToolPluginRegistry:
    def register(plugin: ToolPlugin) -> None
    def unregister(plugin_name: str) -> None
    def get_plugin(plugin_name: str) -> Optional[ToolPlugin]
    def get_tool(tool_name: str, **kwargs) -> Optional[BaseTool]

    def list_plugins(status_filter: Optional[PluginStatus] = None) -> List[ToolPlugin]
    def search_by_tag(tag: str) -> List[ToolPlugin]
    def search_by_author(author: str) -> List[ToolPlugin]

    def enable_plugin(plugin_name: str) -> None
    def disable_plugin(plugin_name: str) -> None

    def get_stats() -> Dict[str, Any]
```

### ToolPluginLoader

```python
class ToolPluginLoader:
    async def load_from_file(
        file_path: str | Path,
        auto_register: bool = True
    ) -> ToolPlugin

    async def load_from_module(
        module_name: str,
        auto_register: bool = True
    ) -> ToolPlugin

    async def discover_plugins(
        directory: str | Path,
        auto_register: bool = True
    ) -> List[ToolPlugin]
```

### ToolPluginManager

```python
class ToolPluginManager:
    async def install_from_file(file_path: str | Path, enable: bool = True) -> ToolPlugin
    async def install_from_module(module_name: str, enable: bool = True) -> ToolPlugin
    async def discover_and_install(directory: Optional[str | Path] = None, enable: bool = True) -> List[ToolPlugin]

    def uninstall(plugin_name: str) -> None
    def enable(plugin_name: str) -> None
    def disable(plugin_name: str) -> None

    def list_installed(status_filter: Optional[PluginStatus] = None) -> List[ToolPlugin]
    def get_tool(tool_name: str, **kwargs) -> Optional[BaseTool]
    def get_stats() -> Dict[str, Any]
```

---

## 最佳实践

### 1. 插件命名

✅ **推荐**:
- `weather-lookup` - 描述性强
- `github-api-client` - 清晰明了
- `sentiment-analyzer` - 功能明确

❌ **不推荐**:
- `plugin1` - 不描述性
- `MyPlugin` - 大写
- `my_plugin` - 下划线

### 2. 版本管理

遵循语义化版本控制：

- **MAJOR** (1.0.0 → 2.0.0): 不兼容的 API 变更
- **MINOR** (1.0.0 → 1.1.0): 向后兼容的新功能
- **PATCH** (1.0.0 → 1.0.1): 向后兼容的 bug 修复

### 3. 错误处理

在工具中处理错误并返回友好消息：

```python
class MyTool(BaseTool):
    async def run(self, param: str, **kwargs) -> str:
        try:
            # 处理逻辑
            result = process(param)
            return f"Success: {result}"
        except ValueError as e:
            return f"Error: Invalid parameter - {str(e)}"
        except Exception as e:
            return f"Error: {type(e).__name__}: {str(e)}"
```

### 4. 依赖管理

仅列出直接依赖：

```python
PLUGIN_METADATA = ToolPluginMetadata(
    name="my-plugin",
    version="1.0.0",
    author="Me",
    description="Plugin",
    dependencies=[
        "requests>=2.28.0",  # HTTP 客户端
        "pydantic>=2.0.0",   # 数据验证
    ]
)
```

### 5. 文档

在工具类中添加详细文档：

```python
class MyTool(BaseTool):
    """
    My tool does X, Y, and Z.

    This tool is useful for scenarios where you need to...

    Example:
        ```python
        tool = MyTool()
        result = await tool.run(param="value")
        ```

    Args:
        param: Description of parameter

    Returns:
        Description of return value

    Raises:
        ValueError: When param is invalid
    """
    name = "my_tool"
    description = "Brief one-line description"
    args_schema = MyToolInput

    async def run(self, param: str, **kwargs) -> str:
        ...
```

### 6. 测试

为插件创建测试：

```python
import pytest

@pytest.mark.asyncio
async def test_my_tool():
    """Test my tool"""
    tool = MyTool()
    result = await tool.run(param="test")
    assert "test" in result

@pytest.mark.asyncio
async def test_my_tool_error_handling():
    """Test error handling"""
    tool = MyTool()
    result = await tool.run(param="invalid")
    assert "Error" in result
```

---

## 示例

### 示例 1: 天气查询插件

```python
# weather_plugin.py
from pydantic import BaseModel, Field
from loom.interfaces.tool import BaseTool
from loom.plugins import ToolPluginMetadata

PLUGIN_METADATA = ToolPluginMetadata(
    name="weather-lookup",
    version="1.0.0",
    author="Weather Team <weather@example.com>",
    description="Get weather information for any location",
    tags=["weather", "data", "api"],
    dependencies=["requests>=2.28.0"]
)

class WeatherInput(BaseModel):
    location: str = Field(..., description="City name")
    units: str = Field("celsius", description="Temperature units")

class WeatherTool(BaseTool):
    name = "weather"
    description = "Get current weather for a location"
    args_schema = WeatherInput
    is_read_only = True
    category = "network"

    async def run(self, location: str, units: str = "celsius", **kwargs) -> str:
        # 实现天气查询逻辑
        temp = 22 if units == "celsius" else 72
        return f"Weather in {location}: {temp}°{units[0].upper()}"
```

使用：

```python
from loom.plugins import ToolPluginManager

manager = ToolPluginManager()
await manager.install_from_file("weather_plugin.py", enable=True)

weather = manager.get_tool("weather")
result = await weather.run(location="Tokyo", units="celsius")
print(result)  # "Weather in Tokyo: 22°C"
```

### 示例 2: 多工具插件

```python
# utils_plugin.py
from pydantic import BaseModel, Field
from loom.interfaces.tool import BaseTool
from loom.plugins import ToolPluginMetadata

PLUGIN_METADATA = ToolPluginMetadata(
    name="text-utils",
    version="1.0.0",
    author="Utils Team",
    description="Text utility tools",
    tags=["text", "utility"],
    tool_names=["uppercase", "lowercase", "reverse"]  # 多个工具
)

class TextInput(BaseModel):
    text: str = Field(..., description="Input text")

class UppercaseTool(BaseTool):
    name = "uppercase"
    description = "Convert text to uppercase"
    args_schema = TextInput

    async def run(self, text: str, **kwargs) -> str:
        return text.upper()

class LowercaseTool(BaseTool):
    name = "lowercase"
    description = "Convert text to lowercase"
    args_schema = TextInput

    async def run(self, text: str, **kwargs) -> str:
        return text.lower()

class ReverseTool(BaseTool):
    name = "reverse"
    description = "Reverse text"
    args_schema = TextInput

    async def run(self, text: str, **kwargs) -> str:
        return text[::-1]
```

---

## 故障排除

### 常见错误

#### 1. "Invalid plugin name"

**原因**: 插件名称不符合命名规范
**解决**: 使用小写字母和连字符，例如 `"my-plugin"`

#### 2. "Invalid version"

**原因**: 版本号不符合语义化版本
**解决**: 使用格式 `"MAJOR.MINOR.PATCH"`，例如 `"1.0.0"`

#### 3. "Tool class must inherit from BaseTool"

**原因**: 工具类没有继承 `BaseTool`
**解决**: 确保工具类定义为 `class MyTool(BaseTool):`

#### 4. "Plugin is already registered"

**原因**: 尝试注册同名插件
**解决**: 先卸载旧插件或使用不同名称

#### 5. "Tool name conflicts"

**原因**: 多个插件提供同名工具
**解决**: 确保每个工具有唯一名称

### 调试技巧

```python
# 1. 检查插件状态
plugin = manager.registry.get_plugin("my-plugin")
print(f"Status: {plugin.status}")
print(f"Error: {plugin.error_message}")

# 2. 列出所有工具
stats = manager.get_stats()
print(f"Total tools: {stats['total_tools']}")

# 3. 查看注册表
for plugin in manager.list_installed():
    print(f"{plugin.metadata.name}: {plugin.metadata.tool_names}")

# 4. 测试插件加载
try:
    plugin = await manager.install_from_file("my_plugin.py")
    print("✓ Plugin loaded successfully")
except Exception as e:
    print(f"✗ Error loading plugin: {e}")
```

---

## 下一步

- 查看 [示例插件](../examples/tool_plugins/) 获取更多灵感
- 运行 [plugin_demo.py](../examples/plugin_demo.py) 查看完整演示
- 阅读 [BaseTool 文档](tool_interfaces.md) 了解工具接口
- 探索 [Crew 系统文档](crew_system.md) 了解团队协作

---

**需要帮助?**
- 提交 Issue: https://github.com/loom-agent/loom/issues
- 讨论: https://github.com/loom-agent/loom/discussions
- 文档: https://loom-agent.github.io/docs
