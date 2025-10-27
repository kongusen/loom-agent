#!/usr/bin/env python3
"""
Loom 框架 TT 递归功能改进演示

展示基于 Claude Code 设计模式的智能递归控制功能：
1. 智能工具结果分析
2. 任务类型识别
3. 动态递归指导生成
4. 错误处理和恢复
"""

import asyncio
from loom.core.agent_executor import AgentExecutor
from loom.core.turn_state import TurnState
from loom.core.execution_context import ExecutionContext
from loom.core.events import ToolResult
from loom.core.types import Message


def demonstrate_recursion_analysis():
    """演示递归分析功能"""
    print("🔍 演示智能递归分析功能")
    print("=" * 50)
    
    # 创建执行器实例
    executor = AgentExecutor(llm=None, tools={})
    
    # 测试不同类型的工具结果
    test_cases = [
        {
            "name": "SQL 数据检索结果",
            "results": [
                ToolResult(
                    tool_call_id="call_1",
                    tool_name="get_schema",
                    content="获取到表结构：users(id INT, name VARCHAR(100), email VARCHAR(255), created_at DATETIME)",
                    is_error=False
                )
            ]
        },
        {
            "name": "分析结果",
            "results": [
                ToolResult(
                    tool_call_id="call_1",
                    tool_name="analyze_code",
                    content="代码分析完成，发现3个问题：缺少类型注解、函数过长、缺少错误处理",
                    is_error=False
                )
            ]
        },
        {
            "name": "错误结果",
            "results": [
                ToolResult(
                    tool_call_id="call_1",
                    tool_name="read_file",
                    content="错误：文件不存在或无法访问",
                    is_error=True
                )
            ]
        },
        {
            "name": "完成建议结果",
            "results": [
                ToolResult(
                    tool_call_id="call_1",
                    tool_name="generate_code",
                    content="代码生成完成，已创建完整的实现",
                    is_error=False
                )
            ]
        }
    ]
    
    for case in test_cases:
        print(f"\n📋 {case['name']}:")
        analysis = executor._analyze_tool_results(case['results'])
        print(f"   - 有数据: {analysis['has_data']}")
        print(f"   - 有错误: {analysis['has_errors']}")
        print(f"   - 建议完成: {analysis['suggests_completion']}")
        print(f"   - 结果类型: {analysis['result_types']}")
        print(f"   - 完整性评分: {analysis['completeness_score']:.1%}")


def demonstrate_task_extraction():
    """演示任务提取功能"""
    print("\n🎯 演示任务提取功能")
    print("=" * 50)
    
    executor = AgentExecutor(llm=None, tools={})
    
    test_messages = [
        [
            Message(role="user", content="生成用户统计的 SQL 查询"),
            Message(role="assistant", content="我需要获取表结构"),
            Message(role="user", content="工具调用已完成，请生成 SQL")
        ],
        [
            Message(role="user", content="分析 main.py 的代码质量"),
            Message(role="assistant", content="我先读取文件内容"),
            Message(role="user", content="继续处理任务：分析 main.py 的代码质量")
        ],
        [
            Message(role="user", content="创建一个 REST API"),
            Message(role="assistant", content="我需要了解需求"),
            Message(role="user", content="工具执行遇到问题，请重新尝试")
        ]
    ]
    
    for i, messages in enumerate(test_messages, 1):
        original_task = executor._extract_original_task(messages)
        print(f"📝 测试案例 {i}: {original_task}")


def demonstrate_guidance_generation():
    """演示指导生成功能"""
    print("\n💡 演示智能指导生成功能")
    print("=" * 50)
    
    executor = AgentExecutor(llm=None, tools={})
    
    # 测试不同任务类型的指导生成
    test_scenarios = [
        {
            "task": "生成用户统计的 SQL 查询",
            "analysis": {"has_data": True, "has_errors": False, "suggests_completion": False, "completeness_score": 0.6},
            "depth": 2
        },
        {
            "task": "分析代码质量",
            "analysis": {"has_data": False, "has_errors": False, "suggests_completion": True, "completeness_score": 0.8},
            "depth": 3
        },
        {
            "task": "创建 REST API",
            "analysis": {"has_data": False, "has_errors": True, "suggests_completion": False, "completeness_score": 0.2},
            "depth": 1
        },
        {
            "task": "生成报告",
            "analysis": {"has_data": True, "has_errors": False, "suggests_completion": False, "completeness_score": 0.4},
            "depth": 6
        }
    ]
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n📋 场景 {i}: {scenario['task']}")
        guidance = executor._generate_recursion_guidance(
            scenario['task'],
            scenario['analysis'],
            scenario['depth']
        )
        print(f"💬 生成的指导:")
        print(f"   {guidance}")


def demonstrate_improvements():
    """演示改进效果"""
    print("\n🚀 改进效果对比")
    print("=" * 50)
    
    print("❌ 改进前的问题:")
    print("   - 硬编码的递归消息：'工具调用已完成。请基于工具返回的结果生成最终的 SQL 查询。不要继续调用工具，直接生成 SQL！'")
    print("   - 缺乏任务上下文感知")
    print("   - 无法根据工具结果调整策略")
    print("   - 没有错误处理机制")
    print("   - 递归深度控制简单")
    
    print("\n✅ 改进后的优势:")
    print("   - 智能分析工具结果类型和质量")
    print("   - 根据任务类型生成个性化指导")
    print("   - 动态调整递归策略")
    print("   - 完善的错误处理和恢复机制")
    print("   - 基于完成度的智能决策")
    print("   - 保持原始任务上下文")
    
    print("\n🎯 核心改进点:")
    print("   1. 智能工具结果分析 - 识别数据类型、错误、完成建议")
    print("   2. 任务类型识别 - SQL、分析、生成等不同处理策略")
    print("   3. 动态递归指导 - 基于进度和结果生成合适消息")
    print("   4. 错误处理机制 - 检测错误并提供重试建议")
    print("   5. 完成度评估 - 基于工具结果计算任务完成度")
    print("   6. 上下文保持 - 始终记住原始任务目标")


def main():
    """主演示函数"""
    print("🎉 Loom 框架 TT 递归功能改进演示")
    print("=" * 60)
    print("基于 Claude Code 设计模式的智能递归控制")
    print("=" * 60)
    
    try:
        # 演示各个功能模块
        demonstrate_recursion_analysis()
        demonstrate_task_extraction()
        demonstrate_guidance_generation()
        demonstrate_improvements()
        
        print("\n🎊 演示完成！")
        print("=" * 60)
        print("✨ 改进后的 TT 递归功能具备以下能力：")
        print("   🔍 智能分析工具结果")
        print("   🎯 任务类型识别")
        print("   💡 动态指导生成")
        print("   🛡️ 错误处理机制")
        print("   📊 完成度评估")
        print("   🔄 上下文保持")
        
    except Exception as e:
        print(f"❌ 演示失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
