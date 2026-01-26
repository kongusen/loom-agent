"""
Loom Code Assistant Demo

展示Loom框架的核心能力：
1. 四层记忆系统（L1-L4）- 记住对话历史和代码知识
2. 工具系统 - 文件读取、代码搜索、代码分析
3. 外部知识库 - 代码库知识集成
4. 语义搜索 - 基于向量的代码搜索
5. 多轮对话 - 持续的上下文理解

类似Claude Code的能力展示。
"""

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

from loom.config import LLMConfig
from loom.orchestration.agent import Agent
from loom.protocol import Task, TaskStatus
from loom.providers.llm.openai import OpenAIProvider
from loom.tools.registry import ToolRegistry

# 加载环境变量
load_dotenv()


# ============================================================================
# 自定义Agent - 支持实际工具执行
# ============================================================================


class CodeAssistantAgent(Agent):
    """
    代码助手Agent - 扩展基础Agent以支持实际工具执行

    这个类重写了Agent的_execute_impl方法，添加了真实的工具执行逻辑。
    """

    def __init__(self, tool_registry: ToolRegistry, **kwargs):
        """
        初始化代码助手Agent

        Args:
            tool_registry: 工具注册表
            **kwargs: 传递给基类的参数
        """
        super().__init__(**kwargs)
        self.tool_registry = tool_registry

    async def _execute_single_tool(self, tool_name: str, tool_args: dict | str) -> str:
        """
        执行单个工具

        Args:
            tool_name: 工具名称
            tool_args: 工具参数（可能是dict或JSON字符串）

        Returns:
            工具执行结果
        """
        import json

        # 如果tool_args是字符串，解析为字典
        if isinstance(tool_args, str):
            try:
                tool_args = json.loads(tool_args)
            except json.JSONDecodeError:
                return f"错误：无法解析工具参数 - {tool_args}"

        # 获取工具的可调用对象
        tool_func = self.tool_registry.get_callable(tool_name)

        if tool_func is None:
            return f"错误：工具 '{tool_name}' 未找到"

        try:
            # 执行工具
            result = await tool_func(**tool_args)
            return str(result)
        except Exception as e:
            return f"错误：工具执行失败 - {str(e)}"

    async def _execute_impl(self, task: Task) -> Task:
        """
        重写执行任务方法，添加真实的工具执行逻辑

        这个方法基于Agent._execute_impl，但修改了工具执行部分
        """
        from loom.exceptions import TaskComplete
        from loom.tools.done_tool import execute_done_tool

        # 存储任务到记忆
        self.memory.add_task(task)

        # Agent 循环
        accumulated_messages = []
        final_content = ""

        try:
            for iteration in range(self.max_iterations):
                # 1. 构建上下文
                messages = await self.context_manager.build_context(task)

                # 添加累积消息
                if accumulated_messages:
                    messages.extend(accumulated_messages)

                # 2. 调用 LLM（流式）
                full_content = ""
                tool_calls = []

                print(f"\n[迭代 {iteration + 1}] 调用LLM...")
                print(f"[调试] 消息数量: {len(messages)}")
                print(f"[调试] 工具数量: {len(self.all_tools) if self.all_tools else 0}")

                chunk_count = 0
                async for chunk in self.llm_provider.stream_chat(
                    messages, tools=self.all_tools if self.all_tools else None
                ):
                    chunk_count += 1
                    print(f"\n[调试] 收到chunk #{chunk_count}, 类型: {chunk.type}")

                    if chunk.type == "text":
                        full_content += chunk.content
                        # 实时打印LLM的思考过程
                        print(chunk.content, end="", flush=True)
                        await self.publish_thinking(
                            content=chunk.content,
                            task_id=task.task_id,
                            metadata={"iteration": iteration},
                        )

                    elif chunk.type == "tool_call_complete":
                        tool_calls.append(chunk.content)
                        print(f"\n[工具调用] {chunk.content.get('name', 'unknown')}")

                    elif chunk.type == "error":
                        print(f"\n[错误] {chunk.content}")
                        await self._publish_event(
                            action="node.error",
                            parameters={"error": chunk.content},
                            task_id=task.task_id,
                        )

                final_content = full_content
                print(f"\n[调试] 总共收到 {chunk_count} 个chunks")
                print(f"[调试] final_content长度: {len(final_content)}")
                print(f"[调试] tool_calls数量: {len(tool_calls)}")
                print()  # 换行

                # 3. 检查是否有工具调用
                if not tool_calls:
                    if self.require_done_tool:
                        accumulated_messages.append(
                            {
                                "role": "system",
                                "content": "Please call the 'done' tool when you have completed the task.",
                            }
                        )
                        continue
                    else:
                        # 不要求 done tool，直接结束
                        break

                # 4. 执行工具调用
                # 先添加assistant消息（包含tool_calls）
                accumulated_messages.append(
                    {
                        "role": "assistant",
                        "content": full_content or "",
                        "tool_calls": [
                            {
                                "id": tc.get("id", ""),
                                "type": "function",
                                "function": {
                                    "name": tc.get("name", ""),
                                    "arguments": tc.get("arguments", {}),
                                },
                            }
                            for tc in tool_calls
                        ],
                    }
                )

                # 执行每个工具并添加tool消息
                for tool_call in tool_calls:
                    tool_name = tool_call.get("name", "")
                    tool_args = tool_call.get("arguments", {})

                    # 发布工具调用事件
                    await self.publish_tool_call(
                        tool_name=tool_name,
                        tool_args=tool_args,
                        task_id=task.task_id,
                    )

                    # 检查是否是 done tool
                    if tool_name == "done":
                        await execute_done_tool(tool_args)

                    # 处理元工具
                    if tool_name == "create_plan":
                        result = f"Plan created: {tool_args.get('goal', '')}"
                    elif tool_name == "delegate_task":
                        target_agent = tool_args.get("target_agent", "")
                        subtask = tool_args.get("subtask", "")
                        result = await self._execute_delegate_task(
                            target_agent, subtask, task.task_id
                        )
                    else:
                        # 普通工具 - 实际执行
                        print(f"[执行工具] {tool_name}({tool_args})")
                        result = await self._execute_single_tool(tool_name, tool_args)
                        print(f"[工具结果] {result[:200]}...")

                    # 添加tool消息
                    accumulated_messages.append(
                        {
                            "role": "tool",
                            "content": result,
                            "tool_call_id": tool_call.get("id", ""),
                        }
                    )

        except TaskComplete as e:
            # 捕获 TaskComplete 异常，正常结束
            task.status = TaskStatus.COMPLETED
            task.result = {
                "content": e.message,
                "completed_explicitly": True,
            }
            self.memory.add_task(task)
            return task

        # 如果循环正常结束（没有调用 done）
        task.status = TaskStatus.COMPLETED
        task.result = {
            "content": final_content,
            "completed_explicitly": False,
            "iterations": iteration + 1,
        }

        # 存储完成的任务到记忆
        self.memory.add_task(task)

        return task


