#!/usr/bin/env python3
"""测试单个占位符的 SQL 生成。

简化测试，专注于验证 SQL 生成的核心功能。
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


async def test_single_placeholder_sql():
    """测试单个占位符的 SQL 生成。"""
    print("🎯 单个占位符 SQL 生成测试")
    print("=" * 60)
    
    # 创建探索器
    explorer = DorisSchemaExplorer(
        hosts=DATA_SOURCE.hosts,
        mysql_port=DATA_SOURCE.mysql_port,
        user=DATA_SOURCE.user,
        password=DATA_SOURCE.password,
        database=DATA_SOURCE.database,
        connect_timeout=DATA_SOURCE.connect_timeout,
        config=DEFAULT_SQL_CONFIG
    )
    
    # 创建代理
    agent = build_sql_template_agent(
        explorer=explorer,
        config=DEFAULT_SQL_CONFIG,
        execution_id="single_placeholder_test"
    )
    
    # 简单的测试提示
    simple_prompt = """
请为以下占位符生成 SQL：

占位符：{{统计:总行程数}}

要求：
1. 使用 ods_itinerary 表
2. 统计总行程数量
3. 返回字段名为 total_itinerary_count
4. 使用 ```sql 代码块包裹最终 SQL

请直接生成 SQL，不需要调用工具。
"""
    
    print("📝 测试提示:")
    print(simple_prompt)
    print("\n🚀 开始执行...")
    print("=" * 60)
    
    try:
        # 使用 tt() 方法获取事件流
        turn_state = TurnState.initial(max_iterations=10)
        context = ExecutionContext.create(correlation_id="single_placeholder_test")
        messages = [Message(role="user", content=simple_prompt)]
        
        final_output = ""
        iteration_count = 0
        tool_call_count = 0
        
        async for event in agent.tt(messages, turn_state, context):
            if event.type == AgentEventType.ITERATION_START:
                iteration_count += 1
                print(f"\n🔄 [迭代 {iteration_count}] 开始")
                
            elif event.type == AgentEventType.LLM_DELTA:
                # 实时显示 LLM 输出
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
                    content_preview = event.tool_result.content[:300] + "..." if len(event.tool_result.content) > 300 else event.tool_result.content
                    print(f"📊 结果预览: {content_preview}")
                    
            elif event.type == AgentEventType.TOOL_ERROR and event.tool_result:
                print(f"\n❌ [工具错误] {event.tool_result.tool_name}: {event.tool_result.content}")
                
            elif event.type == AgentEventType.MAX_ITERATIONS_REACHED:
                print(f"\n⚠️ [警告] 达到最大迭代次数限制: {event.metadata.get('max_iterations', 0)}")
                
            elif event.type == AgentEventType.AGENT_FINISH:
                final_output = event.content or ""
                print(f"\n\n🎉 [完成] 代理执行完成")
                print(f"📊 总迭代次数: {iteration_count}")
                print(f"🛠️ 总工具调用次数: {tool_call_count}")
                
            elif event.type == AgentEventType.ERROR:
                print(f"\n❌ [错误] {event.error}")
        
        # 显示最终结果
        print("\n" + "=" * 60)
        print("🎯 最终 SQL 生成结果")
        print("=" * 60)
        
        if final_output:
            print("📄 生成的 SQL:")
            print("-" * 40)
            print(final_output)
            
            # 检查是否包含 SQL 代码块
            if "```sql" in final_output.lower():
                print("\n✅ 成功生成 SQL 代码块！")
            else:
                print("\n⚠️ 未找到 SQL 代码块")
        else:
            print("❌ 未生成最终输出")
            
        print("\n" + "=" * 60)
        print("📊 执行统计")
        print("=" * 60)
        print(f"✅ 总迭代次数: {iteration_count}")
        print(f"🛠️ 总工具调用次数: {tool_call_count}")
        print(f"📄 最终输出长度: {len(final_output)} 字符")
        
    except Exception as e:
        print(f"\n❌ 执行过程中出现错误: {e}")
        import traceback
        traceback.print_exc()


async def test_tool_directly():
    """直接测试工具功能。"""
    print("\n🔧 直接测试工具功能")
    print("=" * 60)
    
    try:
        # 创建探索器
        explorer = DorisSchemaExplorer(
            hosts=DATA_SOURCE.hosts,
            mysql_port=DATA_SOURCE.mysql_port,
            user=DATA_SOURCE.user,
            password=DATA_SOURCE.password,
            database=DATA_SOURCE.database,
            connect_timeout=DATA_SOURCE.connect_timeout,
            config=DEFAULT_SQL_CONFIG
        )
        
        # 测试 SchemaLookupTool
        print("🔍 测试 SchemaLookupTool...")
        schema_tool = SchemaLookupTool(explorer)
        lookup_result = await schema_tool.run(
            placeholder="统计:总行程数",
            hint="行程数量统计"
        )
        print(f"✅ 模式查找成功，结果长度: {len(lookup_result)} 字符")
        print(f"📊 结果预览: {lookup_result[:200]}...")
        
        # 测试 DorisSelectTool
        print("\n🔍 测试 DorisSelectTool...")
        select_tool = DorisSelectTool(explorer)
        select_result = await select_tool.run(
            sql="SELECT COUNT(*) as total_count FROM ods_itinerary LIMIT 1",
            limit=10
        )
        print(f"✅ SQL 执行成功，结果长度: {len(select_result)} 字符")
        print(f"📊 结果预览: {select_result[:200]}...")
        
    except Exception as e:
        print(f"❌ 工具测试失败: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """主函数。"""
    try:
        await test_single_placeholder_sql()
        await test_tool_directly()
    except KeyboardInterrupt:
        print("\n\n⏹️ 用户中断执行")
    except Exception as e:
        print(f"\n❌ 执行过程中出现错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
