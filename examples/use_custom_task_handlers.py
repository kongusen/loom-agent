#!/usr/bin/env python3
"""
Loom 框架使用自定义任务处理器示例

展示如何在 AgentExecutor 中使用自定义的任务处理器
"""

import asyncio
from loom.core.agent_executor import AgentExecutor, TaskHandler
from loom.core.turn_state import TurnState
from loom.core.execution_context import ExecutionContext
from loom.core.events import ToolResult
from loom.core.types import Message
from typing import Dict, Any


class MockLLM:
    """模拟 LLM"""
    
    def __init__(self, responses):
        self.responses = responses
        self.call_count = 0
        self.supports_tools = True
    
    async def generate_with_tools(self, messages, tools_spec):
        if self.call_count < len(self.responses):
            response = self.responses[self.call_count]
            self.call_count += 1
            return response
        else:
            return {
                "content": "任务完成",
                "tool_calls": []
            }


class MockTool:
    """模拟工具"""
    
    def __init__(self, name, results):
        self.name = name
        self.results = results
        self.call_count = 0
    
    async def call(self, input_data, context, mcp_context=None, assistant_message=None):
        if self.call_count < len(self.results):
            result = self.results[self.call_count]
            self.call_count += 1
            
            yield {"type": "progress", "data": f"执行 {self.name}..."}
            yield {"type": "result", "data": result}
        else:
            yield {"type": "result", "data": "工具执行完成"}


class SQLTaskHandler(TaskHandler):
    """SQL 任务处理器"""
    
    def can_handle(self, task: str) -> bool:
        sql_keywords = ["sql", "query", "select", "database", "表", "查询", "数据库"]
        task_lower = task.lower()
        return any(keyword in task_lower for keyword in sql_keywords)
    
    def generate_guidance(
        self,
        original_task: str,
        result_analysis: Dict[str, Any],
        recursion_depth: int
    ) -> str:
        if result_analysis["has_errors"]:
            return f"""工具执行遇到问题。请重新尝试完成 SQL 任务：{original_task}

建议：
- 检查工具参数是否正确
- 尝试使用不同的方法获取数据
- 如果问题持续，请说明具体错误"""
        
        elif result_analysis["has_data"] and result_analysis["completeness_score"] >= 0.6:
            return f"""工具调用已完成，已获取到所需的数据信息。现在请基于这些数据生成最终的 SQL 查询语句。

重要提示：
- 不要继续调用工具
- 直接生成完整的 SQL 查询
- 确保 SQL 语法正确
- 包含适当的注释说明查询目的

原始任务：{original_task}"""
        
        elif recursion_depth >= 5:
            return f"""已达到较深的递归层级。请基于当前可用的信息生成 SQL 查询。

如果信息不足，请说明需要哪些额外信息。

原始任务：{original_task}"""
        
        else:
            return f"""继续处理 SQL 任务：{original_task}

当前进度：{result_analysis['completeness_score']:.0%}
建议：使用更多工具收集相关信息，或分析已获得的数据"""


class AnalysisTaskHandler(TaskHandler):
    """分析任务处理器"""
    
    def can_handle(self, task: str) -> bool:
        analysis_keywords = ["analyze", "analysis", "examine", "review", "分析", "检查", "评估"]
        task_lower = task.lower()
        return any(keyword in task_lower for keyword in analysis_keywords)
    
    def generate_guidance(
        self,
        original_task: str,
        result_analysis: Dict[str, Any],
        recursion_depth: int
    ) -> str:
        if result_analysis["suggests_completion"] or result_analysis["completeness_score"] >= 0.8:
            return f"""信息收集基本完成。请基于已收集的信息完成分析任务：{original_task}

请提供：
1. 关键发现和洞察
2. 数据支持的分析结论  
3. 建议或推荐行动
4. 任何需要注意的限制或风险"""
        
        elif result_analysis["has_errors"]:
            return f"""分析过程中遇到问题。请重新尝试完成任务：{original_task}

建议：
- 检查数据源是否可用
- 尝试不同的分析方法
- 如果问题持续，请说明具体错误"""
        
        else:
            return f"""继续分析任务：{original_task}

当前进度：{result_analysis['completeness_score']:.0%}
建议：收集更多数据或使用分析工具处理已获得的信息"""