# ============================================================================
# Agent配置和创建
# ============================================================================


def create_code_assistant():
    """创建代码助手Agent"""

    # 1. 配置LLM - 使用 LLMConfig 统一配置管理
    # 用户在应用层从环境变量读取配置，框架不读取环境变量
    llm_config = LLMConfig(
        provider="openai",
        api_key=os.getenv("OPENAI_API_KEY"),  # 用户控制配置来源
        base_url=os.getenv("OPENAI_BASE_URL"),
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0.7,
        max_tokens=2000,
    )

    llm_provider = OpenAIProvider(llm_config)

    # 2. 创建工具注册表和工具
    tool_registry = ToolRegistry()

    # 注册工具函数
    async def read_file(file_path: str) -> str:
        """读取文件内容"""
        try:
            path = Path(file_path)
            if not path.exists():
                return f"错误：文件不存在 - {file_path}"
            if not path.is_file():
                return f"错误：不是文件 - {file_path}"
            if path.stat().st_size > 1024 * 1024:
                return f"错误：文件太大 - {file_path}"
            content = path.read_text(encoding="utf-8")
            return f"文件内容 ({file_path}):\n\n{content}"
        except Exception as e:
            return f"错误：读取文件失败 - {str(e)}"

    async def list_files(directory: str = ".", pattern: str = "*.py") -> str:
        """列出目录中的文件"""
        try:
            path = Path(directory)
            if not path.exists():
                return f"错误：目录不存在 - {directory}"
            if not path.is_dir():
                return f"错误：不是目录 - {directory}"
            files = list(path.glob(pattern))
            if not files:
                return f"未找到匹配的文件：{pattern} in {directory}"
            file_list = "\n".join([f"  - {f.relative_to(path)}" for f in files[:50]])
            count_msg = f"\n\n(显示前50个，共{len(files)}个文件)" if len(files) > 50 else ""
            return f"文件列表 ({directory}/{pattern}):\n{file_list}{count_msg}"
        except Exception as e:
            return f"错误：列出文件失败 - {str(e)}"

    async def search_code(keyword: str, directory: str = ".", file_pattern: str = "*.py") -> str:
        """在代码中搜索关键词"""
        try:
            path = Path(directory)
            if not path.exists():
                return f"错误：目录不存在 - {directory}"
            results = []
            files = list(path.rglob(file_pattern))
            for file_path in files[:100]:
                try:
                    content = file_path.read_text(encoding="utf-8")
                    lines = content.split("\n")
                    for line_num, line in enumerate(lines, 1):
                        if keyword.lower() in line.lower():
                            results.append(f"{file_path}:{line_num}: {line.strip()}")
                            if len(results) >= 20:
                                break
                except Exception:
                    continue
                if len(results) >= 20:
                    break
            if not results:
                return f"未找到包含 '{keyword}' 的代码"
            result_text = "\n".join(results)
            return f"搜索结果 (关键词: {keyword}):\n\n{result_text}"
        except Exception as e:
            return f"错误：搜索失败 - {str(e)}"

    async def analyze_code_structure(file_path: str) -> str:
        """分析代码结构"""
        try:
            path = Path(file_path)
            if not path.exists():
                return f"错误：文件不存在 - {file_path}"
            content = path.read_text(encoding="utf-8")
            lines = content.split("\n")
            imports = []
            classes = []
            functions = []
            for line_num, line in enumerate(lines, 1):
                stripped = line.strip()
                if stripped.startswith("import ") or stripped.startswith("from "):
                    imports.append(f"  L{line_num}: {stripped}")
                elif stripped.startswith("class "):
                    classes.append(f"  L{line_num}: {stripped}")
                elif stripped.startswith("def ") or stripped.startswith("async def "):
                    functions.append(f"  L{line_num}: {stripped}")
            result = f"代码结构分析 ({file_path}):\n\n"
            result += f"导入 ({len(imports)}):\n" + "\n".join(imports[:10]) + "\n\n"
            result += f"类 ({len(classes)}):\n" + "\n".join(classes[:10]) + "\n\n"
            result += f"函数 ({len(functions)}):\n" + "\n".join(functions[:10])
            return result
        except Exception as e:
            return f"错误：分析失败 - {str(e)}"

    # 注册所有工具
    tool_registry.register_function(read_file)
    tool_registry.register_function(list_files)
    tool_registry.register_function(search_code)
    tool_registry.register_function(analyze_code_structure)

    # 转换为Agent需要的格式
    tools = []
    for definition in tool_registry.definitions:
        tools.append(
            {
                "type": "function",
                "function": {
                    "name": definition.name,
                    "description": definition.description,
                    "parameters": definition.input_schema,
                },
            }
        )

    # 3. 系统提示词
    system_prompt = """你是一个专业的代码助手，基于Loom框架构建。

你的能力：
- 读取和分析代码文件
- 搜索代码库中的关键词
- 分析代码结构（类、函数、导入）
- 记住对话历史和代码知识（四层记忆系统）
- 提供代码建议和解释

工作方式：
1. 使用工具来访问代码库
2. 记住之前的对话和分析结果
3. 提供清晰、准确的代码分析和建议
4. 主动使用记忆系统来保持上下文

请始终保持专业、准确、有帮助。"""

    # 4. 创建CodeAssistantAgent（支持真实工具执行）
    agent = CodeAssistantAgent(
        tool_registry=tool_registry,
        node_id="code-assistant",
        llm_provider=llm_provider,
        system_prompt=system_prompt,
        tools=tools,
        available_agents={},
        require_done_tool=False,
        max_iterations=15,
    )

    return agent


