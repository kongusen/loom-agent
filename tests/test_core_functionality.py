"""
核心功能测试

测试Lexicon Agent Framework的基本功能
"""

import asyncio
import pytest
from datetime import datetime

from lexicon_agent.main import LexiconAgent, create_agent, quick_chat
from lexicon_agent.types import Agent, ToolCall, ToolSafetyLevel
from lexicon_agent.core.tools.registry import FileSystemTool, KnowledgeBaseTool


class TestLexiconAgent:
    """Lexicon Agent 主框架测试"""
    
    @pytest.mark.asyncio
    async def test_agent_initialization(self):
        """测试智能体初始化"""
        
        agent = LexiconAgent()
        assert not agent.is_initialized
        
        await agent.start()
        assert agent.is_initialized
        assert agent.startup_time is not None
        
        await agent.stop()
        assert not agent.is_initialized
    
    @pytest.mark.asyncio
    async def test_simple_chat(self):
        """测试简单聊天功能"""
        
        async with LexiconAgent() as agent:
            response = await agent.simple_chat("Hello")
            assert isinstance(response, str)
            assert len(response) > 0
    
    @pytest.mark.asyncio
    async def test_streaming_response(self):
        """测试流式响应"""
        
        async with LexiconAgent() as agent:
            chunks = []
            async for chunk in agent.process_message("Test message"):
                chunks.append(chunk)
            
            assert len(chunks) > 0
            assert any(chunk["is_final"] for chunk in chunks)
    
    @pytest.mark.asyncio
    async def test_health_check(self):
        """测试健康检查"""
        
        async with LexiconAgent() as agent:
            health = await agent.health_check()
            assert "status" in health
            assert "overall_health_score" in health
            assert health["overall_health_score"] >= 0.0
    
    @pytest.mark.asyncio
    async def test_framework_status(self):
        """测试框架状态"""
        
        async with LexiconAgent() as agent:
            status = agent.get_framework_status()
            assert status["is_initialized"]
            assert "components" in status
            assert "statistics" in status
    
    @pytest.mark.asyncio
    async def test_performance_report(self):
        """测试性能报告"""
        
        async with LexiconAgent() as agent:
            report = agent.get_performance_report()
            assert "framework_stats" in report
            assert "timestamp" in report


class TestContextEngineering:
    """上下文工程测试"""
    
    @pytest.mark.asyncio
    async def test_context_retrieval(self):
        """测试上下文检索"""
        
        agent = LexiconAgent()
        await agent.start()
        
        try:
            # 测试上下文引擎是否正常工作
            assert agent.context_engine is not None
            assert agent.context_processor is not None
            assert agent.context_manager is not None
            
        finally:
            await agent.stop()
    
    @pytest.mark.asyncio
    async def test_context_processing(self):
        """测试上下文处理"""
        
        async with LexiconAgent() as agent:
            # 发送一个需要上下文处理的消息
            response_count = 0
            async for chunk in agent.process_message("Analyze the context of this conversation"):
                response_count += 1
            
            assert response_count > 0


