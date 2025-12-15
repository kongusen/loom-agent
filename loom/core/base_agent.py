"""
Agent 基类 - 递归状态机

核心理念：
- Agent = 递归函数 run(Message) -> Message
- 简单、优雅、强大
"""

from __future__ import annotations
from typing import Protocol, List, Optional
from loom.core.message import Message
from loom.interfaces.llm import BaseLLM
from loom.interfaces.tool import BaseTool


class BaseAgent(Protocol):
    """
    Agent 协议 - 递归状态机

    核心理念：
    Agent 就是一个递归函数，通过 run(Message) -> Message 的递归调用实现复杂行为。

    核心方法：
    - run(Message) -> Message

    工作流程：
    1. 接收 Message（包含完整上下文）
    2. LLM 推理决策
    3. 工具调用（如需要）
    4. 递归调用 run() - 关键！
    5. 返回最终 Message

    示例：
    ```python
    from loom.core.agent import BaseAgent
    from loom.core.message import Message

    agent: BaseAgent = loom.agent(name="assistant", llm="openai", api_key="...")

    # 递归调用
    message = Message(role="user", content="What's 2+2?")
    response = await agent.run(message)
    print(response.content)  # "2+2 equals 4"
    ```
    """

    name: str
    llm: BaseLLM
    tools: List[BaseTool]

    async def run(self, message: Message) -> Message:
        """
        核心递归方法

        Args:
            message: 输入消息（包含完整上下文）

        Returns:
            响应消息

        Raises:
            AgentError: Agent 执行错误
            RecursionError: 递归深度超限
        """
        ...

    async def reply(self, message: Message) -> Message:
        """
        便捷方法 - 直接回复（alias for run）

        Args:
            message: 输入消息

        Returns:
            响应消息
        """
        ...


# ============================================================================
# 工厂函数
# ============================================================================


def create_agent(
    name: str,
    llm: BaseLLM,
    tools: Optional[List[BaseTool]] = None,
    agent_type: str = "simple",
    **kwargs,
) -> BaseAgent:
    """
    创建 Agent 的工厂函数

    Args:
        name: Agent 名称
        llm: LLM 实例
        tools: 工具列表
        agent_type: Agent 类型
            - "simple": Agent（标准实现，基于递归状态机）
            - "react": Agent with react_mode=True（推理+行动模式）
            - "crew": CrewAgent（多智能体协调）
        **kwargs: 其他参数

    Returns:
        Agent 实例

    Raises:
        ValueError: 未知的 agent_type

    Examples:
        ```python
        # 创建简单 Agent
        agent = create_agent(
            name="assistant",
            llm=OpenAILLM(),
            tools=[calculator, search],
            agent_type="simple"
        )

        # 创建 ReAct Agent
        agent = create_agent(
            name="researcher",
            llm=OpenAILLM(),
            tools=[search, fetch],
            agent_type="react"
        )
        ```
    """
    # 动态导入（避免循环依赖）
    if agent_type == "simple":
        from loom.agents.agent import Agent

        return Agent(name=name, llm=llm, tools=tools, **kwargs)

    elif agent_type == "react":
        from loom.agents.agent import Agent

        # ReAct 模式：通过 react_mode=True 启用
        return Agent(name=name, llm=llm, tools=tools, react_mode=True, **kwargs)

    elif agent_type == "crew":
        # CrewAgent 需要更多参数，应该直接使用构造函数
        raise ValueError(
            "CrewAgent requires additional parameters. "
            "Please use CrewAgent constructor directly or use patterns.Crew."
        )

    else:
        raise ValueError(
            f"Unknown agent type: {agent_type}. "
            f"Available types: 'simple', 'react', 'crew'"
        )


# ============================================================================
# 向后兼容
# ============================================================================


def is_agent(obj) -> bool:
    """
    检查对象是否实现了 BaseAgent 协议

    Args:
        obj: 要检查的对象

    Returns:
        是否实现了 BaseAgent

    Examples:
        ```python
        from loom.core.agent import is_agent
        import loom

        agent = loom.agent(...)
        assert is_agent(agent)  # True
        ```
    """
    return isinstance(obj, BaseAgent)


def validate_agent(obj, name: str = "agent") -> None:
    """
    验证对象实现了 BaseAgent 协议，否则抛出异常

    Args:
        obj: 要验证的对象
        name: 参数名（用于错误消息）

    Raises:
        TypeError: 对象未实现 BaseAgent

    Examples:
        ```python
        from loom.core.agent import validate_agent

        def use_agent(agent):
            validate_agent(agent)  # 确保实现了协议
            return await agent.run(message)
        ```
    """
    if not isinstance(obj, BaseAgent):
        raise TypeError(
            f"{name} must implement BaseAgent protocol. "
            f"Got {type(obj).__name__} which is missing required methods. "
            f"Required: name, llm, tools attributes and run() method."
        )
