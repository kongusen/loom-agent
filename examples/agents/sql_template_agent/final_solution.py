"""最终解决方案：基于工具的 SQL 生成。"""

import asyncio
from loom.core.events import AgentEventType
from examples.agents.sql_template_agent.llms import create_llm
from loom import agent as build_agent
from loom.builtin.memory.in_memory import InMemoryMemory
from examples.agents.sql_template_agent.metadata import DorisSchemaExplorer
from examples.agents.sql_template_agent.config import DATA_SOURCE
from examples.agents.sql_template_agent.tools import DorisSelectTool, SchemaLookupTool

async def main():
    print("=" * 80)
    print("最终解决方案 - 基于工具的 SQL 生成")
    print("=" * 80)
    
    # 1. 连接数据库
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
        print(f"✓ 成功连接数据库，发现 {len(schema)} 张表")
    except Exception as exc:
        print(f"✗ 连接失败: {exc}")
        return
    
    # 2. 创建代理
    agent = build_agent(
        llm=create_llm(model="gpt-4o-mini"),
        tools=[
            SchemaLookupTool(explorer),
            DorisSelectTool(explorer),
        ],
        memory=InMemoryMemory(),
        max_iterations=10,
        system_instructions="""你是 SQL 专家。工作流程：
1. 使用 schema_lookup 工具查找相关表
2. 使用 doris_select 工具获取样例数据
3. 基于工具返回的真实数据生成 SQL

重要：在收集到足够信息后，必须生成 SQL！不要无限循环调用工具！"""
    )
    
    # 3. 非常明确的提示词
    prompt = """
请为旅游业务分析生成 SQL，统计以下指标：
1. 总行程单数 (COUNT)
2. 数据时间范围 (MIN 和 MAX 日期)
3. 总行程数 (COUNT DISTINCT)
4. 活跃导游数量 (COUNT DISTINCT)

数据库：Doris, 主机：192.168.61.30, 数据库：yjg

请按以下步骤执行：
1. 使用 schema_lookup 工具查找 ods_itinerary 表
2. 使用 doris_select 工具查看 ods_itinerary 表的样例数据
3. 基于真实数据生成 SQL

现在开始！第一步：调用 schema_lookup 工具查找 ods_itinerary 表。
"""
    
    print("正在运行代理...")
    final_output = ""
    iteration_count = 0
    tool_calls_count = 0
    
    async for event in agent.execute(prompt):
        if event.type == AgentEventType.ITERATION_START:
            iteration_count += 1
            print(f"\n[iteration {iteration_count}] 开始")
        elif event.type == AgentEventType.LLM_DELTA:
            print(event.content or "", end="", flush=True)
        elif event.type == AgentEventType.TOOL_EXECUTION_START and event.tool_call:
            tool_calls_count += 1
            print(f"\n\n[tool:start] {event.tool_call.name}")
            if event.tool_call.arguments:
                print(f"[tool:args] {event.tool_call.arguments}")
        elif event.type == AgentEventType.TOOL_RESULT and event.tool_result:
            print(f"\n[tool:result] {event.tool_result.tool_name}")
            if event.tool_result.content:
                content_preview = event.tool_result.content[:300] + "..." if len(event.tool_result.content) > 300 else event.tool_result.content
                print(f"[tool:content] {content_preview}")
        elif event.type == AgentEventType.TOOL_ERROR and event.tool_result:
            print(f"\n[tool:error] {event.tool_result.tool_name}: {event.tool_result.content}")
        elif event.type == AgentEventType.MAX_ITERATIONS_REACHED:
            print(f"\n[warning] 达到最大迭代次数限制: {event.metadata.get('max_iterations', 0)}")
        elif event.type == AgentEventType.AGENT_FINISH:
            final_output = event.content or ""
            print("\n\n[agent:finish]")
            print(f"[final_iterations] {iteration_count}")
            print(f"[total_tool_calls] {tool_calls_count}")
    
    print("\n" + "=" * 80)
    print("FINAL SQL")
    print("=" * 80)
    print(final_output)

if __name__ == "__main__":
    asyncio.run(main())
