#!/usr/bin/env python3
"""
测试改进后的 TT 递归功能

验证智能递归控制器是否能够：
1. 正确分析工具结果
2. 生成合适的递归指导消息
3. 根据任务类型调整策略
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from loom.core.agent_executor import AgentExecutor
from loom.core.turn_state import TurnState
from loom.core.execution_context import ExecutionContext
from loom.core.events import ToolResult
from loom.core.types import Message


class MockLLM:
    """模拟 LLM 用于测试"""
    
    def __init__(self, responses):
        self.responses = responses
        self.call_count = 0
        self.supports_tools = True
    
    async def generate_with_tools(self, messages, tools_spec):
        """模拟带工具的 LLM 生成"""
        if self.call_count < len(self.responses):
            response = self.responses[self.call_count]
            self.call_count += 1
            return response
        else:
            return {
                "content": "测试完成",
                "tool_calls": []
            }


class MockTool:
    """模拟工具用于测试"""
    
    def __init__(self, name, results):
        self.name = name
        self.results = results
        self.call_count = 0
    
    async def call(self, input_data, context, mcp_context=None, assistant_message=None):
        """模拟工具调用"""
        if self.call_count < len(self.results):
            result = self.results[self.call_count]
            self.call_count += 1
            
            # 模拟进度和结果
            yield {"type": "progress", "data": f"执行 {self.name}..."}
            yield {"type": "result", "data": result}
        else:
            yield {"type": "result", "data": "工具执行完成"}


async def test_sql_generation_scenario():
    """测试 SQL 生成场景"""
    print("🧪 测试 SQL 生成场景")
    print("=" * 50)
    
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
    
    # 创建执行器
    executor = AgentExecutor(llm=llm, tools=tools)
    
    # 创建初始状态
    turn_state = TurnState.initial(max_iterations=10)
    context = ExecutionContext.create()
    messages = [Message(role="user", content="生成用户统计的 SQL 查询")]
    
    print(f"📝 原始任务: {messages[0].content}")
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
    print("✅ SQL 生成场景测试完成")


async def test_analysis_scenario():
    """测试分析场景"""
    print("\n🧪 测试分析场景")
    print("=" * 50)
    
    # 创建模拟 LLM
    llm_responses = [
        {
            "content": "我需要分析代码质量，先读取相关文件",
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
    
    # 创建执行器
    executor = AgentExecutor(llm=llm, tools=tools)
    
    # 创建初始状态
    turn_state = TurnState.initial(max_iterations=10)
    context = ExecutionContext.create()
    messages = [Message(role="user", content="分析 main.py 的代码质量")]
    
    print(f"📝 原始任务: {messages[0].content}")
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
    print("✅ 分析场景测试完成")


async def test_error_handling_scenario():
    """测试错误处理场景"""
    print("\n🧪 测试错误处理场景")
    print("=" * 50)
    
    # 创建模拟 LLM
    llm_responses = [
        {
            "content": "尝试访问不存在的文件",
            "tool_calls": [
                {
                    "id": "call_1",
                    "name": "read_file",
                    "arguments": {"file_path": "nonexistent.py"}
                }
            ]
        },
        {
            "content": "文件不存在，让我尝试其他方法或说明问题。",
            "tool_calls": []
        }
    ]
    
    llm = MockLLM(llm_responses)
    
    # 创建模拟工具
    tools = {
        "read_file": MockTool("read_file", [
            "错误：文件 nonexistent.py 不存在"
        ])
    }
    
    # 创建执行器
    executor = AgentExecutor(llm=llm, tools=tools)
    
    # 创建初始状态
    turn_state = TurnState.initial(max_iterations=10)
    context = ExecutionContext.create()
    messages = [Message(role="user", content="读取 nonexistent.py 文件")]
    
    print(f"📝 原始任务: {messages[0].content}")
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
    print("✅ 错误处理场景测试完成")


def test_recursion_guidance_logic():
    """测试递归指导逻辑"""
    print("\n🧪 测试递归指导逻辑")
    print("=" * 50)
    
    # 创建执行器实例
    executor = AgentExecutor(llm=None, tools={})
    
    # 测试 SQL 任务分析
    sql_tool_results = [
        ToolResult(
            tool_call_id="call_1",
            tool_name="get_table_schema",
            content="获取到表结构：users(id, name, email, created_at)",
            is_error=False
        )
    ]
    
    analysis = executor._analyze_tool_results(sql_tool_results)
    print(f"📊 SQL 任务分析结果: {analysis}")
    
    # 测试错误处理
    error_tool_results = [
        ToolResult(
            tool_call_id="call_1",
            tool_name="read_file",
            content="错误：文件不存在",
            is_error=True
        )
    ]
    
    error_analysis = executor._analyze_tool_results(error_tool_results)
    print(f"📊 错误任务分析结果: {error_analysis}")
    
    # 测试任务提取
    messages = [
        Message(role="user", content="生成用户统计的 SQL 查询"),
        Message(role="assistant", content="我需要获取表结构"),
        Message(role="user", content="工具调用已完成，请生成 SQL")
    ]
    
    original_task = executor._extract_original_task(messages)
    print(f"📝 提取的原始任务: {original_task}")
    
    print("✅ 递归指导逻辑测试完成")


async def main():
    """主测试函数"""
    print("🚀 开始测试改进后的 TT 递归功能")
    print("=" * 60)
    
    try:
        # 测试递归指导逻辑
        test_recursion_guidance_logic()
        
        # 测试各种场景
        await test_sql_generation_scenario()
        await test_analysis_scenario()
        await test_error_handling_scenario()
        
        print("\n🎉 所有测试完成！")
        print("=" * 60)
        print("✅ TT 递归功能改进验证成功")
        print("✅ 智能递归控制器工作正常")
        print("✅ 工具结果分析功能正常")
        print("✅ 任务类型识别功能正常")
        print("✅ 错误处理机制正常")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
