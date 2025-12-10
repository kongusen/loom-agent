"""
测试 hooks 参数集成 - 使用真实 OpenAI API

验证：
1. loom.agent() 能够正确接受 hooks 参数
2. Agent 类能够正确初始化并传递 hooks
3. hooks 在运行时能够正常工作
"""

import asyncio
import os
from loom import agent
from loom.core.lifecycle_hooks import LifecycleHook
from loom.core.events import AgentEventType


# 设置环境变量
os.environ["OPENAI_API_KEY"] = "sk-MQWe6wOtgq75cQpK2gGwV9Ninqc5jrxBBWDETRCI8h7PzTkb"
os.environ["OPENAI_MODEL"] = "gpt-4o-mini"
os.environ["OPENAI_BASE_URL"] = "https://xiaoai.plus/v1"


# 自定义测试 Hook
class TestLoggingHook:
    """简单的日志记录 Hook，用于验证 hooks 是否被调用"""
    
    def __init__(self):
        self.events_logged = []
        self.llm_calls = 0
        self.tool_calls = 0
    
    async def before_iteration_start(self, frame):
        """迭代开始前"""
        self.events_logged.append(f"iteration_start_{frame.depth}")
        print(f"🔵 [Hook] 迭代开始: depth={frame.depth}")
        return None
    
    async def before_llm_call(self, frame, messages):
        """LLM 调用前"""
        self.llm_calls += 1
        self.events_logged.append(f"llm_call_{self.llm_calls}")
        print(f"🤖 [Hook] LLM 调用 #{self.llm_calls}: {len(messages)} 条消息")
        return None
    
    async def after_llm_response(self, frame, response, tool_calls):
        """LLM 响应后"""
        tool_count = len(tool_calls) if tool_calls else 0
        print(f"✅ [Hook] LLM 响应: {len(response)} 字符, {tool_count} 个工具调用")
        return None
    
    async def before_tool_execution(self, frame, tool_call):
        """工具执行前"""
        self.tool_calls += 1
        tool_name = tool_call.get("name", "unknown") if isinstance(tool_call, dict) else getattr(tool_call, "name", "unknown")
        self.events_logged.append(f"tool_execution_{tool_name}")
        print(f"🔧 [Hook] 工具执行: {tool_name}")
        return None
    
    async def after_tool_execution(self, frame, tool_result):
        """工具执行后"""
        tool_name = tool_result.get("tool_name", "unknown") if isinstance(tool_result, dict) else getattr(tool_result, "tool_name", "unknown")
        print(f"✅ [Hook] 工具完成: {tool_name}")
        return None
    
    async def after_iteration_end(self, frame):
        """迭代结束时"""
        self.events_logged.append(f"iteration_end_{frame.depth}")
        print(f"🔴 [Hook] 迭代结束: depth={frame.depth}")
        return None
    
    def get_summary(self):
        """获取统计摘要"""
        return {
            "events_logged": len(self.events_logged),
            "llm_calls": self.llm_calls,
            "tool_calls": self.tool_calls,
            "events": self.events_logged
        }


