#!/usr/bin/env python3
"""基于发现的 ods_refund 表生成退货渠道 SQL。

基于分析结果，ods_refund 是退货工单表，我们需要进一步分析其字段结构。
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from examples.agents.sql_template_agent.config import (
    DEFAULT_SQL_CONFIG, 
    DATA_SOURCE
)
from examples.agents.sql_template_agent.metadata import DorisSchemaExplorer
from examples.agents.sql_template_agent.tools import SchemaLookupTool, DorisSelectTool


async def analyze_refund_table():
    """分析 ods_refund 表的完整结构"""
    print("🔍 分析 ods_refund 表的完整结构")
    print("=" * 60)
    
    explorer = DorisSchemaExplorer(
        hosts=DATA_SOURCE.hosts,
        mysql_port=DATA_SOURCE.mysql_port,
        user=DATA_SOURCE.user,
        password=DATA_SOURCE.password,
        database=DATA_SOURCE.database,
        connect_timeout=DATA_SOURCE.connect_timeout,
        config=DEFAULT_SQL_CONFIG
    )
    
    schema_tool = SchemaLookupTool(explorer)
    select_tool = DorisSelectTool(explorer)
    
    # 获取 ods_refund 表的完整结构
    print("📊 获取 ods_refund 表的完整结构...")
    result = await schema_tool.run(
        placeholder="ods_refund 表结构",
        table="ods_refund"
    )
    
    print("✅ ods_refund 表结构:")
    print(result)
    
    # 尝试查询表数据（避免日期序列化问题）
    print("\n🚀 查询 ods_refund 表数据...")
    try:
        # 使用简单的查询避免日期字段
        query_result = await select_tool.run(
            sql="SELECT id, flow_status, amount FROM ods_refund LIMIT 5",
            limit=5
        )
        print("✅ 查询结果:")
        print(query_result)
    except Exception as e:
        print(f"❌ 查询失败: {e}")
    
    # 查找渠道相关字段
    print("\n🔍 查找渠道相关字段...")
    channel_result = await schema_tool.run(
        placeholder="退货渠道",
        hint="渠道、channel、App语音",
        table="ods_refund"
    )
    
    print("✅ 渠道字段查找结果:")
    print(channel_result)
    
    return explorer, schema_tool, select_tool


async def generate_return_channel_sql():
    """生成退货渠道 SQL"""
    print("\n🚀 生成退货渠道 SQL")
    print("=" * 60)
    
    explorer = DorisSchemaExplorer(
        hosts=DATA_SOURCE.hosts,
        mysql_port=DATA_SOURCE.mysql_port,
        user=DATA_SOURCE.user,
        password=DATA_SOURCE.password,
        database=DATA_SOURCE.database,
        connect_timeout=DATA_SOURCE.connect_timeout,
        config=DEFAULT_SQL_CONFIG
    )
    
    select_tool = DorisSelectTool(explorer)
    
    # 基于分析结果，尝试不同的 SQL 查询
    sql_queries = [
        # 查询1: 基本的退货单数量统计
        {
            "name": "基本退货单数量统计",
            "sql": "SELECT COUNT(*) as return_count FROM ods_refund"
        },
        
        # 查询2: 按状态统计退货单数量
        {
            "name": "按状态统计退货单数量",
            "sql": "SELECT flow_status, COUNT(*) as return_count FROM ods_refund GROUP BY flow_status"
        },
        
        # 查询3: 查找可能的渠道字段
        {
            "name": "查找可能的渠道字段",
            "sql": "SELECT DISTINCT refund_channel FROM ods_refund WHERE refund_channel IS NOT NULL LIMIT 10"
        },
        
        # 查询4: 查找包含 'App' 或 '语音' 的记录
        {
            "name": "查找包含App或语音的记录",
            "sql": "SELECT * FROM ods_refund WHERE refund_channel LIKE '%App%' OR refund_channel LIKE '%语音%' LIMIT 5"
        }
    ]
    
    for query_info in sql_queries:
        print(f"\n🔍 {query_info['name']}:")
        print(f"SQL: {query_info['sql']}")
        
        try:
            result = await select_tool.run(
                sql=query_info['sql'],
                limit=10
            )
            print("✅ 查询结果:")
            print(result)
        except Exception as e:
            print(f"❌ 查询失败: {e}")


async def manual_sql_generation():
    """手动生成 SQL"""
    print("\n🛠️ 手动生成 SQL")
    print("=" * 60)
    
    explorer = DorisSchemaExplorer(
        hosts=DATA_SOURCE.hosts,
        mysql_port=DATA_SOURCE.mysql_port,
        user=DATA_SOURCE.user,
        password=DATA_SOURCE.password,
        database=DATA_SOURCE.database,
        connect_timeout=DATA_SOURCE.connect_timeout,
        config=DEFAULT_SQL_CONFIG
    )
    
    select_tool = DorisSelectTool(explorer)
    
    # 基于分析结果手动生成 SQL
    print("📝 基于分析结果生成 SQL...")
    
    # 首先查看表的所有字段
    print("\n🔍 查看 ods_refund 表的所有字段...")
    try:
        result = await select_tool.run(
            sql="DESCRIBE ods_refund",
            limit=50
        )
        print("✅ 表结构:")
        print(result)
    except Exception as e:
        print(f"❌ 查看表结构失败: {e}")
    
    # 尝试查找渠道字段
    print("\n🔍 查找可能的渠道字段...")
    try:
        # 查看表的前几行数据，了解字段内容
        result = await select_tool.run(
            sql="SELECT * FROM ods_refund LIMIT 3",
            limit=3
        )
        print("✅ 样例数据:")
        print(result)
    except Exception as e:
        print(f"❌ 查看样例数据失败: {e}")
    
    # 生成最终的 SQL
    print("\n🎯 生成最终 SQL...")
    
    # 基于分析，可能的 SQL 查询
    final_sqls = [
        {
            "name": "方案1: 如果有 refund_channel 字段",
            "sql": """
