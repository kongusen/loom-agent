#!/usr/bin/env python3
"""完整的占位符 SQL 生成和验证流程。

基于占位符"统计:退货渠道为App语音退货的退货单数量"进行：
1. 查找相关表
2. 分析表结构
3. 生成 SQL
4. 验证查询结果
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
from examples.agents.sql_template_agent.agent import build_sql_template_agent
from loom.core.events import AgentEventType
from loom.core.turn_state import TurnState
from loom.core.execution_context import ExecutionContext
from loom.core.types import Message


async def step1_find_relevant_tables():
    """步骤1: 查找与退货相关的表"""
    print("🔍 步骤1: 查找与退货相关的表")
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
    
    # 查找退货相关的表
    print("🔍 查找退货相关表...")
    result = await schema_tool.run(
        placeholder="统计:退货渠道为App语音退货的退货单数量",
        hint="退货单、退货渠道、App语音退货"
    )
    
    print("✅ 查找结果:")
    print(result)
    
    return explorer, schema_tool


async def step2_analyze_table_structure(explorer, schema_tool):
    """步骤2: 分析表结构"""
    print("\n📊 步骤2: 分析表结构")
    print("=" * 60)
    
    # 查找可能的退货表
    print("🔍 查找可能的退货表...")
    result = await schema_tool.run(
        placeholder="退货单",
        hint="退货、退款、return"
    )
    
    print("✅ 退货表查找结果:")
    print(result)
    
    # 查找渠道相关表
    print("\n🔍 查找渠道相关表...")
    result2 = await schema_tool.run(
        placeholder="退货渠道",
        hint="渠道、channel、App语音"
    )
    
    print("✅ 渠道表查找结果:")
    print(result2)


async def step3_generate_sql():
    """步骤3: 生成 SQL"""
    print("\n🚀 步骤3: 生成 SQL")
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
    
    agent = build_sql_template_agent(
        explorer=explorer,
        config=DEFAULT_SQL_CONFIG,
        execution_id="return_channel_analysis"
    )
    
    # 详细的 SQL 生成提示
    sql_prompt = """
请为以下占位符生成 SQL：

占位符：{{统计:退货渠道为App语音退货的退货单数量}}

要求：
1. 首先使用 schema_lookup 工具查找包含"退货"、"渠道"、"App语音"等关键词的表
2. 分析表结构，找到退货单表和渠道字段
3. 生成 SQL 查询退货渠道为"App语音退货"的退货单数量
4. 返回字段名为 return_count
5. 使用 ```sql 代码块包裹最终 SQL

请按步骤执行：
- 先查找退货相关表
- 再查找渠道相关字段
- 最后生成准确的 SQL 查询
"""
    
    print("📝 SQL 生成提示:")
    print(sql_prompt)
    print("\n🚀 开始生成 SQL...")
    print("=" * 60)
    
    try:
        turn_state = TurnState.initial(max_iterations=20)
        context = ExecutionContext.create(correlation_id="return_channel_analysis")
        messages = [Message(role="user", content=sql_prompt)]
        
        final_output = ""
        iteration_count = 0
        tool_call_count = 0
        
        async for event in agent.tt(messages, turn_state, context):
            if event.type == AgentEventType.ITERATION_START:
                iteration_count += 1
                print(f"\n🔄 [迭代 {iteration_count}] 开始")
                
            elif event.type == AgentEventType.LLM_DELTA:
                print(event.content or "", end="", flush=True)
                
            elif event.type == AgentEventType.TOOL_EXECUTION_START and event.tool_call:
                tool_call_count += 1
                print(f"\n\n🛠️ [工具调用 {tool_call_count}] {event.tool_call.name}")
                if event.tool_call.arguments:
                    args_preview = str(event.tool_call.arguments)[:200]
                    print(f"📝 参数: {args_preview}{'...' if len(str(event.tool_call.arguments)) > 200 else ''}")
                    
            elif event.type == AgentEventType.TOOL_RESULT and event.tool_result:
                print(f"\n✅ [工具结果] {event.tool_result.tool_name}")
                if event.tool_result.content:
                    content_preview = event.tool_result.content[:500] + "..." if len(event.tool_result.content) > 500 else event.tool_result.content
                    print(f"📊 结果预览: {content_preview}")
                    
            elif event.type == AgentEventType.TOOL_ERROR and event.tool_result:
                print(f"\n❌ [工具错误] {event.tool_result.tool_name}: {event.tool_result.content}")
                
            elif event.type == AgentEventType.MAX_ITERATIONS_REACHED:
                print(f"\n⚠️ [警告] 达到最大迭代次数限制")
                
            elif event.type == AgentEventType.AGENT_FINISH:
                final_output = event.content or ""
                print(f"\n\n🎉 [完成] SQL 生成完成")
                
            elif event.type == AgentEventType.ERROR:
                print(f"\n❌ [错误] {event.error}")
        
        print("\n" + "=" * 60)
        print("🎯 生成的 SQL")
        print("=" * 60)
        
        if final_output:
            print("📄 最终 SQL:")
            print("-" * 40)
            print(final_output)
            
            # 提取 SQL 代码块
            if "```sql" in final_output.lower():
                print("\n✅ 成功生成 SQL 代码块！")
                return final_output
            else:
                print("\n⚠️ 未找到 SQL 代码块")
        else:
            print("❌ 未生成 SQL")
            
        print(f"\n📊 执行统计: {iteration_count} 次迭代, {tool_call_count} 次工具调用")
        
    except Exception as e:
        print(f"\n❌ SQL 生成失败: {e}")
        import traceback
        traceback.print_exc()
    
    return None


