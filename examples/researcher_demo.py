"""研究员Agent演示 - 展示智能搜索和反思能力"""

import asyncio
import sys
from typing import List

from loom.agents.researcher import ResearcherAgent, ResearchResult
from loom.core.events import AgentEvent, AgentEventType


async def demo_research_workflow():
    """演示完整的研究工作流"""
    print("=" * 80)
    print("🎓 研究员Agent演示")
    print("=" * 80)
    print()

    # 创建研究员Agent
    print("🚀 初始化研究员Agent...")
    researcher = ResearcherAgent()
    print("✅ 研究员Agent初始化完成")
    print()

    # 用户查询示例
    user_queries = [
        "2024年人工智能在医疗领域的最新应用趋势",
        "量子计算对密码学的影响及未来发展方向",
        "气候变化对全球农业生产的长期影响评估"
    ]

    # 让用户选择查询或输入自定义查询
    print("请选择一个研究主题:")
    for i, query in enumerate(user_queries, 1):
        print(f"{i}. {query}")
    print("4. 自定义查询")
    print()

    choice = input("请输入选择 (1-4): ").strip()
    
    if choice == "4":
        user_query = input("请输入自定义研究查询: ").strip()
    elif choice in ["1", "2", "3"]:
        user_query = user_queries[int(choice)-1]
    else:
        print("无效选择，使用默认查询")
        user_query = user_queries[0]

    print()
    print(f"🔍 开始研究: {user_query}")
    print("=" * 80)
    print()

    try:
        # 运行完整研究工作流
        result: ResearchResult = await researcher.run_research_workflow(user_query)

        # 展示研究结果
        print("📊 研究结果")
        print("=" * 80)
        print()

        # 显示研究计划
        print("📋 研究计划:")
        print("目标:")
        for i, objective in enumerate(result.research_plan.objectives, 1):
            print(f"  {i}. {objective}")
        print()

        print("搜索查询:")
        for i, query in enumerate(result.research_plan.search_queries, 1):
            print(f"  {i}. {query}")
        print()

        # 显示分析总结
        print("📈 分析总结:")
        print(result.analysis_summary)
        print()

        # 显示最终结论
        print("🎯 最终结论:")
        print(result.final_conclusion)
        print()

        # 显示来源
        print("📚 引用来源:")
        for i, source in enumerate(result.sources, 1):
            print(f"  {i}. {source}")
        print()

        # 保存结果到文件
        filename = f"research_result_{user_query[:30].replace(' ', '_')}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"研究主题: {result.original_query}\n")
            f.write("=" * 80 + "\n")
            f.write("研究计划:\n")
            f.write("目标:\n")
            for i, objective in enumerate(result.research_plan.objectives, 1):
                f.write(f"  {i}. {objective}\n")
            f.write("\n搜索查询:\n")
            for i, query in enumerate(result.research_plan.search_queries, 1):
                f.write(f"  {i}. {query}\n")
            f.write("\n" + "=" * 80 + "\n")
            f.write("分析总结:\n")
            f.write(result.analysis_summary + "\n")
            f.write("\n" + "=" * 80 + "\n")
            f.write("最终结论:\n")
            f.write(result.final_conclusion + "\n")
            f.write("\n" + "=" * 80 + "\n")
            f.write("引用来源:\n")
            for i, source in enumerate(result.sources, 1):
                f.write(f"  {i}. {source}\n")

        print(f"💾 研究结果已保存到: {filename}")
        print()

    except Exception as e:
        print(f"❌ 研究过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()


async def demo_streaming_research():
    """演示流式研究过程"""
    print("=" * 80)
    print("🎓 研究员Agent流式演示")
    print("=" * 80)
    print()

    # 创建研究员Agent
    researcher = ResearcherAgent()

    # 用户查询
    user_query = "2024年人工智能在医疗领域的最新应用趋势"
    print(f"🔍 开始流式研究: {user_query}")
    print("=" * 80)
    print()

    try:
        # 流式执行研究
        async for event in researcher.research(user_query):
            if event.type == AgentEventType.LLM_DELTA:
                print(event.content, end="", flush=True)
            elif event.type == AgentEventType.TOOL_CALL:
                print(f"\n\n🔧 调用工具: {event.metadata['tool_name']}")
                print(f"   参数: {event.metadata['tool_args']}")
            elif event.type == AgentEventType.TOOL_RESULT:
                print(f"\n📊 工具结果:")
                print(event.content[:200] + "..." if len(event.content) > 200 else event.content)
            elif event.type == AgentEventType.AGENT_FINISH:
                print(f"\n\n✅ 研究完成:")
                print(event.content)
            elif event.type == AgentEventType.ERROR:
                print(f"\n❌ 错误: {event.error}")

    except Exception as e:
        print(f"❌ 流式研究过程中发生错误: {str(e)}")


async def demo_component_tests():
    """演示各个组件的功能测试"""
    print("=" * 80)
    print("🧪 研究员Agent组件测试")
    print("=" * 80)
    print()

    # 创建研究员Agent
    researcher = ResearcherAgent()

    # 测试1: 意图分析
    print("1. 测试意图分析:")
    user_query = "2024年人工智能在医疗领域的最新应用趋势"
    intent = await researcher.analyze_intent(user_query)
    print("意图分析结果:")
    print(intent)
    print()

    # 测试2: 创建研究计划
    print("2. 测试创建研究计划:")
    plan = await researcher.create_research_plan(intent)
    print("研究计划:")
    print(f"目标: {plan.objectives}")
    print(f"搜索查询: {plan.search_queries}")
    print()

    # 测试3: 执行单个搜索
    print("3. 测试单个搜索:")
    if plan.search_queries:
        search_result = await researcher.execute_search(plan.search_queries[0])
        print(f"搜索结果 ({plan.search_queries[0]}):")
        print(search_result[:300] + "..." if len(search_result) > 300 else search_result)
    print()

    print("✅ 组件测试完成")


async def main():
    """主函数"""
    print("🎓 研究员Agent演示程序")
    print("=" * 80)
    print()

    # 显示菜单
    print("请选择演示模式:")
    print("1. 完整研究工作流演示")
    print("2. 流式研究过程演示")
    print("3. 组件功能测试")
    print()

    choice = input("请输入选择 (1-3): ").strip()
    print()

    if choice == "1":
        await demo_research_workflow()
    elif choice == "2":
        await demo_streaming_research()
    elif choice == "3":
        await demo_component_tests()
    else:
        print("无效选择，退出程序")

    print()
    print("👋 演示结束")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⏹️ 程序被用户中断")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 程序运行错误: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
