"""直接测试 LLM 生成 SQL 的能力。"""

import asyncio
from examples.agents.sql_template_agent.llms import create_llm

async def test_llm_direct():
    llm = create_llm()
    
    messages = [
        {
            "role": "system",
            "content": "你是一个 SQL 专家，请根据用户需求生成 SQL 查询。"
        },
        {
            "role": "user", 
            "content": """
请为旅游业务分析生成一个 SQL 查询，需要统计以下指标：
1. 总行程单数 (COUNT)
2. 数据时间范围 (MIN 和 MAX 日期)
3. 总行程数 (COUNT DISTINCT)
4. 活跃导游数量 (COUNT DISTINCT)

数据库中有以下表：
- ods_itinerary: 行程单信息表，包含 itinerary_id, dt, guide_msg_id, certificate, team_id 等字段
- ods_guide: 导游基础信息表，包含 id, dt, name, create_time, audit_time 等字段

请生成一个完整的 SQL 查询，使用适当的别名。
"""
        }
    ]
    
    print("正在测试 LLM 直接生成 SQL...")
    try:
        result = await llm.generate_with_tools(messages)
        print("LLM 响应:")
        print(result.get("content", "无内容"))
        if result.get("tool_calls"):
            print("工具调用:")
            for tc in result["tool_calls"]:
                print(f"  - {tc['name']}: {tc['arguments']}")
    except Exception as e:
        print(f"LLM 调用失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_llm_direct())
