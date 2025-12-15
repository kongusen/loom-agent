"""
Agent - Loom Agent 标准实现

基于递归状态机的核心 Agent 实现
"""

from __future__ import annotations
from typing import List, Optional, Union, Dict, Any

from loom.core.message import Message
from loom.core.executor import AgentExecutor
from loom.core.context import ContextManager
from loom.interfaces.llm import BaseLLM
from loom.interfaces.tool import BaseTool
from loom.skills import SkillManager


class Agent:
    """
    Agent - Loom Agent 标准实现

    核心特性：
    - 纯递归调用
    - 自动工具调用
    - Context 自动管理
    - 简单易用
    - 支持极简 LLM 配置

    用途：
    - 单一职责的 Agent
    - 简单的对话
    - 作为 Crew 的成员
    - 快速原型开发

    示例：
    ```python
    # 方式 1：工厂函数（推荐）
    import loom
    agent = loom.agent(
        name="assistant",
        llm="deepseek",         # 提供商名称
        api_key="sk-...",       # API 密钥
        model="deepseek-chat"   # 可选
    )

    # 方式 2：直接使用类
    from loom import Agent
    agent = Agent(
        name="assistant",
        llm="deepseek",
        api_key="sk-..."
    )

    # 方式 3：字典配置
    agent = loom.agent(
        name="assistant",
        llm={
            "provider": "qwen",
            "api_key": "sk-...",
            "model": "qwen-turbo",
            "temperature": 0.7
        }
    )

    # 方式 4：传入 LLM 实例
    from loom.builtin import UnifiedLLM
    llm = UnifiedLLM(provider="openai", api_key="sk-...")
    agent = loom.agent(name="assistant", llm=llm)

    # 添加工具
    from loom import tool

    @tool(name="calculator")
    async def calculator(expression: str) -> float:
        return eval(expression)

    agent = loom.agent(
        name="assistant",
        llm="openai",
        api_key="sk-...",
        tools=[calculator]
    )

    # 使用
    from loom import Message
    message = Message(role="user", content="What's 2+2?")
    response = await agent.run(message)
    print(response.content)
    ```
    """

    def __init__(
        self,
        name: str,
        llm: Union[str, Dict[str, Any], BaseLLM],
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        tools: Optional[List[BaseTool]] = None,
        system_prompt: Optional[str] = None,
        context_manager: Optional[ContextManager] = None,
        max_recursion_depth: int = 20,
        skills_dir: Optional[str] = None,
        enable_skills: bool = True,
        react_mode: bool = False,  # 新增：ReAct 模式开关
        **llm_kwargs: Any,
    ):
        """
        初始化 Agent

        Args:
            name: Agent 名称
            llm: LLM 配置，支持三种方式：
                - 字符串：提供商名称（如 "openai", "deepseek", "qwen", "custom"）
                - 字典：详细配置 {"provider": "openai", "api_key": "...", ...}
                - BaseLLM 实例：直接使用
            api_key: API 密钥（当 llm 是字符串时必需）
            model: 模型名称（可选，使用默认模型）
            base_url: API 基础 URL（可选，用于自定义服务或代理）
            tools: 工具列表
            system_prompt: 系统提示词（可选）
            context_manager: Context 管理器（可选）
            max_recursion_depth: 最大递归深度
            skills_dir: 技能目录路径（可选，默认 ./skills）
            enable_skills: 是否启用技能系统
            react_mode: 是否启用 ReAct 模式（推理-行动循环）
            **llm_kwargs: 其他 LLM 参数（temperature, max_tokens 等）

        Example::

            # 标准模式
            import loom
            agent = loom.agent(
                name="assistant",
                llm="deepseek",
                api_key="sk-..."
            )

            # ReAct 模式（适合需要多步推理的任务）
            agent = loom.agent(
                name="researcher",
                llm="openai",
                api_key="sk-...",
                tools=[search_tool, calculator],
                react_mode=True  # 启用 ReAct 推理模式
            )

            # 极简配置
            import loom
            agent = loom.agent(
                name="assistant",
                llm="deepseek",
                api_key="sk-..."
            )

            # 使用代理或自定义服务
            agent = loom.agent(
                name="assistant",
                llm="openai",
                api_key="sk-...",
                base_url="https://your-proxy.com/v1"
            )

            # 使用自定义 OpenAI 兼容服务
            agent = loom.agent(
                name="assistant",
                llm="custom",
                api_key="your-key",
                base_url="https://your-service.com/v1",
                model="your-model"
            )

            # 详细配置
            agent = loom.agent(
                name="assistant",
                llm="qwen",
                api_key="sk-...",
                model="qwen-turbo",
                temperature=0.7,
                max_tokens=2000
            )

            # 字典配置
            agent = loom.agent(
                name="assistant",
                llm={
                    "provider": "openai",
                    "api_key": "sk-...",
                    "model": "gpt-4",
                    "base_url": "https://proxy.com/v1",  # 可选
                    "temperature": 0.7
                }
            )

            # LLM 实例
            from loom.builtin import UnifiedLLM
            llm = UnifiedLLM(provider="openai", api_key="sk-...")
            agent = loom.agent(name="assistant", llm=llm)
        """
        self.name = name
        self.react_mode = react_mode  # 保存 ReAct 模式状态

        # 处理 llm 参数
        if isinstance(llm, str):
            # 字符串配置：提供商名称
            if not api_key:
                raise ValueError(
                    f"使用字符串配置 LLM 时需要提供 api_key。\n"
                    f"示例: agent(name='{name}', llm='{llm}', api_key='sk-...')"
                )

            from loom.builtin.llms import UnifiedLLM

            llm = UnifiedLLM(
                provider=llm,
                api_key=api_key,
                model=model,
                base_url=base_url,  # 支持自定义 base_url
                **llm_kwargs
            )

        elif isinstance(llm, dict):
            # 字典配置：详细参数
            provider = llm.pop("provider", "openai")
            from loom.builtin.llms import UnifiedLLM

            llm = UnifiedLLM(provider=provider, **llm)

        # 否则假设是 BaseLLM 实例，直接使用

        self.llm = llm
        self.tools = tools or []

        # Skills 系统
        self.enable_skills = enable_skills
        self.skill_manager = None
        if enable_skills:
            skills_path = skills_dir or "./skills"
            try:
                self.skill_manager = SkillManager(skills_path)
                self.skill_manager.load_all()
                print(f"[{name}] Skills enabled: {self.skill_manager.get_stats()}")
            except Exception as e:
                print(f"[{name}] Failed to load skills: {e}")
                self.enable_skills = False

        # 生成系统提示（包含工具使用启发式 + Skills）
        if system_prompt is None:
            system_prompt = self._generate_default_system_prompt()

        self.system_prompt = system_prompt

        # 创建执行引擎
        self.executor = AgentExecutor(
            agent_name=name,
            llm=llm,
            tools=self.tools,
            context_manager=context_manager or ContextManager(),
            max_recursion_depth=max_recursion_depth,
            system_prompt=self.system_prompt,
        )

    def _generate_default_system_prompt(self) -> str:
        """生成包含工具启发式和技能的默认系统提示"""

        # ReAct 模式：使用推理-行动循环的系统提示
        if self.react_mode:
            return self._generate_react_system_prompt()

        # 标准模式
        base_prompt = f"You are {self.name}, a helpful assistant."

        # 添加 Skills 索引（如果启用）
        if self.enable_skills and self.skill_manager:
            skills_section = self.skill_manager.get_system_prompt_section()
            if skills_section:
                base_prompt += "\n\n" + skills_section

        if not self.tools:
            return base_prompt

        # 添加工具使用启发式
        tool_guidance = """

# Tool Usage Guidelines

When using tools, follow these best practices:

1. **Understand Available Tools**: Always check which tools are available before deciding how to approach a task.

2. **Match Tools to Intent**: Choose tools that directly match the user's intent and task requirements.

3. **Prefer Specific Tools**: When multiple tools could work, prefer specialized tools over general-purpose ones.

4. **Tool Selection Strategy**:
   - For external/web information: Use web search or external API tools
   - For internal data: Use specialized internal tools (databases, file systems, etc.)
   - For calculations: Use calculator or computation tools
   - For data processing: Use appropriate data transformation tools

5. **Efficient Execution**:
   - Call tools in parallel when they don't depend on each other
   - Chain tool calls logically when one depends on another's output
   - Avoid redundant tool calls - reuse results when possible

6. **Error Handling**:
   - If a tool fails, try an alternative approach
   - Explain tool errors to the user clearly
   - Don't repeatedly call a failing tool

7. **Result Validation**:
   - Verify tool results make sense before using them
   - Cross-check important information when possible
   - Acknowledge uncertainty if tool results are unclear
"""
        return base_prompt + tool_guidance

    def _generate_react_system_prompt(self) -> str:
        """生成 ReAct 模式的系统提示"""
        base_prompt = f"""You are {self.name}, an intelligent agent that uses the ReAct (Reasoning + Acting) framework.

# ReAct Framework

You should approach tasks by alternating between **Thought** (reasoning) and **Action** (tool use):

1. **Thought**: Analyze the situation and decide what to do next
2. **Action**: Use tools to gather information or take actions
3. **Observation**: Review the results
4. **Repeat**: Continue the cycle until you can provide a final answer

## Reasoning Process

For each step:
- Think carefully about what information you need
- Consider which tools can help you get that information
- Plan your approach before taking action
- Reflect on results and adjust your strategy if needed

## Best Practices

- Break complex tasks into smaller, manageable steps
- Use tools strategically - each tool call should serve a clear purpose
- If a tool fails or returns unexpected results, analyze why and try a different approach
- Keep track of what you've learned at each step
- Only provide a final answer when you have sufficient information
"""

        # 添加 Skills 索引（如果启用）
        if self.enable_skills and self.skill_manager:
            skills_section = self.skill_manager.get_system_prompt_section()
            if skills_section:
                base_prompt += "\n\n" + skills_section

        if self.tools:
            tool_list = ", ".join([f"**{t.name}**" for t in self.tools])
            base_prompt += f"\n\n## Available Tools\n\nYou have access to these tools: {tool_list}\n\nUse them strategically to accomplish your goal."

        return base_prompt

    async def run(self, message: Message) -> Message:
        """
        核心递归方法

        流程：
        1. 委托给执行引擎
        2. 返回结果

        这个方法实现了递归状态机：
        - LLM 推理 → 工具调用 → 递归调用 run() → 最终结果

        Args:
            message: 输入消息

        Returns:
            响应消息

        Raises:
            AgentError: Agent 执行错误
            RecursionError: 递归深度超限
        """
        return await self.executor.execute(message)

    async def reply(self, message: Message) -> Message:
        """
        便捷方法 - 直接回复（alias for run）

        Args:
            message: 输入消息

        Returns:
            响应消息
        """
        return await self.run(message)

    def reset(self) -> None:
        """重置 Agent 状态"""
        self.executor.reset()

    def get_stats(self) -> dict:
        """获取 Agent 统计信息"""
        stats = {
            "name": self.name,
            "num_tools": len(self.tools),
            "executor_stats": self.executor.get_stats(),
        }

        # 添加 Skills 统计
        if self.enable_skills and self.skill_manager:
            stats["skills"] = self.skill_manager.get_stats()

        return stats

    # ===== Skills Management Methods =====

    def list_skills(self, category: Optional[str] = None) -> List:
        """
        列出可用技能

        Args:
            category: 筛选分类（可选）

        Returns:
            技能列表
        """
        if not self.enable_skills or not self.skill_manager:
            return []

        return self.skill_manager.list_skills(category=category)

    def get_skill(self, name: str):
        """
        获取技能

        Args:
            name: 技能名称

        Returns:
            Skill 实例
        """
        if not self.enable_skills or not self.skill_manager:
            return None

        return self.skill_manager.get_skill(name)

    def reload_skills(self) -> None:
        """重新加载所有技能"""
        if self.enable_skills and self.skill_manager:
            self.skill_manager.reload()
            # 重新生成系统提示
            self.system_prompt = self._generate_default_system_prompt()
            self.executor.system_prompt = self.system_prompt

    def enable_skill(self, name: str) -> bool:
        """启用技能"""
        if not self.enable_skills or not self.skill_manager:
            return False

        result = self.skill_manager.enable_skill(name)
        if result:
            # 更新系统提示
            self.system_prompt = self._generate_default_system_prompt()
            self.executor.system_prompt = self.system_prompt
        return result

    def disable_skill(self, name: str) -> bool:
        """禁用技能"""
        if not self.enable_skills or not self.skill_manager:
            return False

        result = self.skill_manager.disable_skill(name)
        if result:
            # 更新系统提示
            self.system_prompt = self._generate_default_system_prompt()
            self.executor.system_prompt = self.system_prompt
        return result

    def create_skill(
        self,
        name: str,
        description: str,
        category: str = "general",
        **kwargs
    ):
        """
        创建新技能

        Args:
            name: 技能名称
            description: 描述
            category: 分类
            **kwargs: 其他参数

        Returns:
            创建的 Skill 实例
        """
        if not self.enable_skills or not self.skill_manager:
            raise RuntimeError("Skills system is not enabled")

        skill = self.skill_manager.create_skill(
            name=name,
            description=description,
            category=category,
            **kwargs
        )

        # 更新系统提示
        self.system_prompt = self._generate_default_system_prompt()
        self.executor.system_prompt = self.system_prompt

        return skill

    def __repr__(self) -> str:
        return f"Agent(name='{self.name}', tools={len(self.tools)})"
