"""Loom 0.0.3 开发者 API - 简化统一协调使用

提供开发者友好的 API 接口，让开发者能够轻松使用 Loom 0.0.3 的核心能力。
"""

import asyncio
import time
from typing import List, Optional, Dict, Any, AsyncGenerator, Union
from ..core.agent_executor import AgentExecutor
from ..core.unified_coordination import (
    UnifiedExecutionContext,
    IntelligentCoordinator,
    CoordinationConfig
)
from ..core.events import AgentEvent, AgentEventType
from ..core.turn_state import TurnState
from ..core.execution_context import ExecutionContext
from ..core.types import Message
from ..interfaces.llm import BaseLLM
from ..interfaces.tool import BaseTool


class LoomAgent:
    """Loom 0.0.3 统一协调 Agent
    
    提供简化的 API 接口，让开发者能够轻松使用统一协调机制。
    """
    
    def __init__(
        self,
        llm: BaseLLM,
        tools: Optional[Dict[str, BaseTool]] = None,
        config: Optional[CoordinationConfig] = None,
        execution_id: Optional[str] = None,
        max_iterations: int = 50,
        system_instructions: Optional[str] = None,
        **kwargs
    ):
        """初始化 Loom 0.0.3 Agent
        
        Args:
            llm: 语言模型实例
            tools: 工具字典
            config: 统一协调配置
            execution_id: 执行 ID
            max_iterations: 最大迭代次数
            system_instructions: 系统指令
            **kwargs: 其他参数
        """
        self.config = config or CoordinationConfig()
        self.unified_context = UnifiedExecutionContext(
            execution_id=execution_id or f"loom_agent_{int(time.time())}",
            config=self.config
        )
        
        self.executor = AgentExecutor(
            llm=llm,
            tools=tools or {},
            unified_context=self.unified_context,
            enable_unified_coordination=True,
            max_iterations=max_iterations,
            system_instructions=system_instructions,
            **kwargs
        )
    
    async def run(self, input_text: str, correlation_id: Optional[str] = None) -> str:
        """运行 Agent 并返回最终结果
        
        Args:
            input_text: 用户输入
            correlation_id: 关联 ID
            
        Returns:
            最终响应文本
        """
        turn_state = TurnState.initial(max_iterations=self.executor.max_iterations)
        context = ExecutionContext.create(
            correlation_id=correlation_id or f"run_{int(time.time())}"
        )
        messages = [Message(role="user", content=input_text)]
        
        final_content = ""
        async for event in self.executor.tt(messages, turn_state, context):
            if event.type == AgentEventType.AGENT_FINISH:
                final_content = event.content or ""
                break
            elif event.type == AgentEventType.ERROR:
                raise event.error
        
        return final_content
    
    async def stream(self, input_text: str, correlation_id: Optional[str] = None) -> AsyncGenerator[AgentEvent, None]:
        """流式执行 Agent
        
        Args:
            input_text: 用户输入
            correlation_id: 关联 ID
            
        Yields:
            AgentEvent: 执行事件
        """
        turn_state = TurnState.initial(max_iterations=self.executor.max_iterations)
        context = ExecutionContext.create(
            correlation_id=correlation_id or f"stream_{int(time.time())}"
        )
        messages = [Message(role="user", content=input_text)]
        
        async for event in self.executor.tt(messages, turn_state, context):
            yield event
    
    async def execute_with_events(self, input_text: str, correlation_id: Optional[str] = None) -> List[AgentEvent]:
        """执行并返回所有事件
        
        Args:
            input_text: 用户输入
            correlation_id: 关联 ID
            
        Returns:
            事件列表
        """
        events = []
        async for event in self.stream(input_text, correlation_id):
            events.append(event)
        return events
    
    async def run_with_progress(self, input_text: str, progress_callback=None) -> str:
        """带进度回调的执行
        
        Args:
            input_text: 用户输入
            progress_callback: 进度回调函数
            
        Returns:
            最终响应文本
        """
        final_content = ""
        
        async for event in self.stream(input_text):
            if progress_callback:
                await progress_callback(event)
            
            if event.type == AgentEventType.AGENT_FINISH:
                final_content = event.content or ""
                break
            elif event.type == AgentEventType.ERROR:
                raise event.error
        
        return final_content
    
    def get_coordinator(self) -> IntelligentCoordinator:
        """获取智能协调器实例"""
        return self.executor.coordinator
    
    def get_unified_context(self) -> UnifiedExecutionContext:
        """获取统一执行上下文"""
        return self.unified_context


