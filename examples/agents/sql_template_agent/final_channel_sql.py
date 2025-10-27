#!/usr/bin/env python3
"""最终 SQL 生成 - 基于 refund_channel_name 字段。

重大发现：
1. ods_refund 表存在 refund_channel_name 字段
2. refund_channel_name 包含 "App语音退货" 这个值
3. 可以直接使用渠道名称进行查询
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
from examples.agents.sql_template_agent.tools import DorisSelectTool


async def generate_final_sql():
    """生成最终的 SQL"""
    print("🎯 生成最终的 SQL - 基于 refund_channel_name 字段")
    print("=" * 80)
    
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
    
    # 最终 SQL 查询
    print("📝 生成最终的 SQL 查询...")
    
    # 方案1: 直接使用渠道名称查询
    print("\n🔍 方案1: 直接使用渠道名称查询")
    try:
        result = await select_tool.run(
            sql="SELECT COUNT(*) as return_count FROM ods_refund WHERE refund_channel_name = 'App语音退货'",
            limit=10
        )
        print("✅ 查询结果:")
        print(result)
    except Exception as e:
        print(f"❌ 查询失败: {e}")
    
    # 方案2: 排除已删除和撤销的记录
    print("\n🔍 方案2: 排除已删除和撤销的记录")
    try:
        result = await select_tool.run(
            sql="SELECT COUNT(*) as return_count FROM ods_refund WHERE refund_channel_name = 'App语音退货' AND is_deleted = 0 AND flow_status NOT IN (600, 699)",
            limit=10
        )
        print("✅ 查询结果:")
        print(result)
    except Exception as e:
        print(f"❌ 查询失败: {e}")
    
    # 方案3: 查看所有渠道的分布
    print("\n🔍 方案3: 查看所有渠道的分布")
    try:
        result = await select_tool.run(
            sql="SELECT refund_channel_name, COUNT(*) as count FROM ods_refund GROUP BY refund_channel_name ORDER BY count DESC",
            limit=20
        )
        print("✅ 所有渠道分布:")
        print(result)
    except Exception as e:
        print(f"❌ 查询失败: {e}")
    
    # 方案4: 查看 App语音退货 的详细状态分布
    print("\n🔍 方案4: 查看 App语音退货 的详细状态分布")
    try:
        result = await select_tool.run(
            sql="SELECT flow_status, COUNT(*) as count FROM ods_refund WHERE refund_channel_name = 'App语音退货' GROUP BY flow_status ORDER BY count DESC",
            limit=20
        )
        print("✅ App语音退货状态分布:")
        print(result)
    except Exception as e:
        print(f"❌ 查询失败: {e}")
    
    # 方案5: 查看 App语音退货 的样例数据
    print("\n🔍 方案5: 查看 App语音退货 的样例数据")
    try:
        result = await select_tool.run(
            sql="SELECT id, refund_channel_name, flow_status, amount, create_time FROM ods_refund WHERE refund_channel_name = 'App语音退货' LIMIT 5",
            limit=5
        )
        print("✅ App语音退货样例数据:")
        print(result)
    except Exception as e:
        print(f"❌ 查询失败: {e}")


async def create_final_solution():
    """创建最终的解决方案"""
    print("\n🎯 创建最终的解决方案")
    print("=" * 80)
    
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
    
    # 最终解决方案
    print("📝 最终解决方案:")
    
    # 基础查询
    print("\n🔍 基础查询 - 统计 App语音退货 的退货单数量:")
    try:
        result = await select_tool.run(
            sql="SELECT COUNT(*) as return_count FROM ods_refund WHERE refund_channel_name = 'App语音退货'",
            limit=10
        )
        print("✅ 基础查询结果:")
        print(result)
        
        # 解析结果
        import json
        result_data = json.loads(result)
        if result_data.get("status") == "success":
            rows = result_data.get("rows", [])
            if rows:
                return_count = rows[0].get("return_count", 0)
                print(f"\n🎉 最终结果: App语音退货的退货单数量为 {return_count} 条")
            else:
                print("\n⚠️ 没有找到记录")
        else:
            print(f"\n❌ 查询失败: {result_data.get('error', '未知错误')}")
            
    except Exception as e:
        print(f"❌ 查询失败: {e}")
    
    # 优化查询
    print("\n🔍 优化查询 - 排除已删除和撤销的记录:")
    try:
        result = await select_tool.run(
            sql="SELECT COUNT(*) as return_count FROM ods_refund WHERE refund_channel_name = 'App语音退货' AND is_deleted = 0 AND flow_status NOT IN (600, 699)",
            limit=10
        )
        print("✅ 优化查询结果:")
        print(result)
        
        # 解析结果
        import json
        result_data = json.loads(result)
        if result_data.get("status") == "success":
            rows = result_data.get("rows", [])
            if rows:
                return_count = rows[0].get("return_count", 0)
                print(f"\n🎉 优化结果: App语音退货的有效退货单数量为 {return_count} 条")
            else:
                print("\n⚠️ 没有找到记录")
        else:
            print(f"\n❌ 查询失败: {result_data.get('error', '未知错误')}")
            
    except Exception as e:
        print(f"❌ 查询失败: {e}")


async def main():
    """主函数"""
    print("🎯 最终 SQL 生成 - 基于 refund_channel_name 字段")
    print("=" * 80)
    print("占位符: 统计:退货渠道为App语音退货的退货单数量")
    print("=" * 80)
    
    try:
        # 步骤1: 生成最终 SQL
        await generate_final_sql()
        
        # 步骤2: 创建最终解决方案
        await create_final_solution()
        
        print("\n" + "=" * 80)
        print("🎉 分析完成！")
        print("=" * 80)
        print("📋 关键发现:")
        print("1. ✅ 找到了退货表: ods_refund")
        print("2. ✅ 确认了渠道名称字段: refund_channel_name")
        print("3. ✅ 发现渠道名称包含: 'App语音退货'")
        print("4. ✅ 可以直接使用渠道名称进行查询")
        print("\n🎯 最终的 SQL 查询:")
        print("```sql")
        print("-- 基础查询")
        print("SELECT COUNT(*) as return_count")
        print("FROM ods_refund")
        print("WHERE refund_channel_name = 'App语音退货'")
        print("")
        print("-- 优化查询（排除已删除和撤销的记录）")
        print("SELECT COUNT(*) as return_count")
        print("FROM ods_refund")
        print("WHERE refund_channel_name = 'App语音退货'")
        print("AND is_deleted = 0")
        print("AND flow_status NOT IN (600, 699)")
        print("```")
        print("\n💡 说明:")
        print("- 基础查询: 统计所有 App语音退货 的退货单数量")
        print("- 优化查询: 排除已删除和游客撤销的记录")
        print("- 可以根据业务需求选择合适的查询方案")
        
    except KeyboardInterrupt:
        print("\n\n⏹️ 用户中断执行")
    except Exception as e:
        print(f"\n❌ 执行过程中出现错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
