"""运行 SQL 模板 Agent 的入口。

基于 Loom 0.0.3 重构模式，使用统一协调机制和简化的 API。
"""

from __future__ import annotations

import asyncio
from typing import Dict, Optional

from loom.core.events import AgentEventType

from .agent import build_sql_template_agent
from .config import DATA_SOURCE, TEMPLATE_PATH, DEFAULT_SQL_CONFIG, SQLTemplateConfig
from .context_builder import (
    build_coordinator_prompt,
    parse_placeholders,
)
from .metadata import DorisSchemaExplorer


async def main(config: Optional[SQLTemplateConfig] = None) -> None:
    """运行 SQL 模板代理的主函数。
    
    Args:
        config: SQL 模板专用配置，默认使用 DEFAULT_SQL_CONFIG
    """
    if config is None:
        config = DEFAULT_SQL_CONFIG
    
    template_text = TEMPLATE_PATH.read_text(encoding="utf-8")
    explorer = DorisSchemaExplorer(
        hosts=DATA_SOURCE.hosts,
        mysql_port=DATA_SOURCE.mysql_port,
        user=DATA_SOURCE.user,
        password=DATA_SOURCE.password,
        database=DATA_SOURCE.database,
        connect_timeout=DATA_SOURCE.connect_timeout,
        config=config,  # 传递配置
    )

    try:
        schema = await explorer.load_schema()
    except Exception as exc:  # pragma: no cover - 依赖真实 Doris 环境
        raise RuntimeError(
            "无法连接 Doris，请确认网络与账号信息正确。"
        ) from exc

    placeholders = parse_placeholders(template_text)
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
        config=config,  # 传递配置
    )

    # 使用新的统一协调 API
    agent = build_sql_template_agent(
        explorer=explorer,
        config=config,
        execution_id="sql_template_demo"
    )

    print("=" * 80)
    print("SQL Template Agent – Doris Integration Demo")
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

