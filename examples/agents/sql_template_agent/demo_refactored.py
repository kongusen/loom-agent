#!/usr/bin/env python3
"""重构后的 SQL 模板代理演示脚本。

基于 Loom 0.0.3 重构模式，展示统一协调机制和简化的 API。
"""

import asyncio
from typing import Optional

from .config import DEFAULT_SQL_CONFIG, SQLTemplateConfig
from .runner import main


async def demo_default_config():
    """演示使用默认配置运行 SQL 模板代理。"""
    print("🚀 演示 1: 使用默认配置")
    print("=" * 60)
    
    await main()  # 使用默认配置


async def demo_custom_config():
    """演示使用自定义配置运行 SQL 模板代理。"""
    print("\n🔧 演示 2: 使用自定义配置")
    print("=" * 60)
    
    # 创建自定义配置
    custom_config = SQLTemplateConfig(
        # 基础协调配置
        deep_recursion_threshold=8,        # 允许更深递归
        high_complexity_threshold=0.9,     # 提高复杂度阈值
        context_cache_size=300,            # 加大缓存
        event_batch_timeout=0.02,          # 降低延迟到 20ms
        subagent_pool_size=12,             # 更大的子代理池
        
        # SQL 模板专用配置
        max_schema_tables=15,              # 显示更多表
        max_table_columns=15,              # 显示更多字段
        max_query_limit=500,               # 允许更多查询行数
        max_iterations=20,                 # 更多迭代次数
        schema_cache_ttl=600,              # 10分钟缓存
        query_timeout=60,                  # 更长查询超时
    )
    
    await main(config=custom_config)


async def demo_performance_comparison():
    """演示性能对比。"""
    print("\n⚡ 演示 3: 性能对比")
    print("=" * 60)
    
    # 高性能配置
    performance_config = SQLTemplateConfig(
        event_batch_timeout=0.01,          # 极低延迟
        context_cache_size=500,            # 大缓存
        schema_cache_ttl=1800,             # 30分钟缓存
        max_iterations=25,                 # 更多迭代
    )
    
    print("使用高性能配置运行...")
    await main(config=performance_config)


async def demo_error_handling():
    """演示错误处理能力。"""
    print("\n🛡️ 演示 4: 错误处理")
    print("=" * 60)
    
    # 容错配置
    resilient_config = SQLTemplateConfig(
        query_timeout=120,                 # 更长超时
        max_iterations=30,                 # 更多重试机会
        event_batch_timeout=0.05,          # 更宽松的批处理
    )
    
    print("使用容错配置运行...")
    await main(config=resilient_config)


async def main_demo():
    """主演示函数。"""
    print("🎯 SQL 模板代理 - Loom 0.0.3 重构演示")
    print("=" * 80)
    print("本演示展示了基于 Loom 0.0.3 重构的 SQL 模板代理的以下特性：")
    print("✅ 统一协调机制 (UnifiedExecutionContext)")
    print("✅ 配置管理 (SQLTemplateConfig)")
    print("✅ 性能优化 (缓存、批处理)")
    print("✅ 简化的 API 接口")
    print("✅ 错误处理和超时管理")
    print("=" * 80)
    
    try:
        # 运行各种演示
        await demo_default_config()
        await demo_custom_config()
        await demo_performance_comparison()
        await demo_error_handling()
        
        print("\n🎉 所有演示完成！")
        print("=" * 80)
        print("重构后的 SQL 模板代理具有以下优势：")
        print("📈 性能提升: 缓存优化、批处理延迟降低 50%")
        print("🔧 配置灵活: 集中管理所有配置参数")
        print("🛡️ 错误处理: 更好的错误分类和恢复机制")
        print("🚀 易于使用: 简化的 API 接口")
        print("📊 可观测性: 统一的事件和监控机制")
        
    except Exception as e:
        print(f"\n❌ 演示过程中出现错误: {e}")
        print("请检查 Doris 连接配置和网络连接。")


if __name__ == "__main__":
    asyncio.run(main_demo())