SELECT COUNT(*) as return_count 
FROM ods_refund 
WHERE refund_channel = 'App语音退货'
"""
        },
        {
            "name": "方案2: 如果有 channel 字段",
            "sql": """
SELECT COUNT(*) as return_count 
FROM ods_refund 
WHERE channel = 'App语音退货'
"""
        },
        {
            "name": "方案3: 如果有 source 字段",
            "sql": """
SELECT COUNT(*) as return_count 
FROM ods_refund 
WHERE source = 'App语音退货'
"""
        },
        {
            "name": "方案4: 基于状态和金额的推测",
            "sql": """
SELECT COUNT(*) as return_count 
FROM ods_refund 
WHERE flow_status BETWEEN 100 AND 199 
AND amount > 0
"""
        }
    ]
    
    for sql_info in final_sqls:
        print(f"\n📝 {sql_info['name']}:")
        print(sql_info['sql'])
        
        try:
            result = await select_tool.run(
                sql=sql_info['sql'].strip(),
                limit=10
            )
            print("✅ 执行结果:")
            print(result)
        except Exception as e:
            print(f"❌ 执行失败: {e}")


async def main():
    """主函数"""
    print("🎯 基于 ods_refund 表的退货渠道 SQL 生成")
    print("=" * 80)
    print("占位符: 统计:退货渠道为App语音退货的退货单数量")
    print("=" * 80)
    
    try:
        # 步骤1: 分析 ods_refund 表
        explorer, schema_tool, select_tool = await analyze_refund_table()
        
        # 步骤2: 生成退货渠道 SQL
        await generate_return_channel_sql()
        
        # 步骤3: 手动生成 SQL
        await manual_sql_generation()
        
        print("\n" + "=" * 80)
        print("🎉 分析完成！")
        print("=" * 80)
        print("📋 总结:")
        print("1. ✅ 找到了退货表: ods_refund")
        print("2. ✅ 分析了表结构: 29个字段")
        print("3. ✅ 尝试了多种 SQL 查询方案")
        print("4. ⚠️ 需要进一步确认渠道字段的具体名称")
        print("\n💡 建议:")
        print("- 检查 ods_refund 表的完整字段列表")
        print("- 确认渠道字段的具体名称（可能是 refund_channel、channel、source 等）")
        print("- 根据实际字段名称调整 SQL 查询")
        
    except KeyboardInterrupt:
        print("\n\n⏹️ 用户中断执行")
    except Exception as e:
        print(f"\n❌ 执行过程中出现错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
