"""最终测试：使用最简化的配置生成 SQL。"""

import asyncio
from loom.core.events import AgentEventType
from examples.agents.sql_template_agent.llms import create_llm
from loom import agent as build_agent
from loom.builtin.memory.in_memory import InMemoryMemory

async def main():
    print("=" * 80)
    print("最终测试 - 最简化配置")
    print("=" * 80)
    
    # 创建最简单的代理
    agent = build_agent(
        llm=create_llm(model="gpt-4o-mini"),
        tools=[],  # 不使用任何工具
        memory=InMemoryMemory(),
        max_iterations=2,
        system_instructions="你是一个 SQL 专家，请直接生成 SQL 查询。",
    )
    
    # 简化的提示词
    prompt = """
请为旅游业务分析生成一个 SQL 查询，统计以下指标：

1. 总行程单数 (COUNT)
2. 数据时间范围 (MIN 和 MAX 日期)
3. 总行程数 (COUNT DISTINCT)
4. 活跃导游数量 (COUNT DISTINCT)

数据库表：
- ods_itinerary: 行程单信息表，包含 itinerary_id, dt, guide_msg_id, certificate, team_id, number_people, team_start_date 等字段
- ods_guide: 导游基础信息表，包含 id, dt, name, create_time, audit_time 等字段

请生成一个完整的 SQL 查询，使用适当的别名，用 ```sql 代码块包裹。
"""
    
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