def create_loom_agent(
    llm: BaseLLM,
    tools: Optional[Dict[str, BaseTool]] = None,
    config: Optional[CoordinationConfig] = None,
    **kwargs
) -> LoomAgent:
    """创建 Loom 0.0.3 Agent
    
    Args:
        llm: 语言模型实例
        tools: 工具字典
        config: 统一协调配置
        **kwargs: 其他参数
        
    Returns:
        LoomAgent 实例
    """
    return LoomAgent(llm=llm, tools=tools, config=config, **kwargs)


def create_unified_executor(
    llm: BaseLLM,
    tools: Optional[Dict[str, BaseTool]] = None,
    config: Optional[CoordinationConfig] = None,
    execution_id: Optional[str] = None,
    **kwargs
) -> AgentExecutor:
    """创建使用统一协调机制的 AgentExecutor
    
    Args:
        llm: 语言模型实例
        tools: 工具字典
        config: 统一协调配置
        execution_id: 执行 ID
        **kwargs: 其他参数
        
    Returns:
        AgentExecutor 实例
    """
    if config is None:
        config = CoordinationConfig()
    
    unified_context = UnifiedExecutionContext(
        execution_id=execution_id or f"executor_{int(time.time())}",
        config=config
    )
    
    return AgentExecutor(
        llm=llm,
        tools=tools or {},
        unified_context=unified_context,
        enable_unified_coordination=True,
        **kwargs
    )


# 便捷函数
def loom_agent(
    llm: BaseLLM,
    tools: Optional[Dict[str, BaseTool]] = None,
    config: Optional[CoordinationConfig] = None,
    **kwargs
) -> LoomAgent:
    """创建 Loom 0.0.3 统一协调 Agent
    
    这是最推荐的创建方式，提供简化的 API 和完整的功能。
    
    Args:
        llm: 语言模型实例
        tools: 工具字典
        config: 统一协调配置
        **kwargs: 其他参数
        
    Returns:
        LoomAgent 实例
        
    Example:
        ```python
        import loom
        from loom.builtin.llms import MockLLM
        
        agent = loom.loom_agent(
            llm=MockLLM(),
            tools={"calculator": CalculatorTool()}
        )
        
        result = await agent.run("计算 2+2")
        print(result)
        ```
    """
    return create_loom_agent(llm=llm, tools=tools, config=config, **kwargs)


def unified_executor(
    llm: BaseLLM,
    tools: Optional[Dict[str, BaseTool]] = None,
    config: Optional[CoordinationConfig] = None,
    **kwargs
) -> AgentExecutor:
    """创建统一协调 AgentExecutor
    
    适用于需要直接控制执行流程的高级用户。
    
    Args:
        llm: 语言模型实例
        tools: 工具字典
        config: 统一协调配置
        **kwargs: 其他参数
        
    Returns:
        AgentExecutor 实例
        
    Example:
        ```python
        import loom
        from loom.builtin.llms import MockLLM
        
        executor = loom.unified_executor(
            llm=MockLLM(),
            tools={"calculator": CalculatorTool()}
        )
        
        turn_state = loom.TurnState.initial(max_iterations=10)
        context = loom.ExecutionContext.create()
        messages = [loom.Message(role="user", content="Hello")]
        
        async for event in executor.tt(messages, turn_state, context):
            print(f"Event: {event.type} - {event.content}")
        ```
    """
    return create_unified_executor(llm=llm, tools=tools, config=config, **kwargs)


# 导出所有 API
__all__ = [
    "LoomAgent",
    "create_loom_agent", 
    "create_unified_executor",
    "loom_agent",
    "unified_executor",
]
