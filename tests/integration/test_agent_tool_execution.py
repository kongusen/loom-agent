"""
Agent Tool Execution Integration Tests

测试Agent真实的工具执行流程，验证：
1. 工具注册表的查找和执行
2. LLM返回tool_calls后的处理
3. 工具执行结果的返回
4. 多轮工具调用

这些测试应该能发现之前的占位符bug（返回"Tool X executed"而不是真实结果）。
"""

import pytest

from loom.agent import Agent
from loom.protocol import Task, TaskStatus
from loom.providers.llm.mock import MockLLMProvider
from loom.tools.core.registry import ToolRegistry


class TestAgentToolExecution:
    """测试Agent工具执行"""

    @pytest.mark.asyncio
    async def test_agent_executes_single_tool(self):
        """测试Agent执行单个工具 - 验证工具真的被执行"""
        # 1. 创建工具注册表
        tool_registry = ToolRegistry()

        # 使用一个有副作用的工具（修改列表）
        execution_log = []

        async def calculator(a: int, b: int) -> int:
            """计算两个数的和，并记录执行"""
            result = a + b
            execution_log.append({"tool": "calculator", "args": {"a": a, "b": b}, "result": result})
            return result

        tool_registry.register_function(calculator)

        # 2. 创建MockLLM，让它调用工具
        llm = MockLLMProvider(
            responses=[
                {"type": "text", "content": "I'll calculate 2 + 3..."},
                {"type": "tool_call", "name": "calculator", "arguments": {"a": 2, "b": 3}},
                {"type": "text", "content": "Done!"},
            ]
        )

        # 3. 创建Agent
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "calculator",
                    "description": "Calculate sum of two numbers",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "a": {"type": "integer"},
                            "b": {"type": "integer"},
                        },
                        "required": ["a", "b"],
                    },
                },
            }
        ]

        agent = Agent(
            node_id="test-agent",
            llm_provider=llm,
            tool_registry=tool_registry,
            tools=tools,
            require_done_tool=False,
            max_iterations=3,
        )

        # 4. 执行任务
        task = Task(
            task_id="test-task-001",
            action="execute",
            parameters={"content": "Calculate 2 + 3"},
        )

        result = await agent.execute_task(task)

        # 5. 验证结果
        assert result.status == TaskStatus.COMPLETED

        # 关键验证：检查execution_log是否被修改
        print(f"\n[DEBUG] Execution log: {execution_log}")

        # 如果工具真的被执行，execution_log应该至少包含一条记录
        assert len(execution_log) >= 1, f"Expected at least 1 execution, got {len(execution_log)}"

        # 验证第一次执行的参数和结果
        assert execution_log[0]["tool"] == "calculator"
        assert execution_log[0]["args"] == {"a": 2, "b": 3}
        assert execution_log[0]["result"] == 5

        print(f"[SUCCESS] Tool was executed {len(execution_log)} times with correct results")

        # 验证没有返回占位符
        result_str = str(result.result)
        assert (
            "Tool" not in result_str or "executed" not in result_str.lower()
        ), f"Result contains placeholder text: {result_str}"

    @pytest.mark.asyncio
    async def test_agent_executes_multiple_tools(self):
        """测试Agent执行多个工具"""
        # 1. 创建工具注册表
        tool_registry = ToolRegistry()

        # 使用execution_log跟踪工具执行
        execution_log = []

        async def add(a: int, b: int) -> int:
            """加法"""
            result = a + b
            execution_log.append({"tool": "add", "args": {"a": a, "b": b}, "result": result})
            return result

        async def multiply(a: int, b: int) -> int:
            """乘法"""
            result = a * b
            execution_log.append({"tool": "multiply", "args": {"a": a, "b": b}, "result": result})
            return result

        tool_registry.register_function(add)
        tool_registry.register_function(multiply)

        # 2. 创建MockLLM，返回多个tool_calls（不使用done工具）
        llm = MockLLMProvider(
            responses=[
                {"type": "text", "content": "First, I'll add 2 + 3..."},
                {"type": "tool_call", "name": "add", "arguments": {"a": 2, "b": 3}},
                {"type": "text", "content": "Now I'll multiply 4 * 5..."},
                {"type": "tool_call", "name": "multiply", "arguments": {"a": 4, "b": 5}},
                {"type": "text", "content": "Done!"},
            ]
        )

        # 3. 创建Agent
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "add",
                    "description": "Add two numbers",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "a": {"type": "integer"},
                            "b": {"type": "integer"},
                        },
                        "required": ["a", "b"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "multiply",
                    "description": "Multiply two numbers",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "a": {"type": "integer"},
                            "b": {"type": "integer"},
                        },
                        "required": ["a", "b"],
                    },
                },
            },
        ]

        agent = Agent(
            node_id="test-agent-multi",
            llm_provider=llm,
            tool_registry=tool_registry,
            tools=tools,
            require_done_tool=False,  # 不使用done工具，让Agent自然结束
        )

        # 4. 执行任务
        task = Task(
            task_id="test-task-002",
            action="execute",
            parameters={"content": "Calculate 2+3 and 4*5"},
        )

        result = await agent.execute_task(task)

        # 5. 验证结果
        assert result.status == TaskStatus.COMPLETED

        # 验证两个工具都被执行了（通过execution_log）
        print(f"\n[DEBUG] Execution log: {execution_log}")

        # 验证至少有两次工具调用
        assert (
            len(execution_log) >= 2
        ), f"Expected at least 2 tool executions, got {len(execution_log)}"

        # 验证add工具被调用
        add_calls = [log for log in execution_log if log["tool"] == "add"]
        assert len(add_calls) >= 1, "Expected add tool to be called at least once"
        assert add_calls[0]["args"] == {
            "a": 2,
            "b": 3,
        }, f"Expected add(2, 3), got {add_calls[0]['args']}"
        assert add_calls[0]["result"] == 5, f"Expected add result 5, got {add_calls[0]['result']}"

        # 验证multiply工具被调用
        multiply_calls = [log for log in execution_log if log["tool"] == "multiply"]
        assert len(multiply_calls) >= 1, "Expected multiply tool to be called at least once"
        assert multiply_calls[0]["args"] == {
            "a": 4,
            "b": 5,
        }, f"Expected multiply(4, 5), got {multiply_calls[0]['args']}"
        assert (
            multiply_calls[0]["result"] == 20
        ), f"Expected multiply result 20, got {multiply_calls[0]['result']}"

        print(
            f"[SUCCESS] Both tools were executed correctly: {len(execution_log)} total executions"
        )