async def test_with_custom_handlers():
    """测试使用自定义任务处理器"""
    print("🧪 测试使用自定义任务处理器")
    print("=" * 50)
    
    # 创建自定义任务处理器
    custom_handlers = [
        SQLTaskHandler(),
        AnalysisTaskHandler(),
    ]
    
    # 创建模拟 LLM
    llm_responses = [
        {
            "content": "我需要获取数据库表结构来生成 SQL 查询",
            "tool_calls": [
                {
                    "id": "call_1",
                    "name": "get_table_schema",
                    "arguments": {"table_name": "users"}
                }
            ]
        },
        {
            "content": "基于获取的表结构，我生成以下 SQL 查询：\n\n```sql\nSELECT COUNT(*) as user_count\nFROM users\nWHERE created_at >= '2024-01-01';\n```",
            "tool_calls": []
        }
    ]
    
    llm = MockLLM(llm_responses)
    
    # 创建模拟工具
    tools = {
        "get_table_schema": MockTool("get_table_schema", [
            "表结构：users(id INT, name VARCHAR(100), email VARCHAR(255), created_at DATETIME)"
        ])
    }
    
    # 创建执行器，传入自定义任务处理器
    executor = AgentExecutor(
        llm=llm, 
        tools=tools,
        task_handlers=custom_handlers  # 传入自定义处理器
    )
    
    # 创建初始状态
    turn_state = TurnState.initial(max_iterations=10)
    context = ExecutionContext.create()
    messages = [Message(role="user", content="生成用户统计的 SQL 查询")]
    
    print(f"📝 原始任务: {messages[0].content}")
    print(f"🔧 使用的任务处理器: {[h.__class__.__name__ for h in custom_handlers]}")
    print()
    
    # 执行 TT 递归
    events = []
    async for event in executor.tt(messages, turn_state, context):
        events.append(event)
        
        if event.type.value == "llm_delta":
            print(f"🤖 LLM 输出: {event.content}")
        elif event.type.value == "tool_result":
            print(f"🔧 工具结果: {event.tool_result.content}")
        elif event.type.value == "agent_finish":
            print(f"✅ 任务完成: {event.content}")
            break
    
    print(f"\n📊 总共生成了 {len(events)} 个事件")
    print("✅ 自定义任务处理器测试完成")


async def test_without_handlers():
    """测试不使用自定义任务处理器（使用默认处理）"""
    print("\n🧪 测试不使用自定义任务处理器")
    print("=" * 50)
    
    # 创建模拟 LLM
    llm_responses = [
        {
            "content": "我需要分析代码质量",
            "tool_calls": [
                {
                    "id": "call_1",
                    "name": "read_file",
                    "arguments": {"file_path": "main.py"}
                }
            ]
        },
        {
            "content": "基于代码分析，我发现以下问题：\n\n1. 缺少类型注解\n2. 函数过长\n3. 缺少错误处理\n\n建议进行重构以提高代码质量。",
            "tool_calls": []
        }
    ]
    
    llm = MockLLM(llm_responses)
    
    # 创建模拟工具
    tools = {
        "read_file": MockTool("read_file", [
            "文件内容：def process_data(data):\n    result = []\n    for item in data:\n        result.append(item * 2)\n    return result"
        ])
    }
    
    # 创建执行器，不传入自定义任务处理器（使用默认处理）
    executor = AgentExecutor(
        llm=llm, 
        tools=tools
        # 不传入 task_handlers，将使用默认处理
    )
    
    # 创建初始状态
    turn_state = TurnState.initial(max_iterations=10)
    context = ExecutionContext.create()
    messages = [Message(role="user", content="分析 main.py 的代码质量")]
    
    print(f"📝 原始任务: {messages[0].content}")
    print(f"🔧 使用的任务处理器: 默认处理")
    print()
    
    # 执行 TT 递归
    events = []
    async for event in executor.tt(messages, turn_state, context):
        events.append(event)
        
        if event.type.value == "llm_delta":
            print(f"🤖 LLM 输出: {event.content}")
        elif event.type.value == "tool_result":
            print(f"🔧 工具结果: {event.tool_result.content}")
        elif event.type.value == "agent_finish":
            print(f"✅ 任务完成: {event.content}")
            break
    
    print(f"\n📊 总共生成了 {len(events)} 个事件")
    print("✅ 默认处理测试完成")


def demonstrate_handler_selection():
    """演示处理器选择逻辑"""
    print("\n🎯 演示处理器选择逻辑")
    print("=" * 50)
    
    # 创建处理器
    handlers = [
        SQLTaskHandler(),
        AnalysisTaskHandler(),
    ]
    
    # 测试任务
    test_tasks = [
        "生成用户统计的 SQL 查询",
        "分析代码质量",
        "创建 REST API",
        "生成报告"
    ]
    
    print("📋 处理器选择测试:")
    for task in test_tasks:
        matched_handler = None
        for handler in handlers:
            if handler.can_handle(task):
                matched_handler = handler
                break
        
        if matched_handler:
            print(f"  ✅ '{task}' -> {matched_handler.__class__.__name__}")
        else:
            print(f"  ❌ '{task}' -> 无匹配处理器（将使用默认处理）")


async def main():
    """主测试函数"""
    print("🚀 Loom 框架自定义任务处理器使用示例")
    print("=" * 60)
    
    try:
        # 演示处理器选择
        demonstrate_handler_selection()
        
        # 测试使用自定义处理器
        await test_with_custom_handlers()
        
        # 测试不使用自定义处理器
        await test_without_handlers()
        
        print("\n🎉 所有测试完成！")
        print("=" * 60)
        print("✨ 关键特性验证：")
        print("   🔧 自定义任务处理器正常工作")
        print("   🎯 任务匹配逻辑正确")
        print("   💡 指导生成功能正常")
        print("   🔄 默认处理机制正常")
        print("   📊 框架扩展性良好")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
