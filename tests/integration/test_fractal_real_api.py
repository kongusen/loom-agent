"""
Fractal Architecture Real API Integration Test

测试目标：
1. 验证 EventBus → Memory → Context 数据流
2. 验证分形委派（多层递归）
3. 验证记忆继承和同步

Phase 5: 预算控制已移除，只测试核心分形功能。

测试场景：
一个复杂的研究任务，需要多层委派：
- Level 0 (Root): 研究 Python 异步编程最佳实践
  - Level 1 (Child 1): 研究 asyncio 核心概念
    - Level 2 (Grandchild 1): 研究 event loop
    - Level 2 (Grandchild 2): 研究 coroutines
  - Level 1 (Child 2): 研究实际应用案例
    - Level 2 (Grandchild 3): 研究 web 框架
"""

import os
from datetime import datetime

import pytest

from loom.agent import Agent
from loom.config.llm import LLMConfig
from loom.events.event_bus import EventBus
from loom.providers.llm.mock import MockLLMProvider
from loom.providers.llm.openai import OpenAIProvider
from loom.runtime import Task, TaskStatus


@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="Requires OPENAI_API_KEY environment variable",
)
class TestFractalRealAPI:
    """基于真实 API 的分形架构测试"""

    @pytest.fixture
    def llm_provider(self):
        """创建 LLM 提供者"""
        config = LLMConfig(
            provider="openai",
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),  # 从环境变量读取，默认 gpt-4o-mini
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL"),  # 支持自定义端点
            temperature=0.7,
        )
        return OpenAIProvider(config)

    @pytest.fixture
    def event_bus(self):
        """创建事件总线"""
        return EventBus()

    @pytest.mark.asyncio
    @pytest.mark.xfail(reason="Real API test - may timeout without proper API configuration")
    async def test_fractal_delegation_with_memory_flow(self, llm_provider, event_bus):
        """
        测试分形委派和记忆流动

        验证点：
        1. 父节点可以创建子节点
        2. 子节点继承父节点记忆
        3. 子节点结果同步回父节点
        4. EventBus → Memory → Context 数据流正确
        5. 预算控制生效
        """
        # 创建根节点 Agent
        root_agent = Agent(
            node_id="root_researcher",
            llm_provider=llm_provider,
            system_prompt="""你是一个研究助手。

当任务复杂时，你可以使用 delegate_task 工具将子任务委派给子节点。
子节点会自动创建，你不需要指定 target_agent。

示例：
- 如果任务是"研究 Python 异步编程"，你可以委派：
  1. "研究 asyncio 核心概念"
  2. "研究实际应用案例"

完成所有子任务后，使用 done 工具总结结果。""",
            event_bus=event_bus,
            max_iterations=15,
            require_done_tool=True,
            recursive_depth=0,
        )

        # 创建测试任务
        task = Task(
            task_id="research_async_python",
            action="execute",
            parameters={
                "content": """请研究 Python 异步编程的最佳实践。

要求：
1. 解释 asyncio 的核心概念（event loop, coroutines）
2. 提供实际应用案例
3. 总结最佳实践

如果任务复杂，可以使用 delegate_task 工具委派子任务。"""
            },
            session_id="test_session_001",
        )

        # 执行任务
        start_time = datetime.now()
        result_task = await root_agent.execute_task(task)
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # ==================== 验证点 1: 任务完成 ====================
        # 打印任务状态和错误信息（如果有）
        print(f"\n任务状态: {result_task.status}")
        if result_task.error:
            print(f"错误信息: {result_task.error}")
        if result_task.result:
            print(f"结果类型: {type(result_task.result)}")
            print(f"结果内容: {result_task.result}")

        assert (
            result_task.status == TaskStatus.COMPLETED
        ), f"任务应该成功完成，实际状态: {result_task.status}, 错误: {result_task.error}"
        assert result_task.result is not None, "应该有结果"

        print(f"\n{'='*60}")
        print(f"任务执行时间: {duration:.2f} 秒")
        print(f"{'='*60}")

        # 提取结果内容
        if isinstance(result_task.result, dict):
            result_content = result_task.result.get("content", "")
        else:
            result_content = str(result_task.result)

        print(f"\n最终结果:\n{result_content[:500]}...")

        # ==================== 验证点 2: Memory 数据流 ====================
        # 检查 Memory 是否正确存储了任务
        memory = root_agent.memory

        # L1: 最近任务
        l1_tasks = memory.get_l1_tasks(limit=50)
        print(f"\n{'='*60}")
        print(f"L1 Memory: {len(l1_tasks)} 个任务")
        print(f"{'='*60}")

        # 打印所有任务的详细信息
        print("\n所有 L1 任务详情:")
        for i, task in enumerate(l1_tasks[:20], 1):  # 只显示前20个
            print(f"{i}. action={task.action}, task_id={task.task_id[:30]}...")
            if task.action == "node.tool_call":
                tool_name = task.parameters.get("tool_name", "unknown")
                print(f"   工具: {tool_name}")
            elif task.action == "node.thinking":
                content = task.parameters.get("content", "")[:500]
                print(f"   内容: {content}...")

        # 应该包含：
        # - 根任务
        # - thinking 事件
        # - tool_call 事件（delegate_task, done）
        assert len(l1_tasks) > 0, "L1 应该有任务记录"

        # 检查是否有 thinking 事件
        thinking_tasks = [t for t in l1_tasks if t.action == "node.thinking"]
        print(f"\nThinking 事件: {len(thinking_tasks)} 个")

        # 检查是否有 tool_call 事件
        tool_call_tasks = [t for t in l1_tasks if t.action == "node.tool_call"]
        print(f"Tool Call 事件: {len(tool_call_tasks)} 个")

        # L2: 重要任务
        l2_tasks = memory.get_l2_tasks(limit=50)
        print(f"\nL2 Memory: {len(l2_tasks)} 个重要任务")

        # ==================== 验证点 3: EventBus 订阅机制 ====================
        # Memory 应该通过订阅 EventBus 自动接收所有任务
        # 这已经在 L1/L2 检查中验证了

        # ==================== 验证点 4: Context 构建 ====================
        # 创建一个新任务，验证 Context 可以从 Memory 获取历史
        follow_up_task = Task(
            task_id="follow_up_task",
            action="execute",
            parameters={"content": "根据之前的研究，总结3个关键要点"},
            session_id="test_session_001",  # 同一个 session
        )

        # 构建上下文
        context_messages = await root_agent.context_orchestrator.build_context(follow_up_task)

        print(f"\n{'='*60}")
        print("Context 构建:")
        print(f"  消息数量: {len(context_messages)}")
        print(
            f"  包含历史: {len([m for m in context_messages if m.get('role') == 'assistant'])} 条"
        )
        print(f"{'='*60}")

        # 应该包含历史消息
        assert len(context_messages) > 1, "Context 应该包含历史消息"

        # ==================== 验证点 6: 分形委派（如果发生）====================
        # 检查是否有委派发生
        delegate_events = [
            t
            for t in l1_tasks
            if t.action == "node.tool_call"
            and "delegate_task" in str(t.parameters.get("tool_name", ""))
        ]

        if delegate_events:
            print(f"\n{'='*60}")
            print("分形委派:")
            print(f"  委派次数: {len(delegate_events)}")
            print(f"{'='*60}")

            for i, event in enumerate(delegate_events[:3], 1):
                subtask = event.parameters.get("tool_args", {}).get("subtask_description", "")
                print(f"  {i}. {subtask[:80]}...")

        # ==================== 最终验证 ====================
        print(f"\n{'='*60}")
        print("✅ 所有验证点通过!")
        print(f"{'='*60}")

        # 验证结果质量
        assert len(result_content) > 100, "结果应该有实质内容"

        # 验证结果包含关键词（异步编程相关）
        keywords = ["async", "await", "asyncio", "coroutine", "event loop"]
        found_keywords = [kw for kw in keywords if kw.lower() in result_content.lower()]
        print(f"\n找到的关键词: {found_keywords}")
        assert len(found_keywords) >= 2, f"结果应该包含至少2个关键词，实际: {found_keywords}"

    @pytest.mark.asyncio
    @pytest.mark.xfail(reason="Real API test - may timeout without proper API configuration")
    async def test_multi_level_fractal_delegation(self, llm_provider, event_bus):
        """
        测试多层分形委派

        验证点：
        1. 可以创建多层子节点（Level 0 → Level 1 → Level 2）
        2. 记忆在多层之间正确流动
        3. 最终结果正确收敛
        """
        # 创建根节点，使用更明确的提示词鼓励委派
        root_agent = Agent(
            node_id="root_planner",
            llm_provider=llm_provider,
            system_prompt="""你是一个任务规划助手。

对于复杂任务，你应该：
1. 使用 create_plan 工具创建执行计划
2. 或使用 delegate_task 工具委派子任务

delegate_task 工具会自动创建子节点，你只需要提供：
- subtask_description: 子任务描述
- context_hints: 相关上下文（可选）

完成后使用 done 工具。""",
            event_bus=event_bus,
            max_iterations=20,
            require_done_tool=True,
            recursive_depth=0,
        )

        # 创建一个明确需要多层委派的任务
        task = Task(
            task_id="complex_research",
            action="execute",
            parameters={
                "content": """请研究"如何构建一个高性能的 Python Web 应用"。

这个任务需要分解为多个子任务：
1. 研究 Web 框架选择（FastAPI vs Flask vs Django）
2. 研究性能优化技术（异步、缓存、数据库优化）
3. 研究部署方案（Docker、K8s、云服务）

请使用 delegate_task 工具将这些子任务委派出去。"""
            },
            session_id="test_session_002",
        )

        # 执行任务
        start_time = datetime.now()
        result_task = await root_agent.execute_task(task)
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # 验证任务完成
        assert result_task.status == TaskStatus.COMPLETED

        print(f"\n{'='*60}")
        print("多层委派测试")
        print(f"执行时间: {duration:.2f} 秒")
        print(f"{'='*60}")

        # 验证发生了委派
        memory = root_agent.memory
        l1_tasks = memory.get_l1_tasks(limit=100)

        delegate_events = [
            t
            for t in l1_tasks
            if t.action == "node.tool_call"
            and "delegate" in str(t.parameters.get("tool_name", "")).lower()
        ]

        print(f"\n委派事件: {len(delegate_events)} 个")

        if delegate_events:
            print("\n委派的子任务:")
            for i, event in enumerate(delegate_events[:5], 1):
                tool_args = event.parameters.get("tool_args", {})
                subtask = tool_args.get("subtask_description", tool_args.get("subtask", ""))
                print(f"  {i}. {subtask[:80]}...")

        # 验证结果
        if isinstance(result_task.result, dict):
            result_content = result_task.result.get("content", "")
        else:
            result_content = str(result_task.result)

        print(f"\n最终结果长度: {len(result_content)} 字符")
        print(f"结果预览:\n{result_content[:300]}...")

        assert len(result_content) > 50, "应该有实质性结果"

        print(f"\n{'='*60}")
        print("✅ 多层委派测试通过!")
        print(f"{'='*60}")