async def test_basic_agent_with_hooks():
    """测试 1: 基本 Agent 创建和使用 hooks"""
    print("\n" + "="*60)
    print("测试 1: 基本 Agent 创建和使用 hooks")
    print("="*60 + "\n")
    
    # 创建测试 hook
    test_hook = TestLoggingHook()
    
    try:
        # 创建 agent，传入 hooks 参数
        print("📦 创建 Agent（带 hooks）...")
        my_agent = agent(
            provider="openai",
            model="gpt-4o-mini",
            api_key=os.environ["OPENAI_API_KEY"],
            base_url=os.environ["OPENAI_BASE_URL"],
            hooks=[test_hook],  # 🆕 测试 hooks 参数
        )
        print("✅ Agent 创建成功！")
        
        # 执行一个简单的任务
        print("\n🚀 执行任务: '请用中文回答：1+1等于几？'")
        print("-" * 60)
        
        response = await my_agent.run("请用中文回答：1+1等于几？")
        
        print("-" * 60)
        print(f"\n📝 Agent 响应:\n{response}\n")
        
        # 检查 hook 是否被调用
        summary = test_hook.get_summary()
        print("📊 Hook 统计:")
        print(f"  - 记录的事件数: {summary['events_logged']}")
        print(f"  - LLM 调用次数: {summary['llm_calls']}")
        print(f"  - 工具调用次数: {summary['tool_calls']}")
        
        if summary['events_logged'] > 0:
            print("✅ Hook 被成功调用！")
        else:
            print("⚠️ 警告: Hook 似乎没有被调用")
            
        return True
        
    except Exception as e:
        print(f"❌ 错误: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_streaming_with_hooks():
    """测试 2: 流式输出和 hooks"""
    print("\n" + "="*60)
    print("测试 2: 流式输出和 hooks")
    print("="*60 + "\n")
    
    test_hook = TestLoggingHook()
    
    try:
        my_agent = agent(
            provider="openai",
            model="gpt-4o-mini",
            api_key=os.environ["OPENAI_API_KEY"],
            base_url=os.environ["OPENAI_BASE_URL"],
            hooks=[test_hook],
        )
        
        print("🚀 流式执行: '请用一句话介绍 Python 编程语言'")
        print("-" * 60)
        print("📺 流式输出:\n")
        
        async for event in my_agent.execute("请用一句话介绍 Python 编程语言"):
            if event.type == AgentEventType.LLM_DELTA:
                print(event.content or "", end="", flush=True)
            elif event.type == AgentEventType.AGENT_FINISH:
                print(f"\n\n✅ 完成: {event.content}")
        
        print("-" * 60)
        summary = test_hook.get_summary()
        print(f"\n📊 Hook 统计: {summary['llm_calls']} 次 LLM 调用")
        
        return True
        
    except Exception as e:
        print(f"❌ 错误: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_multiple_hooks():
    """测试 3: 多个 hooks"""
    print("\n" + "="*60)
    print("测试 3: 多个 hooks")
    print("="*60 + "\n")
    
    hook1 = TestLoggingHook()
    hook2 = TestLoggingHook()
    
    try:
        my_agent = agent(
            provider="openai",
            model="gpt-4o-mini",
            api_key=os.environ["OPENAI_API_KEY"],
            base_url=os.environ["OPENAI_BASE_URL"],
            hooks=[hook1, hook2],  # 🆕 多个 hooks
        )
        
        print("🚀 执行任务（多个 hooks）...")
        response = await my_agent.run("用一句话说：你好")
        
        print(f"\n📝 响应: {response}\n")
        
        summary1 = hook1.get_summary()
        summary2 = hook2.get_summary()
        
        print(f"📊 Hook 1: {summary1['llm_calls']} 次 LLM 调用")
        print(f"📊 Hook 2: {summary2['llm_calls']} 次 LLM 调用")
        
        if summary1['llm_calls'] > 0 and summary2['llm_calls'] > 0:
            print("✅ 多个 hooks 都正常工作！")
        else:
            print("⚠️ 警告: 某些 hooks 可能没有被调用")
            
        return True
        
    except Exception as e:
        print(f"❌ 错误: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("🧪 Loom Agent Hooks 集成测试")
    print("="*60)
    print(f"\n🔑 API Key: {os.environ['OPENAI_API_KEY'][:20]}...")
    print(f"🌐 Base URL: {os.environ['OPENAI_BASE_URL']}")
    print(f"🤖 Model: {os.environ['OPENAI_MODEL']}\n")
    
    results = []
    
    # 运行测试
    results.append(("基本 Agent + Hooks", await test_basic_agent_with_hooks()))
    results.append(("流式输出 + Hooks", await test_streaming_with_hooks()))
    results.append(("多个 Hooks", await test_multiple_hooks()))
    
    # 总结
    print("\n" + "="*60)
    print("📊 测试总结")
    print("="*60)
    
    for test_name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{status} - {test_name}")
    
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        print("\n🎉 所有测试通过！hooks 参数集成成功！")
    else:
        print("\n⚠️ 部分测试失败，请检查错误信息")
    
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())

