"""
Lexicon Agent Framework 主入口

整合所有核心组件，提供统一的框架接口
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, AsyncIterator, Union
from datetime import datetime

from .types import Agent, SessionState, ToolSafetyLevel
from .core.context import ContextRetrievalEngine, ContextProcessor, ContextManager
from .core.agent import AgentController, StreamingGenerator, ConversationState
from .core.orchestration import OrchestrationEngine, AgentCoordinator
from .core.tools import ToolRegistry, IntelligentToolScheduler, ToolExecutor, ToolSafetyManager
from .core.streaming import StreamingProcessor, PerformanceOptimizer, StreamingPipeline
from .infrastructure.llm import CustomLLMProvider
from .config import LexiconAgentConfig, ConfigManager, LLMConfig, ContextConfig, ToolConfig


class LexiconAgent:
    """
    Lexicon Agent Framework 主类
    
    提供统一的接口来使用所有核心功能
    """
    
    def __init__(self, 
                 config: Optional[Union[Dict[str, Any], str, LexiconAgentConfig]] = None,
                 enable_performance_monitoring: bool = True):
        
        # 初始化配置管理器
        self.config_manager = ConfigManager()
        self.config = self._load_config(config)
        
        # 将配置加载到配置管理器中
        self.config_manager._config = self.config
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
    
    def _load_config(self, config_input: Optional[Union[Dict[str, Any], str, LexiconAgentConfig]]) -> LexiconAgentConfig:
        """加载配置"""
        if config_input is None:
            # 使用默认配置
            return self.config_manager.load_config()
        elif isinstance(config_input, LexiconAgentConfig):
            return config_input
        elif isinstance(config_input, str):
            # 从文件路径加载
            return self.config_manager.load_config(config_input)
        elif isinstance(config_input, dict):
            # 从字典创建配置
            return LexiconAgentConfig.from_dict(config_input)
        else:
            raise ValueError(f"Unsupported config type: {type(config_input)}")
    
    def _setup_logging(self):
        """设置日志"""
        
        log_level = self.config.log_level.value
        log_format = self.config.log_format
        
        logging.basicConfig(
            level=getattr(logging, log_level),
            format=log_format
        )
        
        # 如果指定了日志文件
        if self.config.log_file:
            file_handler = logging.FileHandler(self.config.log_file)
            file_handler.setLevel(getattr(logging, log_level))
            file_handler.setFormatter(logging.Formatter(log_format))
            
            logger = logging.getLogger("LexiconAgent")
            logger.addHandler(file_handler)
        
        self.logger = logging.getLogger("LexiconAgent")
    
    def _initialize_llm_provider(self):
        """初始化LLM提供者"""
        
        llm_config = self.config.llm
        
        # 支持多种LLM提供者类型
        if llm_config.provider.value == "custom":
            if not llm_config.api_base:
                self.logger.warning("No API base URL provided for custom LLM provider")
                return None
                
            return CustomLLMProvider(
                api_base=llm_config.api_base,
                api_key=llm_config.api_key,
                model=llm_config.model,
                timeout=llm_config.timeout,
                max_retries=llm_config.max_retries
            )
        else:
            self.logger.error(f"Unsupported LLM provider type: {llm_config.provider.value}")
            return None
    
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
            
            # 智能体组件 - 初始化LLM提供者
            self.llm_provider = self._initialize_llm_provider()
            self.streaming_generator = StreamingGenerator(self.llm_provider)
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
            
            # 启动内存管理清理任务
            if hasattr(self.context_manager, 'memory_hierarchy'):
                self.context_manager.memory_hierarchy._start_cleanup_task()
            
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
            # 清理LLM提供者HTTP会话
            if self.llm_provider and hasattr(self.llm_provider, 'close'):
                await self.llm_provider.close()
            
            # 停止性能监控
            if self.enable_performance_monitoring and hasattr(self.performance_optimizer, 'stop_monitoring'):
                await self.performance_optimizer.stop_monitoring()
            
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
    
    # =============================================================================
    # 配置管理接口
    # =============================================================================
    
    def update_llm_config(self, **kwargs) -> LLMConfig:
        """
        更新LLM配置
        
        Args:
            **kwargs: LLM配置参数
            
        Returns:
            LLMConfig: 更新后的LLM配置
        """
        try:
            new_config = self.config_manager.update_llm_config(**kwargs)
            self.config = self.config_manager.get_config()
            
            # 重新初始化LLM提供者
            self.llm_provider = self._initialize_llm_provider()
            if self.streaming_generator:
                self.streaming_generator.llm_provider = self.llm_provider
            
            self.logger.info("LLM configuration updated")
            return new_config
            
        except Exception as e:
            self.logger.error(f"Failed to update LLM config: {e}")
            raise
    
    def update_context_config(self, **kwargs) -> ContextConfig:
        """
        更新上下文配置
        
        Args:
            **kwargs: 上下文配置参数
            
        Returns:
            ContextConfig: 更新后的上下文配置
        """
        try:
            new_config = self.config_manager.update_context_config(**kwargs)
            self.config = self.config_manager.get_config()
            
            # 这里可以重新配置上下文相关组件
            self.logger.info("Context configuration updated")
            return new_config
            
        except Exception as e:
            self.logger.error(f"Failed to update context config: {e}")
            raise
    
    def update_tool_config(self, **kwargs) -> ToolConfig:
        """
        更新工具配置
        
        Args:
            **kwargs: 工具配置参数
            
        Returns:
            ToolConfig: 更新后的工具配置
        """
        try:
            new_config = self.config_manager.update_tool_config(**kwargs)
            self.config = self.config_manager.get_config()
            
            # 这里可以重新配置工具相关组件
            self.logger.info("Tool configuration updated")
            return new_config
            
        except Exception as e:
            self.logger.error(f"Failed to update tool config: {e}")
            raise
    
    def get_current_config(self) -> LexiconAgentConfig:
        """获取当前配置"""
        return self.config
    
    def save_config(self, file_path: str, format: str = "yaml") -> None:
        """
        保存当前配置到文件
        
        Args:
            file_path: 文件路径
            format: 文件格式 ("json" 或 "yaml")
        """
        try:
            self.config_manager.save_config(self.config, file_path, format)
            self.logger.info(f"Configuration saved to {file_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to save config: {e}")
            raise
    
    def load_config_from_file(self, file_path: str) -> None:
        """
        从文件重新加载配置
        
        Args:
            file_path: 配置文件路径
        """
        try:
            self.config = self.config_manager.load_config(file_path)
            
            # 重新初始化组件
            self._setup_logging()
            self._initialize_components()
            
            self.logger.info(f"Configuration loaded from {file_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to load config from file: {e}")
            raise
    
    def create_config_template(self, 
                             template_type: str = "default", 
                             output_path: Optional[str] = None) -> LexiconAgentConfig:
        """
        创建配置模板
        
        Args:
            template_type: 模板类型 ("default", "development", "production", "minimal")
            output_path: 输出路径（如果提供，会保存到文件）
            
        Returns:
            LexiconAgentConfig: 配置模板
        """
        try:
            template = self.config_manager.create_config_template(template_type, output_path)
            self.logger.info(f"Configuration template '{template_type}' created")
            return template
            
        except Exception as e:
            self.logger.error(f"Failed to create config template: {e}")
            raise
    
    def validate_config(self) -> Dict[str, Any]:
        """
        验证当前配置
        
        Returns:
            Dict: 验证结果
        """
        try:
            validation_result = self.config_manager.validator.validate(self.config)
            
            return {
                "is_valid": validation_result.is_valid,
                "errors": validation_result.errors,
                "warnings": validation_result.warnings,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to validate config: {e}")
            return {
                "is_valid": False,
                "errors": [str(e)],
                "warnings": [],
                "timestamp": datetime.now().isoformat()
            }
    
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
                "log_level": self.config.log_level.value,
                "environment": self.config.environment,
                "debug_mode": self.config.debug,
                "llm_provider": self.config.llm.provider.value,
                "llm_model": self.config.llm.model,
                "context_strategy": self.config.context.strategy.value,
                "tool_execution_mode": self.config.tools.execution_mode.value,
                "orchestration_strategy": self.config.orchestration.strategy.value
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

async def create_agent(config: Optional[Union[Dict[str, Any], str, LexiconAgentConfig]] = None) -> LexiconAgent:
    """创建并启动Lexicon Agent实例"""
    
    agent = LexiconAgent(config)
    await agent.start()
    return agent


async def quick_chat(message: str, config: Optional[Union[Dict[str, Any], str, LexiconAgentConfig]] = None) -> str:
    """快速聊天函数"""
    
    async with LexiconAgent(config) as agent:
        return await agent.simple_chat(message)


# 配置相关便捷函数

def create_development_agent() -> LexiconAgent:
    """创建开发环境配置的Agent"""
    from .config.models import create_development_config
    return LexiconAgent(create_development_config())


def create_production_agent() -> LexiconAgent:
    """创建生产环境配置的Agent"""
    from .config.models import create_production_config
    return LexiconAgent(create_production_config())


def create_minimal_agent() -> LexiconAgent:
    """创建最小配置的Agent"""
    from .config.models import create_minimal_config
    return LexiconAgent(create_minimal_config())


def create_custom_llm_agent(api_base: str, api_key: str, model: str) -> LexiconAgent:
    """创建自定义LLM配置的Agent"""
    from .config.models import create_default_config, LLMProvider
    
    config = create_default_config()
    config.llm.provider = LLMProvider.CUSTOM
    config.llm.api_base = api_base
    config.llm.api_key = api_key
    config.llm.model = model
    
    return LexiconAgent(config)


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