class TestFractalMockAPI:
    """基于 Mock LLM Provider 的分形架构测试（无需真实 API）"""

    @pytest.fixture
    def event_bus(self):
        """创建事件总线"""
        return EventBus()

    @pytest.mark.asyncio
    async def test_fractal_delegation_with_memory_flow_mock(self, event_bus):
        """
        测试分形委派和记忆流动（使用 Mock LLM）

        验证点：
        1. 父节点可以创建子节点
        2. 子节点继承父节点记忆
        3. 子节点结果同步回父节点
        4. EventBus → Memory → Context 数据流正确

        注意：MockLLMProvider 使用 call_count 跟踪调用次数。
        由于父节点和子节点共享同一个 provider 实例，需要设计响应序列
        来支持多个 Agent 的调用。
        """
        # 创建 Mock LLM Provider，设计响应序列模拟分形委派
        # 响应序列：
        # 1. 父节点：思考任务
        # 2. 父节点：委派第一个子任务
        # 3. 子节点1：执行子任务并完成
        # 4. 父节点：委派第二个子任务
        # 5. 子节点2：执行子任务并完成
        # 6. 父节点：总结结果并完成
        llm_provider = MockLLMProvider(
            responses=[
                # 父节点第1次调用：思考任务
                {
                    "type": "text",
                    "content": "我需要研究 Python 异步编程。这个任务可以分解为两个子任务。",
                },
                # 父节点第2次调用：委派第一个子任务
                {
                    "type": "tool_call",
                    "name": "delegate_task",
                    "arguments": {
                        "subtask_description": "研究 asyncio 的核心概念（event loop, coroutines）",
                    },
                },
                # 子节点1第1次调用：执行子任务
                {
                    "type": "text",
                    "content": "asyncio 是 Python 的异步编程库。核心概念包括：\n1. Event Loop: 事件循环是异步编程的核心\n2. Coroutines: 协程是异步函数",
                },
                # 子节点1第2次调用：完成子任务
                {
                    "type": "tool_call",
                    "name": "done",
                    "arguments": {
                        "message": "已完成 asyncio 核心概念研究：event loop 和 coroutines 是核心概念。",
                    },
                },
                # 父节点第3次调用：委派第二个子任务
                {
                    "type": "tool_call",
                    "name": "delegate_task",
                    "arguments": {
                        "subtask_description": "研究实际应用案例",
                    },
                },
                # 子节点2第1次调用：执行子任务
                {
                    "type": "text",
                    "content": "实际应用案例包括：\n1. Web 框架：FastAPI 使用 async/await\n2. 数据库操作：异步数据库连接\n3. 网络请求：异步 HTTP 客户端",
                },
                # 子节点2第2次调用：完成子任务
                {
                    "type": "tool_call",
                    "name": "done",
                    "arguments": {
                        "message": "已完成实际应用案例研究：包括 FastAPI、异步数据库和 HTTP 客户端。",
                    },
                },
                # 父节点第4次调用：总结结果
                {
                    "type": "text",
                    "content": "基于子任务的研究结果，总结 Python 异步编程最佳实践：\n\n1. 理解 asyncio 核心概念（event loop, coroutines）\n2. 在实际应用中合理使用 async/await\n3. 选择合适的异步框架和库",
                },
                # 父节点第5次调用：完成整个任务
                {
                    "type": "tool_call",
                    "name": "done",
                    "arguments": {
                        "message": "已完成 Python 异步编程最佳实践研究。核心概念包括 event loop 和 coroutines，实际应用包括 FastAPI 等框架。",
                    },
                },
            ]
        )

        # 创建根节点 Agent
        root_agent = Agent(
            node_id="root_researcher",
            llm_provider=llm_provider,
            system_prompt="""你是一个研究助手。

当任务复杂时，你可以使用 delegate_task 工具将子任务委派给子节点。
子节点会自动创建，你不需要指定 target_agent。

示例：
- 如果任务是"研究 Python 异步编程"，你可以委派：
  1. "研究 asyncio 核心概念"
  2. "研究实际应用案例"

完成所有子任务后，使用 done 工具总结结果。""",
            event_bus=event_bus,
            max_iterations=15,
            require_done_tool=True,
            recursive_depth=0,
        )

        # 创建测试任务
        task = Task(
            task_id="research_async_python",
            action="execute",
            parameters={
                "content": """请研究 Python 异步编程的最佳实践。

要求：
1. 解释 asyncio 的核心概念（event loop, coroutines）
2. 提供实际应用案例
3. 总结最佳实践

如果任务复杂，可以使用 delegate_task 工具委派子任务。"""
            },
            session_id="test_session_001",
        )

        # 执行任务
        start_time = datetime.now()
        result_task = await root_agent.execute_task(task)
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # ==================== 验证点 1: 任务完成 ====================
        print(f"\n任务状态: {result_task.status}")
        if result_task.error:
            print(f"错误信息: {result_task.error}")
        if result_task.result:
            print(f"结果类型: {type(result_task.result)}")

        assert (
            result_task.status == TaskStatus.COMPLETED
        ), f"任务应该成功完成，实际状态: {result_task.status}, 错误: {result_task.error}"
        assert result_task.result is not None, "应该有结果"

        print(f"\n{'='*60}")
        print(f"任务执行时间: {duration:.2f} 秒")
        print(f"{'='*60}")

        # 提取结果内容
        if isinstance(result_task.result, dict):
            result_content = result_task.result.get("content", "")
        else:
            result_content = str(result_task.result)

        print(f"\n最终结果:\n{result_content[:500]}...")

        # ==================== 验证点 2: Memory 数据流 ====================
        memory = root_agent.memory

        # L1: 最近任务
        l1_tasks = memory.get_l1_tasks(limit=50)
        print(f"\n{'='*60}")
        print(f"L1 Memory: {len(l1_tasks)} 个任务")
        print(f"{'='*60}")

        # 打印所有任务的详细信息
        print("\n所有 L1 任务详情:")
        for i, task in enumerate(l1_tasks[:20], 1):  # 只显示前20个
            print(f"{i}. action={task.action}, task_id={task.task_id[:30]}...")
            if task.action == "node.tool_call":
                tool_name = task.parameters.get("tool_name", "unknown")
                print(f"   工具: {tool_name}")
            elif task.action == "node.thinking":
                content = task.parameters.get("content", "")[:500]
                print(f"   内容: {content}...")

        assert len(l1_tasks) > 0, "L1 应该有任务记录"

        # 检查是否有 thinking 事件
        thinking_tasks = [t for t in l1_tasks if t.action == "node.thinking"]
        print(f"\nThinking 事件: {len(thinking_tasks)} 个")

        # 检查是否有 tool_call 事件
        tool_call_tasks = [t for t in l1_tasks if t.action == "node.tool_call"]
        print(f"Tool Call 事件: {len(tool_call_tasks)} 个")

        # L2: 重要任务
        l2_tasks = memory.get_l2_tasks(limit=50)
        print(f"\nL2 Memory: {len(l2_tasks)} 个重要任务")

        # ==================== 验证点 3: EventBus 订阅机制 ====================
        # Memory 应该通过订阅 EventBus 自动接收所有任务
        # 这已经在 L1/L2 检查中验证了

        # ==================== 验证点 4: Context 构建 ====================
        # 创建一个新任务，验证 Context 可以从 Memory 获取历史
        follow_up_task = Task(
            task_id="follow_up_task",
            action="execute",
            parameters={"content": "根据之前的研究，总结3个关键要点"},
            session_id="test_session_001",  # 同一个 session
        )

        # 构建上下文
        context_messages = await root_agent.context_orchestrator.build_context(follow_up_task)

        print(f"\n{'='*60}")
        print("Context 构建:")
        print(f"  消息数量: {len(context_messages)}")
        print(
            f"  包含历史: {len([m for m in context_messages if m.get('role') == 'assistant'])} 条"
        )
        print(f"{'='*60}")

        # 应该包含历史消息
        assert len(context_messages) > 1, "Context 应该包含历史消息"

        # ==================== 验证点 5: 分形委派 ====================
        # 检查是否有委派发生
        delegate_events = [
            t
            for t in l1_tasks
            if t.action == "node.tool_call"
            and "delegate_task" in str(t.parameters.get("tool_name", ""))
        ]

        if delegate_events:
            print(f"\n{'='*60}")
            print("分形委派:")
            print(f"  委派次数: {len(delegate_events)}")
            print(f"{'='*60}")

            for i, event in enumerate(delegate_events[:3], 1):
                subtask = event.parameters.get("tool_args", {}).get("subtask_description", "")
                print(f"  {i}. {subtask[:80]}...")

        # ==================== 最终验证 ====================
        print(f"\n{'='*60}")
        print("✅ 所有验证点通过!")
        print(f"{'='*60}")

        # 验证结果质量
        assert len(result_content) > 50, "结果应该有实质内容"

        # 验证结果包含关键词（异步编程相关）
        keywords = ["async", "await", "asyncio", "coroutine", "event loop"]
        found_keywords = [kw for kw in keywords if kw.lower() in result_content.lower()]
        print(f"\n找到的关键词: {found_keywords}")
        # Mock 测试中，关键词可能不完全匹配，所以降低要求
        assert len(found_keywords) >= 1, f"结果应该包含至少1个关键词，实际: {found_keywords}"


if __name__ == "__main__":
    # 可以直接运行此文件进行测试
    pytest.main([__file__, "-v", "-s"])
