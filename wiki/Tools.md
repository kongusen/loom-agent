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
    agent_id: str
    signal: Any = None
    session_id: str = ""
    tenant_id: str = ""

# 内置工具
from loom import done_tool, delegate_tool
```

> 完整示例：[`examples/demo/02_tools.py`](../examples/demo/02_tools.py)
