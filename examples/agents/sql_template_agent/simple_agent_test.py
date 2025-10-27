"""简化的代理：直接使用 LLM 生成 SQL，不使用子代理。"""

import asyncio
from loom.core.events import AgentEventType
from examples.agents.sql_template_agent.llms import create_llm
from examples.agents.sql_template_agent.metadata import DorisSchemaExplorer
from examples.agents.sql_template_agent.config import DATA_SOURCE
from examples.agents.sql_template_agent.context_builder import build_coordinator_prompt, parse_placeholders
from examples.agents.sql_template_agent.config import TEMPLATE_PATH
from loom import agent as build_agent
from loom.builtin.tools.task import TaskTool
from loom.builtin.memory.in_memory import InMemoryMemory
from examples.agents.sql_template_agent.tools import DorisSelectTool, SchemaLookupTool

async def main():
    print("=" * 80)
    print("简化代理测试 - 直接生成 SQL")
    print("=" * 80)
    
    # 1. 获取模板和 schema
    template_text = TEMPLATE_PATH.read_text(encoding="utf-8")
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
        raise RuntimeError("无法连接 Doris，请确认网络与账号信息正确。") from exc
    
    placeholders = parse_placeholders(template_text)
    data_source_summary = {
        "type": "doris",
        "hosts": ",".join(DATA_SOURCE.hosts),
        "mysql_port": str(DATA_SOURCE.mysql_port),
        "http_port": str(DATA_SOURCE.http_port),
        "database": DATA_SOURCE.database,
        "user": DATA_SOURCE.user,
    }
    
    # 2. 构建简化的提示词
    prompt = f"""
你是一个 SQL 专家。请根据以下信息生成一个完整的 SQL 查询：

数据库信息：
- 类型：Doris
- 主机：{DATA_SOURCE.hosts[0]}
- 端口：{DATA_SOURCE.mysql_port}
- 数据库：{DATA_SOURCE.database}
- 用户：{DATA_SOURCE.user}

模板占位符需求：
{placeholders[:5]}  # 只处理前5个占位符

要求：
1. 生成一个完整的 SQL 查询
2. 使用适当的别名
3. 优先使用 ods_itinerary 和 ods_guide 表
4. 确保查询语法正确
5. 用 ```sql 代码块包裹结果

请直接输出 SQL 查询，不要调用任何工具！
"""
    
    # 3. 创建简化的代理（不使用子代理）
    agent = build_agent(
        llm=create_llm(model="gpt-4o-mini"),
        tools=[],  # 不使用任何工具
        memory=InMemoryMemory(),
        max_iterations=3,  # 限制迭代次数
        system_instructions="你是一个 SQL 专家，请直接生成 SQL 查询，不要调用任何工具。",
    )
    
    print("正在运行代理...")
    final_output = ""
    iteration_count = 0
    
    async for event in agent.execute(prompt):
        if event.type == AgentEventType.ITERATION_START:
            iteration_count += 1
            print(f"\n[iteration {iteration_count}] 开始")
        elif event.type == AgentEventType.LLM_DELTA:
            print(event.content or "", end="", flush=True)
        elif event.type == AgentEventType.AGENT_FINISH:
            final_output = event.content or ""
            print("\n\n[agent:finish]")
            print(f"[final_iterations] {iteration_count}")
    
    print("\n" + "=" * 80)
    print("FINAL SQL")
    print("=" * 80)
    print(final_output)

if __name__ == "__main__":
    asyncio.run(main())
