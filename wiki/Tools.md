# 工具系统

`loom/tools/` 实现了统一的工具注册、执行和沙盒管理系统。

## 文件结构

```
loom/tools/
├── core/                # 核心工具基础设施
│   ├── registry.py      # ToolRegistry - 工具注册表
│   ├── sandbox_manager.py # SandboxToolManager - 沙盒工具管理器
│   ├── sandbox.py       # Sandbox - 文件系统沙盒
│   ├── executor.py      # ToolExecutor - 工具执行器
│   ├── converters.py    # FunctionToMCP - Python 函数转 MCP 定义
│   ├── mcp_adapter.py   # MCPAdapter - MCP 协议适配
│   └── toolset.py       # ToolSet - 工具集合
├── builtin/             # 内置工具
│   ├── bash.py          # Bash 命令执行
│   ├── file.py          # 文件操作（读/写/搜索）
│   ├── http.py          # HTTP 请求
│   ├── search.py        # 文件搜索
│   ├── todo.py          # TODO 管理
│   ├── done.py          # 任务完成标记
│   └── creation.py      # 动态工具创建
├── memory/              # 记忆工具
│   ├── browse.py        # 记忆浏览
│   ├── events.py        # 事件查询
│   └── manage.py        # 记忆管理
├── search/              # 统一检索工具
│   ├── builder.py       # UnifiedSearchToolBuilder
│   └── executor.py      # UnifiedSearchExecutor
├── skills/              # 技能系统（见 Skills.md）
└── mcp_types.py         # MCP 类型定义
```

## SandboxToolManager

统一的工具注册和执行中心，所有工具通过此管理器注册和调用。

```python
manager = SandboxToolManager(
    sandbox=Sandbox(root_dir="/workspace"),
    event_bus=event_bus,
)

# 注册工具
await manager.register_tool(
    name="my_tool",
    func=my_tool_func,
    definition=MCPToolDefinition(...),
    scope=ToolScope.SYSTEM,
)

# 执行工具
result = await manager.execute("my_tool", {"arg1": "value"})

# 列出所有工具
tools = manager.list_tools()  # → list[MCPToolDefinition]
```

### ToolScope

工具作用域定义安全策略：

```python
class ToolScope(Enum):
    SANDBOXED = "sandboxed"  # 文件操作受沙盒约束
    SYSTEM = "system"        # 系统级操作，不受沙盒约束
    MCP = "mcp"              # 外部 MCP 工具
    CONTEXT = "context"      # 上下文查询工具
```

## 内置工具

Agent 通过 `AgentFactory` 自动注册以下内置工具：

| 工具 | 作用域 | 说明 |
|------|--------|------|
| `bash` | SYSTEM | 执行 shell 命令 |
| `read_file` | SANDBOXED | 读取文件内容 |
| `write_file` | SANDBOXED | 写入文件 |
| `search_files` | SANDBOXED | 搜索文件 |
| `http_request` | SYSTEM | HTTP 请求 |
| `todo` | SANDBOXED | TODO 管理 |
| `done` | SYSTEM | 标记任务完成（触发 TaskComplete 异常） |

## 元工具

Agent 自动添加的框架级工具，LLM 自主决定是否使用：

| 元工具 | 说明 |
|--------|------|
| `create_plan` | 创建执行计划（规划范式） |
| `delegate_task` | 委派子任务（协作范式） |
| `delegate_to_agent` | 委派给指定 Agent（需配置 available_agents） |
| `query` | 统一检索（记忆 + 知识库） |
| `create_tool` | 运行时动态创建工具 |

## FunctionToMCP

将普通 Python 函数转换为 MCP 工具定义：

```python
from loom.tools.core.converters import FunctionToMCP

def calculate(expression: str) -> str:
    """计算数学表达式"""
    return str(eval(expression))

mcp_def = FunctionToMCP.convert(calculate, name="calculate")
# → MCPToolDefinition(name="calculate", description="计算数学表达式", ...)
```

支持从函数签名和 docstring 自动提取参数定义。

## 统一检索工具

`query` 是框架的统一检索工具，整合记忆检索和知识库检索。工具名始终为 `query`，Agent 无需区分记忆和知识。

### 双通道设计

框架提供两条检索通道，互补工作：

```
主动通道（Agent 调用 query 工具）
  └─ UnifiedSearchExecutor → 结果作为 tool_result 返回

被动通道（上下文构建时自动执行）
  └─ UnifiedRetrievalSource → 结果注入 LLM 上下文
```

- **主动通道**：Agent 根据工具描述中的 `search_hints` 自主决定何时调用
- **被动通道**：每次 LLM 交互前，`ContextOrchestrator` 自动从 L4 和知识库检索相关内容注入上下文

### UnifiedSearchToolBuilder

根据是否配置 `knowledge_base` 动态生成不同的工具定义：

```
无 knowledge_base → 纯记忆检索（参数: query, layer）
有 knowledge_base → 统一检索（参数: query, scope, intent, source, filters）
```

工具描述动态聚合所有知识库的元信息：

```python
# 知识库配置
kb = GraphRAGKnowledgeBase(
    name="product_docs",
    description="产品文档和API参考",
    search_hints=["产品功能", "API用法", "错误排查"],
    supported_filters=["category", "version"],
)

# 自动生成的工具描述包含：
# - "可用知识源：product_docs: 产品文档和API参考"
# - "适用场景：产品功能, API用法, 错误排查"
# - filters 参数说明 "支持: category, version"
# - 多知识库时自动添加 source 参数（enum 列出所有 kb.name）
```

### UnifiedSearchExecutor

主动通道的执行器，处理 `query` 工具调用：

```
Agent 调用 query(query, scope, ...)
  ↓
L1 缓存检查（同 Session 近期相似查询复用，Jaccard ≥ 0.6）
  ↓
路由判断（scope: auto/memory/knowledge/all）
  ↓
QueryRewriter → 查询增强（从对话上下文提取高频实词追加）
  ↓
并行检索:
  ├─ Memory: L1(文本匹配) → L2(重要性加权) → L3(摘要) → L4(向量语义)
  └─ Knowledge: 遍历目标知识库调用 kb.query()
  ↓
Reranker → 跨源统一排序（4 信号加权）
  ↓
格式化输出（带来源标签和相关度分数）
```

### 参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `query` | string | 搜索查询（必填） |
| `scope` | enum | `auto`=自动路由, `memory`=仅记忆, `knowledge`=仅知识库, `all`=全部 |
| `intent` | string | 搜索意图（如 recall/lookup/troubleshooting），追加到查询增强检索 |
| `source` | enum | 指定知识库名（多知识库时可用） |
| `layer` | enum | 指定记忆层级 `auto/l1/l2/l3/l4`（纯记忆模式） |
| `filters` | object | 过滤条件（由知识库 `supported_filters` 定义） |

## Sandbox

文件系统沙盒，限制 SANDBOXED 工具的文件访问范围：

```python
sandbox = Sandbox(root_dir="/workspace")
# SANDBOXED 工具只能访问 /workspace 及其子目录
```