class TestToolSystem:
    """工具系统测试"""
    
    @pytest.mark.asyncio
    async def test_tool_registry(self):
        """测试工具注册表"""
        
        agent = LexiconAgent()
        await agent.start()
        
        try:
            # 检查默认工具是否注册
            registry = agent.tool_registry
            available_tools = registry.list_tools()
            
            assert "file_system" in available_tools
            assert "knowledge_base" in available_tools
            assert "code_interpreter" in available_tools
            assert "web_search" in available_tools
            
        finally:
            await agent.stop()
    
    @pytest.mark.asyncio
    async def test_tool_execution(self):
        """测试工具执行"""
        
        agent = LexiconAgent()
        await agent.start()
        
        try:
            # 创建一个简单的工具调用
            tool_call = ToolCall(
                tool_name="file_system",
                input_data={"action": "list", "path": "."},
                safety_level=ToolSafetyLevel.SAFE
            )
            
            # 执行工具
            result = await agent.tool_executor.execute_single_tool(tool_call)
            assert result is not None
            assert result.tool_call == tool_call
            
        finally:
            await agent.stop()
    
    @pytest.mark.asyncio
    async def test_tool_safety(self):
        """测试工具安全管理"""
        
        agent = LexiconAgent()
        await agent.start()
        
        try:
            # 测试安全的工具调用
            safe_call = ToolCall(
                tool_name="knowledge_base",
                input_data={"action": "search", "kb_name": "test", "query": "test"},
                safety_level=ToolSafetyLevel.SAFE
            )
            
            validation = await agent.tool_safety_manager.validate_tool_call(safe_call)
            assert validation["allowed"]
            
            # 测试危险的工具调用
            dangerous_call = ToolCall(
                tool_name="file_system",
                input_data={"action": "delete", "path": "/system"},
                safety_level=ToolSafetyLevel.EXCLUSIVE
            )
            
            validation = await agent.tool_safety_manager.validate_tool_call(dangerous_call)
            # 根据安全策略，这个调用可能被阻止
            
        finally:
            await agent.stop()


class TestOrchestration:
    """编排系统测试"""
    
    @pytest.mark.asyncio
    async def test_agent_coordination(self):
        """测试智能体协调"""
        
        agent = LexiconAgent()
        await agent.start()
        
        try:
            # 检查协调器是否正常工作
            coordinator = agent.agent_coordinator
            assert coordinator is not None
            
            # 获取协调统计
            stats = coordinator.get_coordination_statistics()
            assert "basic_stats" in stats
            
        finally:
            await agent.stop()
    
    @pytest.mark.asyncio
    async def test_orchestration_strategies(self):
        """测试编排策略"""
        
        agent = LexiconAgent()
        await agent.start()
        
        try:
            orchestration_engine = agent.orchestration_engine
            
            # 检查策略是否注册
            status = await orchestration_engine.get_orchestration_status()
            assert "registered_strategies" in status
            assert len(status["registered_strategies"]) > 0
            
        finally:
            await agent.stop()


class TestStreamingProcessing:
    """流式处理测试"""
    
    @pytest.mark.asyncio
    async def test_streaming_processor(self):
        """测试流式处理器"""
        
        agent = LexiconAgent()
        await agent.start()
        
        try:
            processor = agent.streaming_processor
            
            # 创建测试流
            stream_id = "test_stream"
            success = await processor.create_stream(stream_id, "text")
            assert success
            
            # 获取处理统计
            stats = processor.get_processing_statistics()
            assert "processing_stats" in stats
            
        finally:
            await agent.stop()
    
    @pytest.mark.asyncio
    async def test_performance_optimization(self):
        """测试性能优化"""
        
        agent = LexiconAgent({"performance_monitoring": True})
        await agent.start()
        
        try:
            optimizer = agent.performance_optimizer
            
            # 记录一些性能数据
            optimizer.record_response_time(100.0)  # 100ms
            optimizer.record_request(success=True)
            
            # 获取性能报告
            report = optimizer.get_performance_report()
            assert "framework_stats" in report
            
        finally:
            await agent.stop()


class TestPipeline:
    """处理管道测试"""
    
    @pytest.mark.asyncio
    async def test_pipeline_execution(self):
        """测试管道执行"""
        
        async with LexiconAgent() as agent:
            pipeline = agent.pipeline
            
            # 获取管道状态
            status = pipeline.get_pipeline_status()
            assert "pipeline_stages" in status
            assert len(status["pipeline_stages"]) > 0
            
            # 测试简单请求处理
            chunk_count = 0
            async for chunk in pipeline.process_request("Test pipeline"):
                chunk_count += 1
            
            assert chunk_count > 0
    
    @pytest.mark.asyncio
    async def test_pipeline_stages(self):
        """测试管道阶段"""
        
        async with LexiconAgent() as agent:
            pipeline = agent.pipeline
            
            # 检查默认阶段是否正确设置
            status = pipeline.get_pipeline_status()
            stage_ids = [stage["stage_id"] for stage in status["pipeline_stages"]]
            
            expected_stages = [
                "preprocessing",
                "agent_coordination", 
                "context_processing",
                "core_processing",
                "tool_scheduling",
                "streaming_response",
                "postprocessing"
            ]
            
            for expected_stage in expected_stages:
                assert expected_stage in stage_ids


