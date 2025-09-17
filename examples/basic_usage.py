"""
Lexicon Agent Framework 基本使用示例

演示如何使用框架的各种功能
"""

import asyncio
import json
from lexicon_agent import LexiconAgent, create_agent, quick_chat


async def example_basic_chat():
    """基本聊天示例"""
    
    print("=== 基本聊天示例 ===")
    
    # 方式1: 快速聊天
    response = await quick_chat("你好，请介绍一下你自己")
    print(f"快速聊天响应: {response}")
    
    # 方式2: 使用上下文管理器
    async with LexiconAgent() as agent:
        response = await agent.simple_chat("请分析一下人工智能的发展趋势")
        print(f"简单聊天响应: {response}")


async def example_streaming_chat():
    """流式聊天示例"""
    
    print("\n=== 流式聊天示例 ===")
    
    async with LexiconAgent() as agent:
        print("用户: 请创建一个Python程序来计算斐波那契数列")
        print("助手: ", end="", flush=True)
        
        async for chunk in agent.process_message("请创建一个Python程序来计算斐波那契数列"):
            if chunk["type"] == "response_text":
                print(chunk["content"], end="", flush=True)
            elif chunk["type"] == "stage_event":
                print(f"\n[阶段: {chunk['content']['stage']} - {chunk['content']['status']}]")
            elif chunk["is_final"]:
                print("\n[响应完成]")


async def example_with_session_context():
    """带会话上下文的示例"""
    
    print("\n=== 会话上下文示例 ===")
    
    # 创建会话上下文
    session_context = {
        "user_id": "demo_user",
        "session_id": "demo_session_001", 
        "preferences": {
            "language": "chinese",
            "response_style": "detailed",
            "domain_expertise": ["programming", "ai"]
        },
        "conversation_history": [
            {"role": "user", "content": "我是一名Python开发者"},
            {"role": "assistant", "content": "很高兴认识您！我可以帮助您解决Python开发相关的问题。"}
        ]
    }
    
    async with LexiconAgent() as agent:
        response = await agent.simple_chat("基于我们之前的对话，推荐一些适合我的Python高级技巧")
        print(f"带上下文的响应: {response}")


async def example_tool_usage():
    """工具使用示例"""
    
    print("\n=== 工具使用示例 ===")
    
    async with LexiconAgent() as agent:
        # 获取可用工具列表
        tools = agent.tool_registry.list_tools()
        print(f"可用工具: {tools}")
        
        # 获取工具统计
        stats = agent.tool_registry.get_registry_statistics()
        print(f"工具统计: {json.dumps(stats, indent=2, ensure_ascii=False)}")
        
        # 模拟工具调用请求
        print("\n发送需要工具调用的请求...")
        async for chunk in agent.process_message("请列出当前目录下的文件，然后搜索相关的知识库信息"):
            if chunk["type"] == "tool_execution_start":
                print(f"开始执行工具: {chunk['content']['tool_name']}")
            elif chunk["type"] == "tool_execution_complete":
                print(f"工具执行完成: {chunk['content']['tool_name']}")


async def example_performance_monitoring():
    """性能监控示例"""
    
    print("\n=== 性能监控示例 ===")
    
    # 启用性能监控
    config = {"performance_monitoring": True, "log_level": "INFO"}
    
    async with LexiconAgent(config) as agent:
        # 发送多个请求来生成性能数据
        for i in range(3):
            response = await agent.simple_chat(f"这是第{i+1}个测试请求")
            print(f"请求 {i+1} 完成")
        
        # 获取性能报告
        report = agent.get_performance_report()
        print(f"性能报告: {json.dumps(report, indent=2, ensure_ascii=False, default=str)}")
        
        # 健康检查
        health = await agent.health_check()
        print(f"系统健康状态: {health['status']} (分数: {health['overall_health_score']:.2f})")


