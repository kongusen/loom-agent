# Tools API

**版本**: v0.1.6

Tools API 参考文档 - 工具创建和管理。

---

## 📋 目录

1. [@tool 装饰器](#tool-装饰器)
2. [ToolBuilder](#toolbuilder)
3. [BaseTool](#basetool)
4. [工具注册](#工具注册)
5. [完整示例](#完整示例)

---

## @tool 装饰器

### 概述

`@tool` 是创建工具的最简单方式，支持自动类型推断和文档生成。

```python
from loom.builtin import tool

@tool(name="calculator")
async def calculator(expression: str) -> float:
    """计算数学表达式"""
    return eval(expression)
```

### 函数签名

```python
def tool(
    name: Optional[str] = None,
    description: Optional[str] = None,
    **metadata
) -> Callable
```

#### 参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `name` | `str` | `None` | 工具名称（默认使用函数名） |
| `description` | `str` | `None` | 工具描述（默认使用 docstring） |
| `**metadata` | `Any` | - | 额外元数据 |

#### 返回值

装饰后的函数，实现 `BaseTool` 协议。

---

### 基础用法

#### 同步函数

```python
@tool(name="add")
def add_numbers(a: int, b: int) -> int:
    """将两个数字相加"""
    return a + b
```

#### 异步函数

```python
@tool(name="fetch_data")
async def fetch_data(url: str) -> dict:
    """从 URL 获取数据"""
    import aiohttp
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()
```

---

### 高级用法

#### 自定义描述

```python
@tool(
    name="search",
    description="搜索网络信息，支持多个搜索引擎"
)
async def web_search(
    query: str,
    engine: str = "google",
    max_results: int = 10
) -> List[dict]:
    """
    执行 Web 搜索

    Args:
        query: 搜索查询
        engine: 搜索引擎 (google/bing/duckduckgo)
        max_results: 最大结果数

    Returns:
        搜索结果列表
    """
    # 实现...
    pass
```

#### 带元数据

```python
@tool(
    name="api_call",
    description="调用外部 API",
    category="integration",
    requires_auth=True,
    rate_limit=100
)
async def call_api(endpoint: str, method: str = "GET") -> dict:
    """调用外部 API"""
    # 实现...
    pass
```

---

### 类型支持

`@tool` 自动推断参数和返回值类型：

```python
# 基本类型
@tool()
async def example(
    text: str,          # 字符串
    count: int,         # 整数
    ratio: float,       # 浮点数
    enabled: bool       # 布尔值
) -> str:
    pass

# 复杂类型
from typing import List, Dict, Optional

@tool()
async def complex_tool(
    items: List[str],           # 字符串列表
    config: Dict[str, Any],     # 字典
    optional_param: Optional[int] = None  # 可选参数
) -> Dict[str, List[str]]:
    pass
```

---

### 错误处理

```python
from loom.core.errors import ToolError

@tool(name="divide")
async def divide(a: float, b: float) -> float:
    """除法运算"""
    if b == 0:
        raise ToolError("除数不能为零")
    return a / b
```

---

## ToolBuilder

### 概述

`ToolBuilder` 提供程序化构建工具的能力。

```python
from loom.builtin import ToolBuilder

builder = ToolBuilder()
tool = builder.build(
    name="calculator",
    description="执行数学计算",
    function=calculate,
    parameters={
        "expression": {
            "type": "string",
            "description": "数学表达式"
        }
    }
)
```

### 构造函数

```python
ToolBuilder()
```

无参数构造。

---

### 核心方法

#### `build()`

构建工具。

```python
def build(
    self,
    name: str,
    description: str,
    function: Callable,
    parameters: Dict[str, Any],
    **metadata
) -> BaseTool
```

**参数**：
- `name` (`str`): 工具名称
- `description` (`str`): 工具描述
- `function` (`Callable`): 实现函数
- `parameters` (`Dict`): 参数定义（JSON Schema）
- `**metadata`: 额外元数据

**返回值**：
- `BaseTool`: 工具实例

**示例**：
```python
def my_function(x: int, y: int) -> int:
    return x + y

tool = builder.build(
    name="add",
    description="Add two numbers",
    function=my_function,
    parameters={
        "x": {
            "type": "integer",
            "description": "First number"
        },
        "y": {
            "type": "integer",
            "description": "Second number"
        }
    }
)
```

---

#### `from_function()`

从函数自动构建工具（类似 `@tool`）。

```python
def from_function(
    self,
    function: Callable,
    name: Optional[str] = None,
    description: Optional[str] = None
) -> BaseTool
```

**参数**：
- `function` (`Callable`): 函数
- `name` (`str`, 可选): 工具名称
- `description` (`str`, 可选): 工具描述

**示例**：
```python
async def search(query: str) -> List[dict]:
    """搜索信息"""
    pass

tool = builder.from_function(search)
# 自动使用函数名 "search" 和 docstring
```

---

#### `from_dict()`

从字典构建工具。

```python
def from_dict(self, spec: Dict) -> BaseTool
```

**参数**：
- `spec` (`Dict`): 工具规格

**示例**：
```python
spec = {
    "name": "calculator",
    "description": "Calculate expression",
    "function": calculate_func,
    "parameters": {
        "expression": {
            "type": "string",
            "description": "Math expression"
        }
    }
}

tool = builder.from_dict(spec)
```

---

## BaseTool

### 概述

`BaseTool` 是工具的协议定义。

```python
from loom.interfaces import BaseTool
```

### 协议

```python
class BaseTool(Protocol):
    name: str
    description: str
    parameters: Dict[str, Any]

    async def execute(self, **kwargs) -> Any:
        ...

    def to_function_schema(self) -> Dict[str, Any]:
        ...
```

#### 必需属性

- `name` (`str`): 工具名称
- `description` (`str`): 工具描述
- `parameters` (`Dict`): 参数定义（JSON Schema）

#### 必需方法

- `execute(**kwargs)`: 执行工具
- `to_function_schema()`: 转换为函数调用 schema

---

### 自定义工具

实现 `BaseTool` 协议创建自定义工具：

```python
from loom.interfaces import BaseTool

class CustomTool:
    """自定义工具"""

    def __init__(self):
        self.name = "custom_tool"
        self.description = "A custom tool"
        self.parameters = {
            "param1": {
                "type": "string",
                "description": "Parameter 1"
            }
        }

    async def execute(self, param1: str) -> str:
        """执行工具"""
        return f"Processed: {param1}"

    def to_function_schema(self) -> dict:
        """转换为 schema"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": self.parameters,
                "required": list(self.parameters.keys())
            }
        }

# 使用
tool = CustomTool()
agent = loom.agent(
    name="agent",
    llm=llm,
    tools=[tool]
)
```

---

## 工具注册

### Agent 注册

#### 构造时注册

```python
import loom

agent = loom.agent(
    name="agent",
    llm=llm,
    tools=[tool1, tool2, tool3]
)
```

#### 动态注册

```python
agent = loom.agent(name="agent", llm=llm)

# 添加工具
agent.tools.append(new_tool)

# 或重新设置
agent.tools = [tool1, tool2, tool3]
```

---

### 工具组合

```python
# 基础工具
@tool()
async def search(query: str) -> str:
    """搜索信息"""
    pass

@tool()
async def calculate(expression: str) -> float:
    """计算表达式"""
    pass

# 文件操作工具
@tool()
async def read_file(path: str) -> str:
    """读取文件"""
    pass

@tool()
async def write_file(path: str, content: str) -> bool:
    """写入文件"""
    pass

# 组合使用
agent = loom.agent(
    name="assistant",
    llm=llm,
    tools=[
        search,
        calculate,
        read_file,
        write_file
    ]
)
```

---

## 完整示例

### 示例 1：基础工具

```python
import loom, Message
from loom.builtin import OpenAILLM, tool

@tool(name="get_weather")
async def get_weather(city: str) -> dict:
    """
    获取城市天气

    Args:
        city: 城市名称

    Returns:
        天气信息字典
    """
    # 模拟 API 调用
    return {
        "city": city,
        "temperature": 22,
        "condition": "晴天"
    }

agent = loom.agent(
    name="weather-assistant",
    llm=OpenAILLM(api_key="..."),
    tools=[get_weather]
)

msg = Message(role="user", content="北京的天气怎么样？")
response = await agent.run(msg)
print(response.content)
```

---

### 示例 2：复杂工具

```python
from typing import List, Dict
import aiohttp

@tool(
    name="multi_search",
    description="从多个搜索引擎搜索信息"
)
async def multi_search(
    query: str,
    engines: List[str] = ["google", "bing"],
    max_results_per_engine: int = 5
) -> Dict[str, List[dict]]:
    """
    多引擎搜索

    Args:
        query: 搜索查询
        engines: 搜索引擎列表
        max_results_per_engine: 每个引擎的最大结果数

    Returns:
        每个引擎的搜索结果
    """
    results = {}

    async with aiohttp.ClientSession() as session:
        for engine in engines:
            # 实际实现会调用各引擎 API
            results[engine] = [
                {"title": f"Result {i}", "url": f"https://example.com/{i}"}
                for i in range(max_results_per_engine)
            ]

    return results

agent = loom.agent(
    name="researcher",
    llm=OpenAILLM(api_key="..."),
    tools=[multi_search]
)
```

---

### 示例 3：使用 ToolBuilder

```python
from loom.builtin import ToolBuilder

builder = ToolBuilder()

# 方式 1：完全手动构建
def calculate(expression: str) -> float:
    return eval(expression)

calc_tool = builder.build(
    name="calculator",
    description="Calculate math expression",
    function=calculate,
    parameters={
        "expression": {
            "type": "string",
            "description": "Math expression to evaluate"
        }
    }
)

# 方式 2：从函数自动构建
async def search_docs(keyword: str) -> List[str]:
    """搜索文档"""
    return [f"Doc about {keyword}"]

search_tool = builder.from_function(search_docs)

# 使用
agent = loom.agent(
    name="agent",
    llm=llm,
    tools=[calc_tool, search_tool]
)
```

---

### 示例 4：错误处理

```python
from loom.core.errors import ToolError

@tool(name="divide")
async def divide(a: float, b: float) -> float:
    """
    除法运算

    Args:
        a: 被除数
        b: 除数

    Returns:
        商

    Raises:
        ToolError: 当除数为零时
    """
    if b == 0:
        raise ToolError("除数不能为零")
    return a / b

@tool(name="fetch_url")
async def fetch_url(url: str) -> str:
    """
    获取 URL 内容

    Args:
        url: 网址

    Returns:
        页面内容

    Raises:
        ToolError: 当请求失败时
    """
    import aiohttp
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                response.raise_for_status()
                return await response.text()
    except Exception as e:
        raise ToolError(f"Failed to fetch {url}: {e}")

agent = loom.agent(
    name="agent",
    llm=llm,
    tools=[divide, fetch_url]
)
```

---

### 示例 5：工具集成

```python
# 文件操作工具集
@tool()
async def read_file(path: str) -> str:
    """读取文件内容"""
    with open(path, 'r') as f:
        return f.read()

@tool()
async def write_file(path: str, content: str) -> bool:
    """写入文件"""
    with open(path, 'w') as f:
        f.write(content)
    return True

@tool()
async def list_files(directory: str = ".") -> List[str]:
    """列出目录中的文件"""
    import os
    return os.listdir(directory)

# 数据处理工具集
@tool()
async def parse_json(json_str: str) -> dict:
    """解析 JSON 字符串"""
    import json
    return json.loads(json_str)

@tool()
async def format_json(data: dict, indent: int = 2) -> str:
    """格式化 JSON"""
    import json
    return json.dumps(data, indent=indent, ensure_ascii=False)

# 创建专业 Agent
file_agent = loom.agent(
    name="file-handler",
    llm=llm,
    tools=[read_file, write_file, list_files],
    system_prompt="你是文件处理专家"
)

data_agent = loom.agent(
    name="data-processor",
    llm=llm,
    tools=[parse_json, format_json],
    system_prompt="你是数据处理专家"
)

# 或创建全能 Agent
all_in_one_agent = loom.agent(
    name="assistant",
    llm=llm,
    tools=[
        read_file, write_file, list_files,
        parse_json, format_json
    ]
)
```

---

## 最佳实践

### 1. 命名规范

```python
# ✅ 好的命名
@tool(name="get_weather")
@tool(name="search_documents")
@tool(name="calculate_sum")

# ❌ 不好的命名
@tool(name="tool1")
@tool(name="do_stuff")
@tool(name="helper")
```

### 2. 清晰的描述

```python
# ✅ 好的描述
@tool(
    name="search",
    description="搜索网络信息，支持 Google、Bing、DuckDuckGo 三个搜索引擎"
)

# ❌ 不好的描述
@tool(
    name="search",
    description="Search"
)
```

### 3. 完整的文档字符串

```python
# ✅ 好的 docstring
@tool()
async def process_data(
    data: List[dict],
    filter_key: str,
    filter_value: Any
) -> List[dict]:
    """
    过滤和处理数据

    Args:
        data: 要处理的数据列表
        filter_key: 过滤键名
        filter_value: 过滤值

    Returns:
        过滤后的数据列表

    Raises:
        ToolError: 当数据格式错误时
    """
    pass
```

### 4. 类型注解

```python
# ✅ 好的类型注解
@tool()
async def analyze(
    text: str,
    options: Dict[str, Any],
    max_length: Optional[int] = None
) -> Dict[str, float]:
    pass

# ❌ 缺少类型注解
@tool()
async def analyze(text, options, max_length=None):
    pass
```

### 5. 错误处理

```python
# ✅ 好的错误处理
@tool()
async def fetch_data(url: str) -> dict:
    """获取数据"""
    try:
        # 实现...
        pass
    except HTTPError as e:
        raise ToolError(f"HTTP error: {e}")
    except Timeout as e:
        raise ToolError(f"Request timeout: {e}")
    except Exception as e:
        raise ToolError(f"Unexpected error: {e}")
```

---

## 相关文档

- [工具开发指南](../guides/tools/development.md) - 完整开发指南
- [Agents API](./agents.md) - Agent API 参考
- [快速开始](../getting-started/quickstart.md) - 快速入门

---

**返回**: [API 参考](./README.md) | [文档首页](../README.md)