# ============================================================================
# 演示函数
# ============================================================================


async def demo_basic_usage(agent: Agent):
    """演示基本使用 - 文件读取和分析"""
    print("\n" + "=" * 70)
    print("演示 1: 基本使用 - 文件读取和代码分析")
    print("=" * 70)

    # 任务1: 列出当前目录的Python文件
    print("\n[任务1] 列出examples目录的Python文件")
    task1 = Task(
        task_id="demo-task-001",
        source_agent="user",
        target_agent=agent.node_id,
        action="execute",
        parameters={"content": "请列出examples目录中的所有Python文件"},
    )

    result1 = await agent.execute_task(task1)
    print(f"状态: {result1.status.value}")
    content1 = (
        result1.result.get("content", "")
        or result1.result.get("response", "")
        or str(result1.result)
    )
    print(f"结果:\n{content1[:500]}")
    if len(content1) > 500:
        print(f"... (共{len(content1)}字符)")

    # 任务2: 分析一个文件的结构
    print("\n[任务2] 分析autonomous_agent_demo.py的代码结构")
    task2 = Task(
        task_id="demo-task-002",
        source_agent="user",
        target_agent=agent.node_id,
        action="execute",
        parameters={"content": "请分析examples/autonomous_agent_demo.py的代码结构"},
    )

    result2 = await agent.execute_task(task2)
    print(f"状态: {result2.status.value}")
    content2 = (
        result2.result.get("content", "")
        or result2.result.get("response", "")
        or str(result2.result)
    )
    print(f"结果:\n{content2[:500]}")
    if len(content2) > 500:
        print(f"... (共{len(content2)}字符)")


