"""简化的端到端测试：直接使用 LLM 生成 SQL。"""

import asyncio
import json
from examples.agents.sql_template_agent.llms import create_llm
from examples.agents.sql_template_agent.metadata import DorisSchemaExplorer
from examples.agents.sql_template_agent.config import DATA_SOURCE

async def test_end_to_end():
    print("=" * 80)
    print("SQL Template Agent – 端到端测试")
    print("=" * 80)
    
    # 1. 连接数据库获取 schema
    print("\n1. 连接 Doris 数据库...")
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
        print(f"✓ 成功连接，发现 {len(schema)} 张表")
    except Exception as e:
        print(f"✗ 连接失败: {e}")
        return
    
    # 2. 解析模板占位符
    print("\n2. 解析模板占位符...")
    template_text = """
旅游业务数据分析报告模板（简化版）
本报告基于{{统计：总行程单数}}个行程单数据，涵盖{{周期：数据时间范围}}期间的旅游业务表现。
业务概览 · 总行程数：{{统计：总行程数}}个 · 活跃导游数：{{统计：活跃导游数量}}位
"""
    
    import re
    pattern = re.compile(r"{{\s*(?P<category>[^：:{}]+)\s*[：:]\s*(?P<description>[^{}]+?)\s*}}")
    placeholders = []
    for match in pattern.finditer(template_text):
        category = match.group("category").strip()
        description = match.group("description").strip()
        placeholders.append({
            "category": category,
            "description": description,
            "placeholder": f"{category}:{description}",
        })
    
    print(f"✓ 解析出 {len(placeholders)} 个占位符:")
    for p in placeholders:
        print(f"  - {p['placeholder']}")
    
    # 3. 构建 schema 摘要
    print("\n3. 构建数据库 schema 摘要...")
    schema_summary = []
    for table_name, table_info in list(schema.items())[:5]:  # 只显示前5张表
        columns_info = []
        for col in table_info.columns[:5]:  # 只显示前5个字段
            columns_info.append(f"{col.name} ({col.data_type})")
        schema_summary.append(f"表 {table_name}: {', '.join(columns_info)}")
    
    schema_text = "\n".join(schema_summary)
    print(f"✓ Schema 摘要:\n{schema_text}")
    
    # 4. 使用 LLM 生成 SQL
    print("\n4. 使用 LLM 生成 SQL...")
    llm = create_llm()
    
    prompt = f"""
你是一个 SQL 专家，请根据以下信息生成一个完整的 SQL 查询：

模板占位符需求：
{json.dumps(placeholders, ensure_ascii=False, indent=2)}

数据库 Schema：
{schema_text}

要求：
1. 生成一个完整的 SQL 查询，包含所有占位符对应的字段
2. 使用适当的别名，便于后续替换
3. 优先使用 ods_itinerary 和 ods_guide 表
4. 确保查询语法正确

请直接输出 SQL 查询，用 ```sql 代码块包裹。
"""
    
    messages = [
        {"role": "system", "content": "你是一个专业的 SQL 专家，擅长生成复杂的数据分析查询。"},
        {"role": "user", "content": prompt}
    ]
    
    try:
        result = await llm.generate_with_tools(messages)
        content = result.get("content", "")
        print("✓ LLM 响应:")
        print(content)
        
        # 提取 SQL 代码块
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
        print(f"✗ LLM 调用失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_end_to_end())
