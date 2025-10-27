#!/usr/bin/env python3
"""完整的 SQL 生成过程演示。

基于 Loom 0.0.3 重构模式，展示从模板解析到 SQL 生成的完整流程。
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from examples.agents.sql_template_agent.config import (
    DEFAULT_SQL_CONFIG, 
    SQLTemplateConfig,
    DATA_SOURCE,
    TEMPLATE_PATH
)
from examples.agents.sql_template_agent.metadata import DorisSchemaExplorer
from examples.agents.sql_template_agent.context_builder import (
    parse_placeholders,
    build_coordinator_prompt
)
from examples.agents.sql_template_agent.agent import build_sql_template_agent
from loom.core.events import AgentEventType
from loom.core.turn_state import TurnState
from loom.core.execution_context import ExecutionContext
from loom.core.types import Message


async def run_complete_sql_generation():
    """运行完整的 SQL 生成过程。"""
    print("🎯 SQL 模板代理 - 完整 SQL 生成过程演示")
    print("=" * 80)
    print("基于 Loom 0.0.3 重构模式，展示统一协调机制和简化的 API")
    print("=" * 80)
    
    # 步骤 1: 加载模板文件
    print("\n📄 步骤 1: 加载模板文件")
    print("-" * 50)
    
    try:
        template_text = TEMPLATE_PATH.read_text(encoding="utf-8")
        print(f"✅ 模板文件加载成功")
        print(f"📊 模板长度: {len(template_text)} 字符")
        print(f"📁 文件路径: {TEMPLATE_PATH}")
        
        # 显示模板内容预览
        preview = template_text[:200] + "..." if len(template_text) > 200 else template_text
        print(f"📋 模板预览:\n{preview}")
        
    except Exception as e:
        print(f"❌ 模板文件加载失败: {e}")
        return
    
    # 步骤 2: 解析占位符
    print("\n🔍 步骤 2: 解析占位符")
    print("-" * 50)
    
    try:
        placeholders = parse_placeholders(template_text)
        print(f"✅ 占位符解析成功，共 {len(placeholders)} 个占位符")
        
        for i, placeholder in enumerate(placeholders, 1):
            print(f"   {i}. {placeholder['placeholder']} (分类: {placeholder['category']})")
        
    except Exception as e:
        print(f"❌ 占位符解析失败: {e}")
        return
    
    # 步骤 3: 创建配置和探索器
    print("\n⚙️ 步骤 3: 创建配置和探索器")
    print("-" * 50)
    
    try:
        # 使用优化的配置
        config = SQLTemplateConfig(
            deep_recursion_threshold=8,        # 允许更深递归
            high_complexity_threshold=0.9,     # 提高复杂度阈值
            context_cache_size=300,            # 加大缓存
            event_batch_timeout=0.02,          # 降低延迟到 20ms
            max_iterations=20,                 # 更多迭代次数
            schema_cache_ttl=600,              # 10分钟缓存
            query_timeout=60,                  # 更长查询超时
        )
        print(f"✅ 配置创建成功")
        print(f"   - 深度递归阈值: {config.deep_recursion_threshold}")
        print(f"   - 复杂度阈值: {config.high_complexity_threshold}")
        print(f"   - 缓存大小: {config.context_cache_size}")
        print(f"   - 批处理超时: {config.event_batch_timeout}s")
        print(f"   - 最大迭代次数: {config.max_iterations}")
        
        # 创建探索器
        explorer = DorisSchemaExplorer(
            hosts=DATA_SOURCE.hosts,
            mysql_port=DATA_SOURCE.mysql_port,
            user=DATA_SOURCE.user,
            password=DATA_SOURCE.password,
            database=DATA_SOURCE.database,
            connect_timeout=DATA_SOURCE.connect_timeout,
            config=config
        )
        print(f"✅ DorisSchemaExplorer 创建成功")
        
    except Exception as e:
        print(f"❌ 配置和探索器创建失败: {e}")
        return
    
    # 步骤 4: 加载数据库模式
    print("\n🗄️ 步骤 4: 加载数据库模式")
    print("-" * 50)
    
    try:
        schema = await explorer.load_schema()
        print(f"✅ 数据库模式加载成功，共 {len(schema)} 张表")
        
        # 显示部分表信息
        table_names = list(schema.keys())[:10]
        print(f"📋 示例表名: {', '.join(table_names)}")
        
        # 显示主要表的结构
        main_tables = ['ods_itinerary', 'ods_guide', 'ods_complain']
        for table_name in main_tables:
            if table_name in schema:
                table_info = schema[table_name]
                print(f"   📊 {table_name}: {len(table_info.columns)} 个字段")
                # 显示前几个字段
                columns_preview = [col.name for col in table_info.columns[:5]]
                print(f"      字段示例: {', '.join(columns_preview)}")
        
    except Exception as e:
        print(f"❌ 数据库模式加载失败: {e}")
        print("💡 请检查 Doris 连接配置和网络连接")
        return
    
    # 步骤 5: 构建上下文
    print("\n🏗️ 步骤 5: 构建上下文")
    print("-" * 50)
    
    try:
        data_source_summary = {
            "type": "doris",
            "hosts": ",".join(DATA_SOURCE.hosts),
            "mysql_port": str(DATA_SOURCE.mysql_port),
            "http_port": str(DATA_SOURCE.http_port),
            "database": DATA_SOURCE.database,
            "user": DATA_SOURCE.user,
        }
        
        prompt = build_coordinator_prompt(
            template_text=template_text,
            placeholders=placeholders,
            schema_snapshot=schema,
            data_source_summary=data_source_summary,
            config=config
        )
        
        print(f"✅ 上下文构建成功")
        print(f"📊 提示语长度: {len(prompt)} 字符")
        print(f"🔧 使用配置: max_schema_tables={config.max_schema_tables}, max_table_columns={config.max_table_columns}")
        
    except Exception as e:
        print(f"❌ 上下文构建失败: {e}")
        return
    
    # 步骤 6: 创建代理
    print("\n🤖 步骤 6: 创建代理")
    print("-" * 50)
    
    try:
        agent = build_sql_template_agent(
            explorer=explorer,
            config=config,
            execution_id="complete_sql_generation_demo"
        )
        
        print(f"✅ 代理创建成功")
        print(f"   - 执行 ID: complete_sql_generation_demo")
        print(f"   - 最大迭代次数: {agent.max_iterations}")
        print(f"   - 工具数量: {len(agent.tools)}")
        print(f"   - 工具列表: {[tool.name for tool in agent.tools]}")
        
    except Exception as e:
        print(f"❌ 代理创建失败: {e}")
        return
    
    # 步骤 7: 执行 SQL 生成
    print("\n🚀 步骤 7: 执行 SQL 生成")
    print("-" * 50)
    print("开始执行代理，生成 SQL...")
    print("=" * 80)
    
    try:
        final_output = ""
        iteration_count = 0
        tool_call_count = 0
        
        # 使用 tt() 方法获取事件流
        turn_state = TurnState.initial(max_iterations=agent.max_iterations)
        context = ExecutionContext.create(correlation_id="complete_sql_generation_demo")
        messages = [Message(role="user", content=prompt)]
        
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
        
        # 步骤 8: 显示最终结果
        print("\n" + "=" * 80)
        print("🎯 最终 SQL 生成结果")
        print("=" * 80)
        
        if final_output:
            print("📄 生成的 SQL 和说明:")
            print("-" * 50)
            print(final_output)
        else:
            print("❌ 未生成最终输出")
            
        print("\n" + "=" * 80)
        print("📊 执行统计")
        print("=" * 80)
        print(f"✅ 总迭代次数: {iteration_count}")
        print(f"🛠️ 总工具调用次数: {tool_call_count}")
        print(f"📄 最终输出长度: {len(final_output)} 字符")
        print(f"⚙️ 使用配置: {config}")
        
        print("\n🎉 SQL 生成过程完成！")
        print("=" * 80)
        print("重构后的 SQL 模板代理成功展示了以下特性：")
        print("✅ 统一协调机制 - 使用 UnifiedExecutionContext")
        print("✅ 配置管理 - 使用 SQLTemplateConfig")
        print("✅ 性能优化 - 缓存机制和批处理优化")
        print("✅ 简化 API - 更清晰的接口设计")
        print("✅ 错误处理 - 更好的错误分类和恢复")
        print("✅ 可观测性 - 详细的事件和监控")
        
    except Exception as e:
        print(f"\n❌ SQL 生成过程失败: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """主函数。"""
    try:
        await run_complete_sql_generation()
    except KeyboardInterrupt:
        print("\n\n⏹️ 用户中断执行")
    except Exception as e:
        print(f"\n❌ 执行过程中出现错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
