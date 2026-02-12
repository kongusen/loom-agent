"""
Integration Tests for Unified Search System

覆盖：
1. Query tool routing + EventBus event recording (KnowledgeAction.SEARCH / SEARCH_RESULT)
2. Importance tag stripping + L2 immediate promote
3. MEMORY_GUIDANCE system prompt injection + query tool definition
"""

import asyncio

import pytest

from loom.agent import Agent
from loom.events.actions import KnowledgeAction
from loom.events.event_bus import EventBus
from loom.providers.llm.mock import MockLLMProvider
from loom.runtime import Task, TaskStatus

# ==================== Query Tool + EventBus ====================


class TestQueryToolEventBusIntegration:
    """Agent 调用 query 工具 → EventBus 记录 SEARCH / SEARCH_RESULT 事件"""

    @pytest.mark.asyncio
    async def test_query_publishes_search_and_result_events(self):
        """query 工具执行后，EventBus 应同时记录 SEARCH 和 SEARCH_RESULT"""
        event_bus = EventBus(debug_mode=True)

        llm = MockLLMProvider(
            responses=[
                {
                    "type": "tool_call",
                    "name": "query",
                    "arguments": {"query": "API认证", "scope": "memory"},
                },
            ]
        )

        agent = Agent(
            node_id="test-search-agent",
            llm_provider=llm,
            event_bus=event_bus,
            require_done_tool=False,
            max_iterations=1,
        )

        task = Task(
            taskId="search-int-001",
            action="execute",
            parameters={"content": "查询API认证"},
        )

        await agent.execute_task(task)
        await asyncio.sleep(0.1)  # let background tasks settle

        events = event_bus.get_recent_events(limit=100)
        search_events = [e for e in events if e.action == KnowledgeAction.SEARCH]
        result_events = [e for e in events if e.action == KnowledgeAction.SEARCH_RESULT]

        assert len(search_events) >= 1, f"Expected ≥1 SEARCH event, got {len(search_events)}"
        assert len(result_events) >= 1, f"Expected ≥1 SEARCH_RESULT event, got {len(result_events)}"

        # verify search event fields
        se = search_events[0]
        assert se.parameters["query"] == "API认证"
        assert se.parameters["scope"] == "memory"
        assert se.sourceAgent == "test-search-agent"

        # verify result event links back to search event
        re = result_events[0]
        assert re.status == TaskStatus.COMPLETED
        assert "formatted_output" in re.result
        assert re.parentTaskId == se.taskId

    @pytest.mark.asyncio
    async def test_query_result_event_contains_output(self):
        """SEARCH_RESULT 事件的 formatted_output 应为非空字符串"""
        event_bus = EventBus(debug_mode=True)

        llm = MockLLMProvider(
            responses=[
                {
                    "type": "tool_call",
                    "name": "query",
                    "arguments": {"query": "测试内容", "scope": "memory"},
                },
            ]
        )

        agent = Agent(
            node_id="test-agent-output",
            llm_provider=llm,
            event_bus=event_bus,
            require_done_tool=False,
            max_iterations=1,
        )

        # seed memory with a task so the search has something to find
        seed = Task(
            taskId="seed-001",
            action="测试内容",
            parameters={"content": "这是测试内容"},
        )
        agent.memory.add_task(seed)

        task = Task(
            taskId="search-int-002",
            action="execute",
            parameters={"content": "搜索测试内容"},
        )

        await agent.execute_task(task)
        await asyncio.sleep(0.1)

        events = event_bus.get_recent_events(limit=100)
        result_events = [e for e in events if e.action == KnowledgeAction.SEARCH_RESULT]
        assert len(result_events) >= 1

        output = result_events[0].result["formatted_output"]
        assert isinstance(output, str)
        assert len(output) > 0

    @pytest.mark.asyncio
    async def test_no_eventbus_still_works(self):
        """无 EventBus 时 query 工具仍正常执行（不发布事件）"""
        llm = MockLLMProvider(
            responses=[
                {
                    "type": "tool_call",
                    "name": "query",
                    "arguments": {"query": "test", "scope": "memory"},
                },
            ]
        )

        agent = Agent(
            node_id="test-no-bus",
            llm_provider=llm,
            require_done_tool=False,
            max_iterations=1,
        )

        task = Task(
            taskId="search-int-003",
            action="execute",
            parameters={"content": "test query"},
        )

        result = await agent.execute_task(task)
        assert result.status == TaskStatus.COMPLETED


# ==================== Importance Tag + L2 Promote ====================


