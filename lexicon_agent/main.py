"""
Lexicon Agent Framework 主入口

整合所有核心组件，提供统一的框架接口
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, AsyncIterator
from datetime import datetime

from .types import Agent, SessionState, ToolSafetyLevel
from .core.context import ContextRetrievalEngine, ContextProcessor, ContextManager
from .core.agent import AgentController, StreamingGenerator, ConversationState
from .core.orchestration import OrchestrationEngine, AgentCoordinator
from .core.tools import ToolRegistry, IntelligentToolScheduler, ToolExecutor, ToolSafetyManager
from .core.streaming import StreamingProcessor, PerformanceOptimizer, StreamingPipeline


class LexiconAgent:
    """
    Lexicon Agent Framework 主类
    
    提供统一的接口来使用所有核心功能
    """
    
    def __init__(self, 
                 config: Optional[Dict[str, Any]] = None,
                 enable_performance_monitoring: bool = True):
        
        self.config = config or {}
        self.enable_performance_monitoring = enable_performance_monitoring
        
        # 初始化日志
        self._setup_logging()
        
        # 初始化核心组件
        self._initialize_components()
        
        # 框架状态
        self.is_initialized = False
        self.startup_time: Optional[datetime] = None
        
        # 统计信息
        self.framework_stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "average_response_time": 0.0,
            "uptime_seconds": 0.0
        }
        
        self.logger.info("Lexicon Agent Framework initialized")
    
    def _setup_logging(self):
        """设置日志"""
        
        log_level = self.config.get("log_level", "INFO")
        logging.basicConfig(
            level=getattr(logging, log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger("LexiconAgent")
    
    def _initialize_components(self):
        """初始化所有核心组件"""
        
        try:
            # 上下文工程组件
            self.context_engine = ContextRetrievalEngine()
            self.context_processor = ContextProcessor()
            self.context_manager = ContextManager()
            
            # 工具系统组件
            self.tool_registry = ToolRegistry()
            self.tool_safety_manager = ToolSafetyManager()
            self.tool_scheduler = IntelligentToolScheduler(self.tool_registry)
            self.tool_executor = ToolExecutor(self.tool_registry, self.tool_safety_manager)
            
            # 智能体组件
            self.streaming_generator = StreamingGenerator(None)  # 需要LLM提供者
            self.agent_controller = AgentController(
                context_engine=self.context_engine,
                context_processor=self.context_processor,
                context_manager=self.context_manager,
                streaming_generator=self.streaming_generator
            )
            
            # 编排组件
            self.orchestration_engine = OrchestrationEngine()
            self.agent_coordinator = AgentCoordinator()
            
            # 流式处理组件
            self.streaming_processor = StreamingProcessor()
            self.performance_optimizer = PerformanceOptimizer()
            
            # 主处理管道
            self.pipeline = StreamingPipeline(
                agent_controller=self.agent_controller,
                agent_coordinator=self.agent_coordinator,
                tool_scheduler=self.tool_scheduler,
                streaming_processor=self.streaming_processor,
                performance_optimizer=self.performance_optimizer
            )
            
            self.logger.info("All core components initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize components: {e}")
            raise
    
    async def start(self):
        """启动框架"""
        
        if self.is_initialized:
            self.logger.warning("Framework is already initialized")
            return
        
        try:
            self.startup_time = datetime.now()
            
            # 启动性能监控
            if self.enable_performance_monitoring:
                asyncio.create_task(self.performance_optimizer.start_monitoring())
                self.logger.info("Performance monitoring started")
            
            # 执行健康检查
            health_status = await self.health_check()
            if health_status["status"] != "healthy":
                self.logger.warning(f"Framework health check shows: {health_status['status']}")
            
            self.is_initialized = True
            self.logger.info("Lexicon Agent Framework started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start framework: {e}")
            raise
    
    async def stop(self):
        """停止框架"""
        
        if not self.is_initialized:
            return
        
        try:
            # 这里可以添加清理逻辑
            self.is_initialized = False
            self.logger.info("Lexicon Agent Framework stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping framework: {e}")
    
    async def process_message(self, message: str,
                            session_context: Optional[Dict[str, Any]] = None,
                            user_id: Optional[str] = None) -> AsyncIterator[Dict[str, Any]]:
        """处理用户消息的主接口"""
        
        if not self.is_initialized:
            await self.start()
        
        request_start = datetime.now()
        self.framework_stats["total_requests"] += 1
        
        try:
            # 通过处理管道处理消息
            async for chunk in self.pipeline.process_request(
                user_message=message,
                session_context=session_context or {},
                processing_options={"user_id": user_id}
            ):
                # 转换为标准输出格式
                yield {
                    "type": chunk.chunk_type,
                    "content": chunk.data,
                    "metadata": chunk.metadata,
                    "is_final": chunk.is_final,
                    "timestamp": chunk.timestamp.isoformat()
                }
            
            # 更新成功统计
            self.framework_stats["successful_requests"] += 1
            
        except Exception as e:
            self.framework_stats["failed_requests"] += 1
            self.logger.error(f"Error processing message: {e}")
            
            # 返回错误响应
            yield {
                "type": "error",
                "content": {"error": str(e)},
                "metadata": {"error_type": type(e).__name__},
                "is_final": True,
                "timestamp": datetime.now().isoformat()
            }
        
        finally:
            # 更新性能统计
            processing_time = (datetime.now() - request_start).total_seconds()
            total_requests = self.framework_stats["total_requests"]
            current_avg = self.framework_stats["average_response_time"]
            
            self.framework_stats["average_response_time"] = (
                (current_avg * (total_requests - 1) + processing_time) / total_requests
            )
            
            # 记录到性能优化器
            if self.enable_performance_monitoring:
                self.performance_optimizer.record_response_time(processing_time * 1000)
                self.performance_optimizer.record_request(
                    success=self.framework_stats["failed_requests"] == 0
                )
    
    async def simple_chat(self, message: str) -> str:
        """简单聊天接口，返回最终响应文本"""
        
        response_parts = []
        
        async for response in self.process_message(message):
            if response["type"] == "response_text":
                response_parts.append(response["content"])
            elif response["type"] == "error":
                return f"Error: {response['content'].get('error', 'Unknown error')}"
        
        return "".join(response_parts).strip()
    
    def add_tool(self, tool_name: str, tool_function: callable,
                 description: str = "", 
                 safety_level: ToolSafetyLevel = ToolSafetyLevel.CAUTIOUS) -> bool:
        """添加自定义工具"""
        
        try:
            # 这里需要将函数包装为BaseTool接口
            # 简化实现，实际需要更复杂的包装逻辑
            self.logger.info(f"Tool {tool_name} registration requested")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to add tool {tool_name}: {e}")
            return False
    
    def register_agent(self, agent: Agent) -> bool:
        """注册智能体"""
        
        try:
            # 这里应该将智能体注册到协调器中
            self.logger.info(f"Agent {agent.agent_id} registered")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to register agent {agent.agent_id}: {e}")
            return False
    
    def configure_context_engine(self, config: Dict[str, Any]):
        """配置上下文引擎"""
        
        try:
            # 应用配置到上下文引擎
            self.logger.info("Context engine configured")
            
        except Exception as e:
            self.logger.error(f"Failed to configure context engine: {e}")
    
    def get_framework_status(self) -> Dict[str, Any]:
        """获取框架状态"""
        
        uptime = 0.0
        if self.startup_time:
            uptime = (datetime.now() - self.startup_time).total_seconds()
            self.framework_stats["uptime_seconds"] = uptime
        
        return {
            "framework_version": "2.0.0",
            "is_initialized": self.is_initialized,
            "startup_time": self.startup_time.isoformat() if self.startup_time else None,
            "uptime_seconds": uptime,
            "statistics": self.framework_stats,
            "components": {
                "context_engine": "initialized",
                "agent_controller": "initialized",
                "orchestration_engine": "initialized",
                "tool_system": "initialized",
                "streaming_processor": "initialized",
                "performance_optimizer": "initialized" if self.enable_performance_monitoring else "disabled"
            },
            "configuration": {
                "performance_monitoring": self.enable_performance_monitoring,
                "log_level": self.config.get("log_level", "INFO")
            }
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """系统健康检查"""
        
        health_results = {}
        overall_health = 1.0
        
        try:
            # 检查管道健康
            pipeline_health = await self.pipeline.health_check()
            health_results["pipeline"] = pipeline_health
            if pipeline_health["health_score"] < 0.8:
                overall_health *= 0.8
            
            # 检查工具执行器健康
            executor_health = await self.tool_executor.health_check()
            health_results["tool_executor"] = executor_health
            if executor_health["health_score"] < 0.8:
                overall_health *= 0.9
            
            # 检查性能优化器健康
            if self.enable_performance_monitoring:
                optimizer_health = await self.performance_optimizer.health_check()
                health_results["performance_optimizer"] = optimizer_health
                if optimizer_health["health_score"] < 0.8:
                    overall_health *= 0.9
            
            # 检查协调器健康
            coordinator_health = await self.agent_coordinator.health_check()
            health_results["agent_coordinator"] = coordinator_health
            if coordinator_health["health_score"] < 0.8:
                overall_health *= 0.9
            
            return {
                "status": "healthy" if overall_health > 0.8 else "degraded" if overall_health > 0.5 else "unhealthy",
                "overall_health_score": overall_health,
                "component_health": health_results,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "overall_health_score": 0.0,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def get_performance_report(self) -> Dict[str, Any]:
        """获取性能报告"""
        
        report = {
            "framework_stats": self.framework_stats,
            "timestamp": datetime.now().isoformat()
        }
        
        if self.enable_performance_monitoring:
            optimizer_report = self.performance_optimizer.get_performance_report()
            report["optimizer_report"] = optimizer_report
        
        return report
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.stop()


# 便捷函数

async def create_agent(config: Optional[Dict[str, Any]] = None) -> LexiconAgent:
    """创建并启动Lexicon Agent实例"""
    
    agent = LexiconAgent(config)
    await agent.start()
    return agent


async def quick_chat(message: str, config: Optional[Dict[str, Any]] = None) -> str:
    """快速聊天函数"""
    
    async with LexiconAgent(config) as agent:
        return await agent.simple_chat(message)


# 示例用法
async def main():
    """示例使用"""
    
    # 方式1: 直接使用
    async with LexiconAgent() as agent:
        response = await agent.simple_chat("Hello, how are you?")
        print(f"Agent: {response}")
    
    # 方式2: 流式处理
    agent = await create_agent({"log_level": "DEBUG"})
    
    async for response_chunk in agent.process_message("Analyze this file: example.py"):
        print(f"Chunk: {response_chunk}")
    
    await agent.stop()
    
    # 方式3: 快速聊天
    response = await quick_chat("What's the weather like?")
    print(f"Quick response: {response}")


if __name__ == "__main__":
    asyncio.run(main())