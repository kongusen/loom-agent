"""绕过 Loom 递归机制的解决方案。"""

import asyncio
from examples.agents.sql_template_agent.llms import create_llm
from examples.agents.sql_template_agent.metadata import DorisSchemaExplorer
from examples.agents.sql_template_agent.config import DATA_SOURCE
from examples.agents.sql_template_agent.tools import DorisSelectTool, SchemaLookupTool

async def main():
    print("=" * 80)
    print("绕过 Loom 递归机制的解决方案")
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
    
    # 2. 创建工具实例
    schema_tool = SchemaLookupTool(explorer)
    select_tool = DorisSelectTool(explorer)
    
    # 3. 创建 LLM
    llm = create_llm()
    
    # 4. 手动执行工具调用流程
    print("\n步骤 1: 使用 schema_lookup 工具查找表结构")
    schema_result = await schema_tool.run(placeholder='统计:总行程单数', table='ods_itinerary')
    print("Schema 查询结果:")
    print(schema_result[:500] + "...")
    
    print("\n步骤 2: 使用 doris_select 工具获取样例数据")
    select_result = await select_tool.run(sql="SELECT * FROM ods_itinerary LIMIT 5")
    print("样例数据查询结果:")
    print(select_result[:500] + "...")
    
    print("\n步骤 3: 基于工具结果生成 SQL")
    
    # 5. 构建包含工具结果的提示词
    prompt = f"""
基于以下真实的数据库信息，请生成 SQL 查询：

数据库信息：
- 类型：Doris
- 主机：192.168.61.30
- 数据库：yjg

表结构信息：
{schema_result}

样例数据：
{select_result}

请生成一个 SQL 查询，统计以下指标：
1. 总行程单数 (COUNT)
2. 数据时间范围 (MIN 和 MAX 日期)
3. 总行程数 (COUNT DISTINCT)
4. 活跃导游数量 (COUNT DISTINCT)

要求：
- 使用真实的字段名
- 确保 SQL 语法正确
- 使用适当的别名
- 用 ```sql 代码块包裹结果

请直接输出 SQL 查询：
"""
    
    messages = [
        {"role": "system", "content": "你是一个专业的 SQL 专家，擅长基于真实数据源生成准确的 SQL 查询。"},
        {"role": "user", "content": prompt}
    ]
    
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
    asyncio.run(main())
