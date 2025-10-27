"""直接测试：使用 LLM 生成 SQL，绕过代理架构。"""

import asyncio
import json
from examples.agents.sql_template_agent.llms import create_llm
from examples.agents.sql_template_agent.metadata import DorisSchemaExplorer
from examples.agents.sql_template_agent.config import DATA_SOURCE

async def test_direct_sql_generation():
    print("=" * 80)
    print("直接 SQL 生成测试")
    print("=" * 80)
    
    # 1. 获取 schema
    explorer = DorisSchemaExplorer(
        hosts=DATA_SOURCE.hosts,
        mysql_port=DATA_SOURCE.mysql_port,
        user=DATA_SOURCE.user,
        password=DATA_SOURCE.password,
        database=DATA_SOURCE.database,
        connect_timeout=DATA_SOURCE.connect_timeout,
    )
    
    schema = await explorer.load_schema()
    
    # 2. 构建简化的 schema 信息
    schema_info = []
    for table_name, table_info in list(schema.items())[:5]:
        columns = [f"{col.name} ({col.data_type})" for col in table_info.columns[:5]]
        schema_info.append(f"表 {table_name}: {', '.join(columns)}")
    
    schema_text = "\n".join(schema_info)
    
    # 3. 简化的占位符
    placeholders = [
        {"category": "统计", "description": "总行程单数", "placeholder": "统计:总行程单数"},
        {"category": "周期", "description": "数据时间范围", "placeholder": "周期:数据时间范围"},
        {"category": "统计", "description": "总行程数", "placeholder": "统计:总行程数"},
        {"category": "统计", "description": "活跃导游数量", "placeholder": "统计:活跃导游数量"},
    ]
    
    # 4. 构建提示词
    prompt = f"""
你是一个 SQL 专家。请根据以下信息生成一个完整的 SQL 查询：

数据库信息：
- 类型：Doris
- 主机：192.168.61.30
- 端口：9030
- 数据库：yjg
- 用户：root

表结构：
{schema_text}

需要统计的指标：
{json.dumps(placeholders, ensure_ascii=False, indent=2)}

要求：
1. 生成一个完整的 SQL 查询
2. 使用适当的别名，如 total_itinerary_count, date_range 等
3. 优先使用 ods_itinerary 和 ods_guide 表
4. 确保查询语法正确
5. 用 ```sql 代码块包裹结果

请直接输出 SQL 查询：
"""
    
    # 5. 调用 LLM
    llm = create_llm()
    messages = [
        {"role": "system", "content": "你是一个专业的 SQL 专家，擅长生成复杂的数据分析查询。"},
        {"role": "user", "content": prompt}
    ]
    
    print("正在调用 LLM 生成 SQL...")
    try:
        result = await llm.generate_with_tools(messages)
        content = result.get("content", "")
        
        print("\nLLM 响应:")
        print(content)
        
        # 提取 SQL
        import re
        sql_match = re.search(r'```sql\n(.*?)\n```', content, re.DOTALL)
        if sql_match:
            sql_query = sql_match.group(1).strip()
            print("\n" + "=" * 80)
            print("生成的 SQL 查询:")
            print("=" * 80)
            print(sql_query)
        else:
            print("\n未找到 SQL 代码块")
            
    except Exception as e:
        print(f"LLM 调用失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_direct_sql_generation())