class TestImportanceTagPromoteIntegration:
    """LLM 输出 <imp:X.X/> → 标记剥离 + L2 即时提升"""

    @pytest.mark.asyncio
    async def test_tag_stripped_and_promoted_to_l2(self):
        """<imp:0.8/> 标记被剥离，任务提升到 L2"""
        llm = MockLLMProvider(
            responses=[
                {"type": "text", "content": "建议使用OAuth2.0。<imp:0.8/>"},
            ]
        )

        agent = Agent(
            node_id="test-imp-agent",
            llm_provider=llm,
            require_done_tool=False,
            max_iterations=1,
        )

        task = Task(
            taskId="imp-int-001",
            action="execute",
            parameters={"content": "推荐认证方案"},
        )

        result = await agent.execute_task(task)

        # 1. tag stripped from output
        content = result.result.get("content", "")
        assert "<imp:" not in content
        assert "建议使用OAuth2.0。" in content

        # 2. importance recorded
        assert task.metadata.get("importance") == 0.8

        # 3. task in L2 (0.8 > threshold 0.6)
        l2_ids = {t.taskId for t in agent.memory.get_l2_tasks()}
        assert task.taskId in l2_ids, f"Task {task.taskId} should be in L2, got: {l2_ids}"

    @pytest.mark.asyncio
    async def test_no_tag_no_promote(self):
        """无 importance 标记 → 默认 0.5，不提升到 L2"""
        llm = MockLLMProvider(
            responses=[
                {"type": "text", "content": "这是普通回复。"},
            ]
        )

        agent = Agent(
            node_id="test-imp-agent-2",
            llm_provider=llm,
            require_done_tool=False,
            max_iterations=1,
        )

        task = Task(
            taskId="imp-int-002",
            action="execute",
            parameters={"content": "简单问答"},
        )

        await agent.execute_task(task)

        importance = task.metadata.get("importance", 0.5)
        assert importance <= 0.6, f"Expected importance ≤ 0.6 (no tag), got {importance}"

    @pytest.mark.asyncio
    async def test_tag_1_0_promotes(self):
        """<imp:1.0/> 最高重要性也能正确提升"""
        llm = MockLLMProvider(
            responses=[
                {"type": "text", "content": "关键决策<imp:1.0/>"},
            ]
        )

        agent = Agent(
            node_id="test-imp-max",
            llm_provider=llm,
            require_done_tool=False,
            max_iterations=1,
        )

        task = Task(
            taskId="imp-int-003",
            action="execute",
            parameters={"content": "关键决策"},
        )

        await agent.execute_task(task)

        assert task.metadata.get("importance") == 1.0
        l2_ids = {t.taskId for t in agent.memory.get_l2_tasks()}
        assert task.taskId in l2_ids

    @pytest.mark.asyncio
    async def test_importance_with_eventbus(self):
        """importance 提升 + EventBus 同时工作"""
        event_bus = EventBus(debug_mode=True)

        llm = MockLLMProvider(
            responses=[
                {"type": "text", "content": "重要结论<imp:0.9/>"},
            ]
        )

        agent = Agent(
            node_id="test-imp-bus",
            llm_provider=llm,
            event_bus=event_bus,
            require_done_tool=False,
            max_iterations=1,
        )

        task = Task(
            taskId="imp-int-004",
            action="execute",
            parameters={"content": "重要任务"},
        )

        result = await agent.execute_task(task)
        await asyncio.sleep(0.1)

        assert task.metadata["importance"] == 0.9
        assert result.status == TaskStatus.COMPLETED
        l2_ids = {t.taskId for t in agent.memory.get_l2_tasks()}
        assert task.taskId in l2_ids


# ==================== MEMORY_GUIDANCE + Tool Definition ====================


class TestMemoryGuidanceIntegration:
    """MEMORY_GUIDANCE 注入 + query 工具定义验证"""

    def test_system_prompt_contains_memory_guidance(self):
        """Agent 有 memory 时，system prompt 包含 MEMORY_GUIDANCE"""
        agent = Agent(
            node_id="test-guidance",
            llm_provider=MockLLMProvider(),
            require_done_tool=False,
        )

        assert "query" in agent.system_prompt
        assert "scope" in agent.system_prompt
        assert "<imp:" in agent.system_prompt
        assert "importance" in agent.system_prompt.lower()

    def test_query_tool_present_in_tool_list(self):
        """工具列表包含 query 工具"""
        agent = Agent(
            node_id="test-tools",
            llm_provider=MockLLMProvider(),
            require_done_tool=False,
        )

        names = [
            t["function"]["name"]
            for t in agent.all_tools
            if isinstance(t, dict) and "function" in t
        ]
        assert "query" in names

    def test_memory_only_query_has_layer_no_scope(self):
        """无知识库时，query 工具有 layer 参数但无 scope"""
        agent = Agent(
            node_id="test-params",
            llm_provider=MockLLMProvider(),
            require_done_tool=False,
        )

        query_tool = next(
            (
                t
                for t in agent.all_tools
                if isinstance(t, dict) and t.get("function", {}).get("name") == "query"
            ),
            None,
        )
        assert query_tool is not None

        props = query_tool["function"]["parameters"]["properties"]
        assert "query" in props
        assert "layer" in props
        assert "scope" not in props  # no knowledge bases → no scope

    def test_query_tool_layer_enum_values(self):
        """layer 参数的枚举值正确"""
        agent = Agent(
            node_id="test-layer-enum",
            llm_provider=MockLLMProvider(),
            require_done_tool=False,
        )

        query_tool = next(
            t
            for t in agent.all_tools
            if isinstance(t, dict) and t.get("function", {}).get("name") == "query"
        )
        layer_prop = query_tool["function"]["parameters"]["properties"]["layer"]
        assert set(layer_prop["enum"]) == {"auto", "l1", "l2", "l3", "l4"}
