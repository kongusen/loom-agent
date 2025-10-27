"""简化的 SQL 模板 Agent 测试。"""

from __future__ import annotations

import asyncio
from typing import Dict

from loom.core.events import AgentEventType

from examples.agents.sql_template_agent.agent import build_sql_template_agent
from examples.agents.sql_template_agent.config import DATA_SOURCE
from examples.agents.sql_template_agent.context_builder import build_coordinator_prompt
from examples.agents.sql_template_agent.metadata import DorisSchemaExplorer


async def main() -> None:
    # 使用简化的模板
    template_text = """
旅游业务数据分析报告模板（简化版）
本报告基于{{统计：总行程单数}}个行程单数据，涵盖{{周期：数据时间范围}}期间的旅游业务表现。
业务概览 · 总行程数：{{统计：总行程数}}个 · 活跃导游数：{{统计：活跃导游数量}}位
"""
    
    explorer = DorisSchemaExplorer(
        hosts=DATA_SOURCE.hosts,
        mysql_port=DATA_SOURCE.mysql_port,
        user=DATA_SOURCE.user,
        password=DATA_SOURCE.password,
        database=DATA_SOURCE.database,
        connect_timeout=DATA_SOURCE.connect_timeout,
    )

    try:
        schema = await explorer.load_schema()
    except Exception as exc:
        raise RuntimeError(
            "无法连接 Doris，请确认网络与账号信息正确。"
        ) from exc

    # 简化的占位符列表
    placeholders = [
        {"category": "统计", "description": "总行程单数", "placeholder": "统计:总行程单数"},
        {"category": "周期", "description": "数据时间范围", "placeholder": "周期:数据时间范围"},
        {"category": "统计", "description": "总行程数", "placeholder": "统计:总行程数"},
        {"category": "统计", "description": "活跃导游数量", "placeholder": "统计:活跃导游数量"},
    ]
    
    data_source_summary: Dict[str, str] = {
        "type": "doris",
        "hosts": ",".join(DATA_SOURCE.hosts),
        "mysql_port": str(DATA_SOURCE.mysql_port),
        "http_port": str(DATA_SOURCE.http_port),
        "database": DATA_SOURCE.database,
        "user": DATA_SOURCE.user,
    }

    prompt = build_coordinator_prompt(
        template_text=template_text,
        placeholders=placeholders,
        schema_snapshot=schema,
        data_source_summary=data_source_summary,
    )

    agent = build_sql_template_agent(explorer)

    print("=" * 80)
    print("SQL Template Agent – 简化测试")
    print("=" * 80)

    final_output = ""
    iteration_count = 0
    async for event in agent.execute(prompt):
        if event.type == AgentEventType.ITERATION_START:
            iteration_count += 1
            print(f"\n[iteration {iteration_count}] 开始")
        elif event.type == AgentEventType.LLM_DELTA:
            print(event.content or "", end="", flush=True)
        elif event.type == AgentEventType.TOOL_EXECUTION_START and event.tool_call:
            print(f"\n\n[tool:start] {event.tool_call.name}")
            if event.tool_call.arguments:
                print(f"[tool:args] {event.tool_call.arguments}")
        elif event.type == AgentEventType.TOOL_RESULT and event.tool_result:
            print(f"\n[tool:result] {event.tool_result.tool_name}")
            if event.tool_result.content:
                content_preview = event.tool_result.content[:200] + "..." if len(event.tool_result.content) > 200 else event.tool_result.content
                print(f"[tool:content] {content_preview}")
        elif event.type == AgentEventType.TOOL_ERROR and event.tool_result:
            print(f"\n[tool:error] {event.tool_result.tool_name}: {event.tool_result.content}")
        elif event.type == AgentEventType.MAX_ITERATIONS_REACHED:
            print(f"\n[warning] 达到最大迭代次数限制: {event.metadata.get('max_iterations', 0)}")
        elif event.type == AgentEventType.AGENT_FINISH:
            final_output = event.content or ""
            print("\n\n[agent:finish]")
            print(f"[final_iterations] {iteration_count}")

    print("\n" + "=" * 80)
    print("FINAL SQL\n")
    print(final_output)


if __name__ == "__main__":
    asyncio.run(main())
