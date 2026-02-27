# Tools

Agent 通过 ToolRegistry 注册工具，LLM 在对话中自主决策何时调用哪个工具。

## 定义工具

使用 `define_tool` + Pydantic 参数模型：

```python
from pydantic import BaseModel
from loom import define_tool, ToolContext

class CalcParams(BaseModel):
    expression: str

async def calc_execute(params: CalcParams, ctx: ToolContext) -> str:
    return f"计算结果: {eval(params.expression)}"

tool = define_tool("calculate", "计算数学表达式", CalcParams, calc_execute)
```

## 注册与使用

```python
from loom import Agent, AgentConfig, ToolRegistry

registry = ToolRegistry()
registry.register(tool)

agent = Agent(
    provider=provider,
    config=AgentConfig(
        system_prompt="你是助手，需要时使用工具回答问题。",
        max_steps=5,
    ),
    tools=registry,
)

result = await agent.run("2的20次方是多少？")
# LLM 自主调用 calculate 工具 → 返回 1048576
```

## 多工具协作

LLM 可在一次对话中调用多个工具：

```python
class WeatherParams(BaseModel):
    city: str

async def weather_execute(params: WeatherParams, ctx: ToolContext) -> str:
    data = {"北京": "晴，25°C", "上海": "多云，22°C"}
    return data.get(params.city, f"{params.city}: 暂无数据")

registry.register(define_tool("weather", "查询城市天气", WeatherParams, weather_execute))

result = await agent.run("2的20次方是多少？北京天气如何？")
# LLM 自主调用两个工具，综合回答
print(result.steps)  # 2 (两次工具调用步骤)
```

## ToolContext 扩展 — 动态元数据访问

v0.6.3 新增。通过 `AgentConfig.tool_context` 向工具传递任意上下文数据，工具函数可以属性方式直接访问：

```python
from loom import Agent, AgentConfig, ToolRegistry, define_tool, ToolContext

agent = Agent(
    provider=provider,
    config=AgentConfig(
        max_steps=5,
        tool_context={"documentContext": ["block-A", "block-B"], "selectedText": "hello"},
    ),
    tools=registry,
)
```

在工具函数中，通过 `ctx.metadata` 字典或直接属性访问：

```python
async def my_tool(params, ctx: ToolContext) -> str:
    # 字典访问
    docs = ctx.metadata["documentContext"]
    # 属性访问（等价，通过 __getattr__ 代理到 metadata）
    docs = ctx.documentContext
    text = ctx.selectedText
    return f"Found {len(docs)} docs"
```

数据流链路：`AgentConfig.tool_context` → `LoopContext.tool_context` → `_exec_tool()` → `ToolContext.metadata`

注意：metadata 中的键不会覆盖 ToolContext 的原生字段（`agent_id`、`session_id` 等）。

## API 参考

```python
# ToolRegistry
registry = ToolRegistry()
registry.register(tool)        # 注册工具
registry.list() -> list[ToolDefinition]  # 列出所有工具

# define_tool
define_tool(name, description, params_model, execute_fn) -> ToolDefinition

# ToolContext — 工具执行时的上下文
@dataclass
class ToolContext:
    agent_id: str = ""
    session_id: str | None = None
    tenant_id: str | None = None
    signal: Any | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

# 内置工具
from loom import done_tool, delegate_tool
```

> 完整示例：[`examples/demo/02_tools.py`](../examples/demo/02_tools.py)