async def step4_verify_query(sql_output):
    """步骤4: 验证查询结果"""
    print("\n🔍 步骤4: 验证查询结果")
    print("=" * 60)
    
    if not sql_output:
        print("❌ 没有 SQL 可以验证")
        return
    
    # 提取 SQL 语句
    sql_lines = []
    in_sql_block = False
    
    for line in sql_output.split('\n'):
        if '```sql' in line.lower():
            in_sql_block = True
            continue
        elif '```' in line and in_sql_block:
            break
        elif in_sql_block:
            sql_lines.append(line)
    
    if not sql_lines:
        print("❌ 无法提取 SQL 语句")
        return
    
    sql_query = '\n'.join(sql_lines).strip()
    print(f"📝 提取的 SQL:")
    print(sql_query)
    
    # 执行查询验证
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
    
    try:
        print(f"\n🚀 执行查询验证...")
        result = await select_tool.run(
            sql=sql_query,
            limit=10
        )
        
        print("✅ 查询验证结果:")
        print(result)
        
        # 解析结果
        import json
        try:
            result_data = json.loads(result)
            if result_data.get("status") == "success":
                rows = result_data.get("rows", [])
                if rows:
                    print(f"\n🎉 查询成功！找到 {len(rows)} 条记录")
                    for i, row in enumerate(rows):
                        print(f"  记录 {i+1}: {row}")
                else:
                    print("\n⚠️ 查询成功但没有找到记录")
            else:
                print(f"\n❌ 查询失败: {result_data.get('error', '未知错误')}")
        except json.JSONDecodeError:
            print("❌ 无法解析查询结果")
            
    except Exception as e:
        print(f"❌ 查询验证失败: {e}")


async def step5_manual_analysis():
    """步骤5: 手动分析可能的表结构"""
    print("\n🔍 步骤5: 手动分析可能的表结构")
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
    
    # 手动查找可能的表
    possible_tables = [
        "ods_return", "ods_refund", "ods_order_return", 
        "ods_return_order", "return_order", "refund_order"
    ]
    
    print("🔍 手动查找可能的退货表...")
    for table_name in possible_tables:
        try:
            result = await schema_tool.run(
                placeholder=f"表 {table_name}",
                table=table_name
            )
            print(f"\n📊 表 {table_name} 查找结果:")
            print(result[:500] + "..." if len(result) > 500 else result)
        except Exception as e:
            print(f"❌ 查找表 {table_name} 失败: {e}")
    
    # 尝试查找所有表
    print("\n🔍 查找所有表...")
    try:
        schema = await explorer.load_schema()
        print(f"📊 数据库中共有 {len(schema)} 张表:")
        
        # 查找包含退货关键词的表
        return_tables = []
        for table_name in schema.keys():
            if any(keyword in table_name.lower() for keyword in ['return', 'refund', '退货', '退款']):
                return_tables.append(table_name)
        
        if return_tables:
            print(f"✅ 找到可能的退货表: {return_tables}")
            
            # 分析第一个退货表的结构
            if return_tables:
                table_name = return_tables[0]
                table_info = schema[table_name]
                print(f"\n📊 表 {table_name} 的结构:")
                print(f"   表注释: {table_info.comment}")
                print(f"   字段数量: {len(table_info.columns)}")
                print("   字段列表:")
                for col in table_info.columns[:10]:  # 显示前10个字段
                    print(f"     - {col.name} ({col.data_type}): {col.comment}")
                
                # 尝试查询这个表
                print(f"\n🚀 尝试查询表 {table_name}...")
                try:
                    query_result = await select_tool.run(
                        sql=f"SELECT * FROM {table_name} LIMIT 5",
                        limit=5
                    )
                    print("✅ 查询结果:")
                    print(query_result)
                except Exception as e:
                    print(f"❌ 查询失败: {e}")
        else:
            print("⚠️ 未找到明显的退货表")
            print("📋 所有表名:")
            for i, table_name in enumerate(list(schema.keys())[:20]):  # 显示前20个表
                print(f"   {i+1}. {table_name}")
                
    except Exception as e:
        print(f"❌ 分析表结构失败: {e}")


async def main():
    """主函数 - 完整的占位符分析流程"""
    print("🎯 占位符 SQL 生成和验证完整流程")
    print("=" * 80)
    print("占位符: 统计:退货渠道为App语音退货的退货单数量")
    print("=" * 80)
    
    try:
        # 步骤1: 查找相关表
        explorer, schema_tool = await step1_find_relevant_tables()
        
        # 步骤2: 分析表结构
        await step2_analyze_table_structure(explorer, schema_tool)
        
        # 步骤3: 生成 SQL
        sql_output = await step3_generate_sql()
        
        # 步骤4: 验证查询结果
        await step4_verify_query(sql_output)
        
        # 步骤5: 手动分析
        await step5_manual_analysis()
        
        print("\n" + "=" * 80)
        print("🎉 完整流程执行完成！")
        print("=" * 80)
        
    except KeyboardInterrupt:
        print("\n\n⏹️ 用户中断执行")
    except Exception as e:
        print(f"\n❌ 执行过程中出现错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