async def example_error_handling():
    """错误处理示例"""
    
    print("\n=== 错误处理示例 ===")
    
    async with LexiconAgent() as agent:
        # 测试空消息
        try:
            response = await agent.simple_chat("")
            print(f"空消息响应: {response}")
        except Exception as e:
            print(f"空消息错误: {e}")
        
        # 测试异常长的消息
        long_message = "测试" * 1000
        try:
            response = await agent.simple_chat(long_message)
            print(f"长消息响应长度: {len(response)}")
        except Exception as e:
            print(f"长消息错误: {e}")


async def example_advanced_configuration():
    """高级配置示例"""
    
    print("\n=== 高级配置示例 ===")
    
    # 自定义配置
    advanced_config = {
        "log_level": "DEBUG",
        "performance_monitoring": True,
        "context_engine": {
            "max_context_length": 8000,
            "compression_enabled": True
        },
        "tool_system": {
            "max_concurrent_tools": 3,
            "safety_mode": "strict"
        },
        "orchestration": {
            "default_strategy": "functional",
            "max_agents": 5
        }
    }
    
    agent = LexiconAgent(advanced_config)
    await agent.start()
    
    try:
        # 配置上下文引擎
        agent.configure_context_engine(advanced_config.get("context_engine", {}))
        
        # 获取框架状态
        status = agent.get_framework_status()
        print(f"框架状态: {json.dumps(status, indent=2, ensure_ascii=False, default=str)}")
        
        # 处理复杂请求
        response = await agent.simple_chat("请分析当前AI技术发展趋势，包括大语言模型、多模态AI和自动化编程等方向")
        print(f"复杂请求响应: {response[:200]}...")
        
    finally:
        await agent.stop()


async def example_concurrent_requests():
    """并发请求示例"""
    
    print("\n=== 并发请求示例 ===")
    
    async with LexiconAgent() as agent:
        
        # 定义不同类型的请求
        requests = [
            "请解释什么是机器学习",
            "编写一个排序算法的代码",
            "分析当前科技发展趋势",
            "推荐一些编程学习资源",
            "解释区块链技术原理"
        ]
        
        async def process_request(i, message):
            print(f"开始处理请求 {i+1}: {message[:30]}...")
            response = await agent.simple_chat(message)
            print(f"请求 {i+1} 完成，响应长度: {len(response)}")
            return response
        
        # 并发执行所有请求
        tasks = [process_request(i, msg) for i, msg in enumerate(requests)]
        responses = await asyncio.gather(*tasks)
        
        print(f"所有 {len(responses)} 个并发请求已完成")


async def example_framework_lifecycle():
    """框架生命周期示例"""
    
    print("\n=== 框架生命周期示例 ===")
    
    # 创建但不启动
    agent = LexiconAgent()
    print(f"框架已创建，初始化状态: {agent.is_initialized}")
    
    # 手动启动
    await agent.start()
    print(f"框架已启动，初始化状态: {agent.is_initialized}")
    print(f"启动时间: {agent.startup_time}")
    
    # 使用框架
    response = await agent.simple_chat("测试框架是否正常工作")
    print(f"测试响应: {response[:50]}...")
    
    # 获取运行时统计
    status = agent.get_framework_status()
    print(f"运行时长: {status['uptime_seconds']:.2f} 秒")
    print(f"处理请求数: {status['statistics']['total_requests']}")
    
    # 手动停止
    await agent.stop()
    print(f"框架已停止，初始化状态: {agent.is_initialized}")


async def main():
    """运行所有示例"""
    
    print("🤖 Lexicon Agent Framework 使用示例")
    print("=" * 50)
    
    try:
        await example_basic_chat()
        await example_streaming_chat()
        await example_with_session_context()
        await example_tool_usage()
        await example_performance_monitoring()
        await example_error_handling()
        await example_advanced_configuration()
        await example_concurrent_requests()
        await example_framework_lifecycle()
        
        print("\n🎉 所有示例运行完成！")
        
    except Exception as e:
        print(f"\n❌ 示例运行出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())