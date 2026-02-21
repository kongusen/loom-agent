"""02 — 自定义工具：Agent 通过 LLM 自主决策调用工具完成任务。"""

import asyncio

from _provider import create_provider
from pydantic import BaseModel

from loom import Agent, AgentConfig, ToolContext, ToolRegistry, define_tool

# ── 工具定义 ──


class CalcParams(BaseModel):
    expression: str


class WeatherParams(BaseModel):
    city: str


async def calc_execute(params: CalcParams, ctx: ToolContext) -> str:
    try:
        return f"计算结果: {eval(params.expression)}"
    except Exception as e:
        return f"错误: {e}"


async def weather_execute(params: WeatherParams, ctx: ToolContext) -> str:
    data = {"北京": "晴，25°C", "上海": "多云，22°C", "深圳": "阵雨，28°C"}
    return data.get(params.city, f"{params.city}: 暂无数据")


async def main():
    # 1. 注册工具
    registry = ToolRegistry()
    registry.register(define_tool("calculate", "计算数学表达式", CalcParams, calc_execute))
    registry.register(define_tool("weather", "查询城市天气", WeatherParams, weather_execute))
    print(f"已注册工具: {[t.name for t in registry.list()]}")

    # 2. 创建带工具的 Agent — LLM 自主决定何时调用工具
    agent = Agent(
        provider=create_provider(),
        config=AgentConfig(system_prompt="你是助手，需要时使用工具回答问题。", max_steps=5),
        tools=registry,
    )

    # 3. LLM 自主调用工具
    print("\n[Agent + Tools] 提问: 2的20次方是多少？北京天气如何？")
    result = await agent.run("2的20次方是多少？北京天气如何？")
    print(f"  回复: {result.content[:200]}")
    print(f"  steps: {result.steps}")


if __name__ == "__main__":
    asyncio.run(main())