async def demo_memory_system(agent: Agent):
    """演示记忆系统 - 多轮对话"""
    print("\n" + "=" * 70)
    print("演示 2: 记忆系统 - 多轮对话与上下文保持")
    print("=" * 70)

    # 第一轮：询问某个文件
    print("\n[第1轮] 询问Agent类的位置")
    task1 = Task(
        task_id="demo-task-003",
        source_agent="user",
        target_agent=agent.node_id,
        action="execute",
        parameters={"content": "请搜索Agent类的定义在哪个文件中"},
    )

    result1 = await agent.execute_task(task1)
    content1 = (
        result1.result.get("content", "")
        or result1.result.get("response", "")
        or str(result1.result)
    )
    print(f"结果:\n{content1[:400]}")
    if len(content1) > 400:
        print(f"... (共{len(content1)}字符)")

    # 第二轮：基于上一轮的结果继续询问
    print("\n[第2轮] 基于记忆继续询问（测试L1工作记忆）")
    task2 = Task(
        task_id="demo-task-004",
        source_agent="user",
        target_agent=agent.node_id,
        action="execute",
        parameters={"content": "请读取刚才找到的那个文件，并分析Agent类的主要方法"},
    )

    result2 = await agent.execute_task(task2)
    content2 = (
        result2.result.get("content", "")
        or result2.result.get("response", "")
        or str(result2.result)
    )
    print(f"结果:\n{content2[:400]}")
    if len(content2) > 400:
        print(f"... (共{len(content2)}字符)")

    # 第三轮：测试记忆保持
    print("\n[第3轮] 测试记忆保持")
    task3 = Task(
        task_id="demo-task-005",
        source_agent="user",
        target_agent=agent.node_id,
        action="execute",
        parameters={"content": "我们刚才分析了哪个类？它有哪些主要方法？"},
    )

    result3 = await agent.execute_task(task3)
    content3 = (
        result3.result.get("content", "")
        or result3.result.get("response", "")
        or str(result3.result)
    )
    print(f"结果:\n{content3[:400]}")
    if len(content3) > 400:
        print(f"... (共{len(content3)}字符)")


