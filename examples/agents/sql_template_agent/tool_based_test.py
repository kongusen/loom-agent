"""测试基于工具的 SQL 生成流程。"""

import asyncio
from loom.core.events import AgentEventType
from examples.agents.sql_template_agent.agent import build_sql_template_agent
from examples.agents.sql_template_agent.metadata import DorisSchemaExplorer
from examples.agents.sql_template_agent.config import DATA_SOURCE

async def main():
    print("=" * 80)
    print("基于工具的 SQL 生成测试")
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
        print(f"✗ 连接失败: {e}")
        return
    
    # 2. 构建代理
    agent = build_sql_template_agent(explorer)
    
    # 3. 简化的模板和提示词
    prompt = """
请为以下旅游业务分析需求生成 SQL：

模板占位符：
1. 统计：总行程单数
2. 周期：数据时间范围  
3. 统计：总行程数
4. 统计：活跃导游数量

数据库信息：
- 类型：Doris
- 主机：192.168.61.30
- 数据库：yjg

请按照以下步骤：
1. 使用 schema_lookup 工具查找相关表
2. 使用 doris_select 工具获取样例数据
3. 基于真实数据源信息生成 SQL

必须使用工具了解数据源后再生成 SQL！
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