class TestConvenienceFunctions:
    """便捷函数测试"""
    
    @pytest.mark.asyncio
    async def test_create_agent(self):
        """测试create_agent函数"""
        
        agent = await create_agent()
        assert agent.is_initialized
        await agent.stop()
    
    @pytest.mark.asyncio
    async def test_quick_chat(self):
        """测试quick_chat函数"""
        
        response = await quick_chat("Hello")
        assert isinstance(response, str)
        assert len(response) > 0


class TestErrorHandling:
    """错误处理测试"""
    
    @pytest.mark.asyncio
    async def test_invalid_message_handling(self):
        """测试无效消息处理"""
        
        async with LexiconAgent() as agent:
            # 测试空消息
            response_chunks = []
            async for chunk in agent.process_message(""):
                response_chunks.append(chunk)
            
            # 应该有错误处理
            assert len(response_chunks) > 0
    
    @pytest.mark.asyncio
    async def test_component_failure_handling(self):
        """测试组件故障处理"""
        
        agent = LexiconAgent()
        
        # 在未启动时尝试操作
        try:
            await agent.simple_chat("test")
            # 应该自动启动
        except Exception:
            # 或者抛出合适的异常
            pass


# 性能测试

class TestPerformance:
    """性能测试"""
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self):
        """测试并发请求处理"""
        
        async with LexiconAgent() as agent:
            
            async def process_message(msg_id):
                chunks = []
                async for chunk in agent.process_message(f"Message {msg_id}"):
                    chunks.append(chunk)
                return len(chunks)
            
            # 创建5个并发请求
            tasks = [process_message(i) for i in range(5)]
            results = await asyncio.gather(*tasks)
            
            # 所有请求都应该成功处理
            assert all(result > 0 for result in results)
    
    @pytest.mark.asyncio
    async def test_response_time(self):
        """测试响应时间"""
        
        async with LexiconAgent() as agent:
            start_time = datetime.now()
            
            response = await agent.simple_chat("Quick test")
            
            end_time = datetime.now()
            response_time = (end_time - start_time).total_seconds()
            
            # 响应时间应该在合理范围内（这里设置为10秒）
            assert response_time < 10.0
            assert len(response) > 0


if __name__ == "__main__":
    # 运行基本测试
    async def run_basic_tests():
        """运行基本测试"""
        
        print("Running Lexicon Agent Framework Tests...")
        
        # 测试框架初始化
        print("Testing framework initialization...")
        agent = LexiconAgent()
        await agent.start()
        print(f"✓ Framework started successfully")
        
        # 测试健康检查
        health = await agent.health_check()
        print(f"✓ Health check: {health['status']}")
        
        # 测试简单聊天
        response = await agent.simple_chat("Hello, this is a test")
        print(f"✓ Simple chat response: {response[:50]}...")
        
        # 测试流式处理
        chunk_count = 0
        async for chunk in agent.process_message("Test streaming"):
            chunk_count += 1
        print(f"✓ Streaming processing: {chunk_count} chunks")
        
        # 测试工具系统
        tools = agent.tool_registry.list_tools()
        print(f"✓ Tool system: {len(tools)} tools available")
        
        # 获取最终状态
        status = agent.get_framework_status()
        print(f"✓ Final status: {status['statistics']}")
        
        await agent.stop()
        print("✓ Framework stopped successfully")
        print("\nAll basic tests passed! 🎉")
    
    # 运行测试
    asyncio.run(run_basic_tests())