async def demo_code_search(agent: Agent):
    """演示代码搜索能力"""
    print("\n" + "=" * 70)
    print("演示 3: 代码搜索 - 在代码库中查找关键词")
    print("=" * 70)

    print("\n[任务] 搜索'LoomMemory'关键词")
    task = Task(
        task_id="demo-task-006",
        source_agent="user",
        target_agent=agent.node_id,
        action="execute",
        parameters={"content": "请在loom目录中搜索'LoomMemory'关键词，找出相关的代码位置"},
    )

    result = await agent.execute_task(task)
    print(f"状态: {result.status.value}")
    content = (
        result.result.get("content", "") or result.result.get("response", "") or str(result.result)
    )
    print(f"结果:\n{content[:600]}")
    if len(content) > 600:
        print(f"... (共{len(content)}字符)")


async def demo_statistics(agent: Agent):
    """展示Agent统计信息"""
    print("\n" + "=" * 70)
    print("演示 4: Agent统计信息")
    print("=" * 70)

    stats = agent.get_stats()
    print("\n执行统计:")
    print(f"  - 总执行次数: {stats['execution_count']}")
    print(f"  - 成功次数: {stats['success_count']}")
    print(f"  - 失败次数: {stats['failure_count']}")
    print(f"  - 成功率: {stats['success_rate']:.1%}")

    # 记忆系统统计
    if hasattr(agent, "memory") and agent.memory:
        print("\n记忆系统:")
        print(f"  - L1 (工作记忆): {len(agent.memory._l1_tasks)} 项")
        print(f"  - L2 (会话记忆): {len(agent.memory._l2_tasks)} 项")
        print(f"  - L3 (情节记忆): {len(agent.memory._l3_summaries)} 项")
        print(f"  - L4 (向量存储): {'已启用' if agent.memory._l4_vector_store else '未启用'}")


# ============================================================================
# 主函数
# ============================================================================


async def main():
    """主函数 - 运行所有演示"""
    print("\n" + "=" * 70)
    print("Loom Code Assistant Demo")
    print("展示Loom框架的核心能力")
    print("=" * 70)

    # 检查环境变量
    if not os.getenv("OPENAI_API_KEY"):
        print("\n错误: 未设置OPENAI_API_KEY环境变量")
        print("请创建.env文件并设置API密钥")
        print("参考.env.example文件")
        return

    print("\n正在创建代码助手...")
    agent = create_code_assistant()
    print(f"✓ 代码助手创建成功: {agent.node_id}")
    print(f"✓ 工具数量: {len(agent.all_tools)}")
    print("✓ 记忆系统: 已启用（L1-L4四层记忆）")

    try:
        # 运行演示
        await demo_basic_usage(agent)
        await demo_memory_system(agent)
        await demo_code_search(agent)
        await demo_statistics(agent)

        print("\n" + "=" * 70)
        print("演示完成！")
        print("=" * 70)

        print("\n核心能力展示:")
        print("✓ 工具系统 - 文件读取、代码搜索、结构分析")
        print("✓ 记忆系统 - L1-L4四层记忆，自动迁移和压缩")
        print("✓ 多轮对话 - 保持上下文，记住之前的分析")
        print("✓ 自主决策 - Agent自动选择合适的工具")

    except Exception as e:
        print(f"\n错误: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
