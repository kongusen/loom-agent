#!/usr/bin/env python3
"""自主 SQL 模板代理演示

展示完整的自主分析流程：
1. 表发现和结构分析
2. 数据采样和观察
3. SQL 生成和验证
4. 结果返回和报告
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from examples.agents.sql_template_agent.config import (
    AUTONOMOUS_ANALYSIS_CONFIG, 
    DATA_SOURCE
)
from examples.agents.sql_template_agent.metadata import DorisSchemaExplorer
from examples.agents.sql_template_agent.autonomous_agent import (
    AutonomousSQLTemplateAgent,
    AutonomousAnalysisConfig,
    create_autonomous_agent
)


async def demo_single_placeholder_analysis():
    """演示单个占位符的自主分析"""
    print("🎯 单个占位符自主分析演示")
    print("=" * 80)
    
    # 创建探索器
    explorer = DorisSchemaExplorer(
        hosts=DATA_SOURCE.hosts,
        mysql_port=DATA_SOURCE.mysql_port,
        user=DATA_SOURCE.user,
        password=DATA_SOURCE.password,
        database=DATA_SOURCE.database,
        connect_timeout=DATA_SOURCE.connect_timeout,
        config=AUTONOMOUS_ANALYSIS_CONFIG
    )
    
    # 创建自主分析配置
    analysis_config = AutonomousAnalysisConfig(
        max_table_discovery_attempts=3,
        max_sample_queries=5,
        sample_data_limit=10,
        enable_data_observation=True,
        enable_sql_validation=True,
        analysis_timeout=300
    )
    
    # 创建自主代理
    agent = create_autonomous_agent(
        explorer=explorer,
        config=AUTONOMOUS_ANALYSIS_CONFIG,
        analysis_config=analysis_config
    )
    
    # 测试占位符
    test_placeholder = "统计:退货渠道为App语音退货的退货单数量"
    
    print(f"📝 测试占位符: {test_placeholder}")
    print("\n🚀 开始自主分析...")
    print("=" * 80)
    
    try:
        # 执行自主分析
        result = await agent.analyze_placeholder(test_placeholder)
        
        # 显示分析结果
        print("\n" + "=" * 80)
        print("🎯 自主分析结果")
        print("=" * 80)
        
        print(f"📝 占位符: {result.placeholder}")
        print(f"🎯 目标表: {result.target_table}")
        print(f"✅ 分析状态: {'成功' if result.success else '失败'}")
        
        if result.table_structure:
            print(f"\n📊 表结构信息:")
            print(f"   表名: {result.table_structure.get('table')}")
            print(f"   表注释: {result.table_structure.get('table_comment')}")
            columns = result.table_structure.get('columns', [])
            print(f"   字段数量: {len(columns)}")
            if columns:
                print("   主要字段:")
                for col in columns[:5]:  # 显示前5个字段
                    print(f"     - {col.get('column')} ({col.get('data_type')}): {col.get('comment')}")
        
        if result.sample_data:
            print(f"\n🔍 样例数据 ({len(result.sample_data)} 条):")
            for i, data in enumerate(result.sample_data[:3]):  # 显示前3条
                print(f"   记录 {i+1}: {data}")
        
        if result.generated_sql:
            print(f"\n🚀 生成的 SQL:")
            print("-" * 40)
            print(result.generated_sql)
            print("-" * 40)
        
        if result.query_result:
            print(f"\n✅ 查询验证结果:")
            if result.query_result.get("status") == "success":
                rows = result.query_result.get("rows", [])
                print(f"   查询状态: 成功")
                print(f"   返回行数: {len(rows)}")
                if rows:
                    print(f"   查询结果: {rows[0]}")
            else:
                print(f"   查询状态: 失败")
                print(f"   错误信息: {result.query_result.get('error')}")
        
        if result.analysis_summary:
            print(f"\n📋 分析摘要:")
            print(result.analysis_summary)
        
        if result.error_message:
            print(f"\n❌ 错误信息: {result.error_message}")
        
        print("\n" + "=" * 80)
        print("🎉 自主分析完成！")
        print("=" * 80)
        
        return result
        
    except Exception as e:
        print(f"\n❌ 自主分析失败: {e}")
        import traceback
        traceback.print_exc()
        return None


async def demo_template_analysis():
    """演示整个模板的自主分析"""
    print("\n🎯 模板文件自主分析演示")
    print("=" * 80)
    
    # 创建探索器
    explorer = DorisSchemaExplorer(
        hosts=DATA_SOURCE.hosts,
        mysql_port=DATA_SOURCE.mysql_port,
        user=DATA_SOURCE.user,
        password=DATA_SOURCE.password,
        database=DATA_SOURCE.database,
        connect_timeout=DATA_SOURCE.connect_timeout,
        config=AUTONOMOUS_ANALYSIS_CONFIG
    )
    
    # 创建自主分析配置
    analysis_config = AutonomousAnalysisConfig(
        max_table_discovery_attempts=2,  # 减少尝试次数以加快演示
        max_sample_queries=3,
        sample_data_limit=5,
        enable_data_observation=True,
        enable_sql_validation=True,
        analysis_timeout=180
    )
    
    # 创建自主代理
    agent = create_autonomous_agent(
        explorer=explorer,
        config=AUTONOMOUS_ANALYSIS_CONFIG,
        analysis_config=analysis_config
    )
    
    # 模板文件路径
    template_path = Path(__file__).parent.parent / "模板.md"
    
    if not template_path.exists():
        print(f"❌ 模板文件不存在: {template_path}")
        return
    
    print(f"📄 分析模板文件: {template_path}")
    print("\n🚀 开始模板分析...")
    print("=" * 80)
    
    try:
        # 执行模板分析
        results = await agent.analyze_template(template_path)
        
        # 显示分析结果
        print("\n" + "=" * 80)
        print("🎯 模板分析结果")
        print("=" * 80)
        
        print(f"📊 总占位符数量: {len(results)}")
        
        success_count = sum(1 for r in results if r.success)
        print(f"✅ 成功分析: {success_count}")
        print(f"❌ 失败分析: {len(results) - success_count}")
        
        print(f"\n📋 详细结果:")
        for i, result in enumerate(results, 1):
            print(f"\n{i}. {result.placeholder}")
            print(f"   状态: {'✅ 成功' if result.success else '❌ 失败'}")
            if result.target_table:
                print(f"   目标表: {result.target_table}")
            if result.generated_sql:
                print(f"   生成 SQL: {result.generated_sql[:100]}...")
            if result.query_result and result.query_result.get("status") == "success":
                rows = result.query_result.get("rows", [])
                if rows:
                    print(f"   查询结果: {rows[0]}")
        
        print("\n" + "=" * 80)
        print("🎉 模板分析完成！")
        print("=" * 80)
        
        return results
        
    except Exception as e:
        print(f"\n❌ 模板分析失败: {e}")
        import traceback
        traceback.print_exc()
        return None


async def demo_multiple_placeholders():
    """演示多个占位符的自主分析"""
    print("\n🎯 多个占位符自主分析演示")
    print("=" * 80)
    
    # 创建探索器
    explorer = DorisSchemaExplorer(
        hosts=DATA_SOURCE.hosts,
        mysql_port=DATA_SOURCE.mysql_port,
        user=DATA_SOURCE.user,
        password=DATA_SOURCE.password,
        database=DATA_SOURCE.database,
        connect_timeout=DATA_SOURCE.connect_timeout,
        config=AUTONOMOUS_ANALYSIS_CONFIG
    )
    
    # 创建自主分析配置
    analysis_config = AutonomousAnalysisConfig(
        max_table_discovery_attempts=2,
        max_sample_queries=3,
        sample_data_limit=5,
        enable_data_observation=True,
        enable_sql_validation=True,
        analysis_timeout=120
    )
    
    # 创建自主代理
    agent = create_autonomous_agent(
        explorer=explorer,
        config=AUTONOMOUS_ANALYSIS_CONFIG,
        analysis_config=analysis_config
    )
    
    # 测试占位符列表
    test_placeholders = [
        "统计:总行程数",
        "统计:最活跃导游",
        "统计:平均团队规模",
        "统计:退货渠道为App语音退货的退货单数量"
    ]
    
    print(f"📝 测试占位符列表:")
    for i, placeholder in enumerate(test_placeholders, 1):
        print(f"   {i}. {placeholder}")
    
    print("\n🚀 开始批量分析...")
    print("=" * 80)
    
    try:
        results = []
        
        for i, placeholder in enumerate(test_placeholders, 1):
            print(f"\n📊 分析占位符 {i}/{len(test_placeholders)}: {placeholder}")
            
            result = await agent.analyze_placeholder(placeholder)
            results.append(result)
            
            # 显示简要结果
            if result.success:
                print(f"   ✅ 成功 - 目标表: {result.target_table}")
                if result.query_result and result.query_result.get("status") == "success":
                    rows = result.query_result.get("rows", [])
                    if rows:
                        print(f"   📊 结果: {rows[0]}")
            else:
                print(f"   ❌ 失败 - {result.error_message}")
        
        # 显示汇总结果
        print("\n" + "=" * 80)
        print("🎯 批量分析汇总")
        print("=" * 80)
        
        success_count = sum(1 for r in results if r.success)
        print(f"📊 总占位符数量: {len(results)}")
        print(f"✅ 成功分析: {success_count}")
        print(f"❌ 失败分析: {len(results) - success_count}")
        print(f"📈 成功率: {success_count/len(results)*100:.1f}%")
        
        print(f"\n📋 成功案例:")
        for i, result in enumerate(results, 1):
            if result.success:
                print(f"   {i}. {result.placeholder}")
                print(f"      目标表: {result.target_table}")
                if result.generated_sql:
                    print(f"      SQL: {result.generated_sql}")
                if result.query_result and result.query_result.get("status") == "success":
                    rows = result.query_result.get("rows", [])
                    if rows:
                        print(f"      结果: {rows[0]}")
        
        print("\n" + "=" * 80)
        print("🎉 批量分析完成！")
        print("=" * 80)
        
        return results
        
    except Exception as e:
        print(f"\n❌ 批量分析失败: {e}")
        import traceback
        traceback.print_exc()
        return None


async def main():
    """主函数"""
    print("🎯 自主 SQL 模板代理演示")
    print("=" * 80)
    print("基于 Loom 0.0.3 重构的自主分析能力")
    print("=" * 80)
    
    try:
        # 演示1: 单个占位符分析
        await demo_single_placeholder_analysis()
        
        # 演示2: 多个占位符分析
        await demo_multiple_placeholders()
        
        # 演示3: 模板文件分析（可选）
        # await demo_template_analysis()
        
        print("\n" + "=" * 80)
        print("🎉 所有演示完成！")
        print("=" * 80)
        print("📋 重构成果总结:")
        print("✅ 自主表发现和结构分析")
        print("✅ 智能数据采样和观察")
        print("✅ 基于真实数据的 SQL 生成")
        print("✅ 自动 SQL 验证和结果返回")
        print("✅ 完整的分析报告和摘要")
        print("✅ 支持批量占位符分析")
        print("✅ 基于 Loom 0.0.3 统一协调机制")
        
    except KeyboardInterrupt:
        print("\n\n⏹️ 用户中断执行")
    except Exception as e:
        print(f"\n❌ 执行过程中出现错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
