"""
Task Context Unit Tests

测试基于 Task 的上下文管理功能
"""

import pytest

from loom.memory.core import LoomMemory
from loom.memory.task_context import (
    ContextBudgeter,
    MemoryContextSource,
    MessageConverter,
)
from loom.memory.tokenizer import TokenCounter
from loom.protocol import Task, TaskStatus


class MockTokenCounter(TokenCounter):
    """Mock TokenCounter for testing"""

    def count(self, text: str) -> int:
        """Simple word-based token counting"""
        return len(text.split())

    def count_messages(self, messages: list[dict]) -> int:
        """Count tokens in messages"""
        total = 0
        for msg in messages:
            content = msg.get("content", "")
            total += self.count(content)
        return total


class TestMessageConverter:
    """测试 MessageConverter"""

    def test_convert_thinking_task(self):
        """测试转换思考任务"""
        converter = MessageConverter()

        task = Task(
            task_id="task-1",
            action="node.thinking",
            parameters={"content": "我在思考问题"},
        )

        message = converter.convert_task_to_message(task)

        assert message is not None
        assert message["role"] == "assistant"
        assert message["content"] == "我在思考问题"

    def test_convert_thinking_task_empty_content(self):
        """测试转换空内容的思考任务"""
        converter = MessageConverter()

        task = Task(
            task_id="task-1",
            action="node.thinking",
            parameters={},
        )

        message = converter.convert_task_to_message(task)

        assert message is None

    def test_convert_tool_call_task(self):
        """测试转换工具调用任务"""
        converter = MessageConverter()

        task = Task(
            task_id="task-1",
            action="node.tool_call",
            parameters={"tool_name": "test_tool", "tool_args": {"arg1": "value1"}},
        )

        message = converter.convert_task_to_message(task)

        assert message is not None
        assert message["role"] == "assistant"
        assert "test_tool" in message["content"]

    def test_convert_execute_task(self):
        """测试转换执行任务"""
        converter = MessageConverter()

        task = Task(
            task_id="task-1",
            action="execute",
            parameters={"content": "执行任务"},
        )

        message = converter.convert_task_to_message(task)

        assert message is not None
        assert message["role"] == "user"
        assert message["content"] == "执行任务"

    def test_convert_node_message_task(self):
        """测试转换节点消息"""
        converter = MessageConverter()

        task = Task(
            task_id="task-1",
            action="node.message",
            parameters={"content": "直接消息"},
        )

        message = converter.convert_task_to_message(task)

        assert message is not None
        assert message["role"] == "assistant"
        assert "直接消息" in message["content"]

    def test_convert_delegation_request_task(self):
        """测试转换委派请求"""
        converter = MessageConverter()

        task = Task(
            task_id="task-1",
            action="node.delegation_request",
            parameters={"subtask": "处理子任务"},
            source_agent="agent-1",
        )

        message = converter.convert_task_to_message(task)

        assert message is not None
        assert message["role"] == "assistant"
        assert "处理子任务" in message["content"]

    def test_convert_unknown_action(self):
        """测试转换未知动作"""
        converter = MessageConverter()

        task = Task(
            task_id="task-1",
            action="unknown_action",
            parameters={},
        )

        message = converter.convert_task_to_message(task)

        assert message is None

    def test_convert_tasks_to_messages(self):
        """测试批量转换任务"""
        converter = MessageConverter()

        tasks = [
            Task(
                task_id="task-1",
                action="node.thinking",
                parameters={"content": "思考1"},
            ),
            Task(
                task_id="task-2",
                action="execute",
                parameters={"content": "执行任务"},
            ),
            Task(
                task_id="task-3",
                action="unknown_action",
                parameters={},
            ),
        ]

        messages = converter.convert_tasks_to_messages(tasks)

        assert len(messages) == 2
        assert messages[0]["role"] == "assistant"
        assert messages[1]["role"] == "user"

    def test_convert_node_message_with_context_role(self):
        """测试带 context_role 的节点消息转换"""
        converter = MessageConverter()

        # 测试 system role
        task_system = Task(
            task_id="task-1",
            action="node.message",
            parameters={"content": "系统消息", "context_role": "system"},
        )
        message_system = converter.convert_task_to_message(task_system)
        assert message_system["role"] == "system"
        assert message_system["content"] == "系统消息"

        # 测试 user role
        task_user = Task(
            task_id="task-2",
            action="node.message",
            parameters={"content": "用户消息", "context_role": "user"},
        )
        message_user = converter.convert_task_to_message(task_user)
        assert message_user["role"] == "user"
        assert message_user["content"] == "用户消息"

    def test_convert_delegation_response(self):
        """测试转换委派响应"""
        converter = MessageConverter()

        task = Task(
            task_id="task-1",
            action="node.delegation_response",
            parameters={"result": "任务完成"},
            source_agent="agent-2",
        )

        message = converter.convert_task_to_message(task)

        assert message is not None
        assert message["role"] == "assistant"
        assert "任务完成" in message["content"]
        assert "agent-2" in message["content"]

    def test_convert_planning_task(self):
        """测试转换规划任务"""
        converter = MessageConverter()

        task = Task(
            task_id="task-1",
            action="node.planning",
            parameters={
                "goal": "完成项目",
                "steps": ["步骤1", "步骤2", "步骤3"],
                "reasoning": "这是最优方案",
            },
        )

        message = converter.convert_task_to_message(task)

        assert message is not None
        assert message["role"] == "system"
        assert "完成项目" in message["content"]
        assert "步骤1" in message["content"]
        assert "这是最优方案" in message["content"]

    def test_convert_execute_task_empty_content(self):
        """测试转换空内容的执行任务"""
        converter = MessageConverter()

        task = Task(
            task_id="task-1",
            action="execute",
            parameters={},
        )

        message = converter.convert_task_to_message(task)

        assert message is None


class TestMemoryContextSource:
    """测试 MemoryContextSource"""

    @pytest.mark.asyncio
    async def test_get_context(self):
        """测试获取上下文"""
        memory = LoomMemory(node_id="test-node")

        # 添加一些任务到记忆
        task1 = Task(
            task_id="task-1",
            action="test_action",
            parameters={"content": "任务1"},
        )
        task1.status = TaskStatus.COMPLETED
        memory.add_task(task1)

        task2 = Task(
            task_id="task-2",
            action="test_action",
            parameters={"content": "任务2"},
        )
        task2.status = TaskStatus.COMPLETED
        memory.add_task(task2)

        source = MemoryContextSource(memory)
        current_task = Task(task_id="current", action="test")

        context = await source.get_context(current_task, max_items=10)

        assert len(context) > 0
        assert any(t.task_id == "task-1" or t.task_id == "task-2" for t in context)

    @pytest.mark.asyncio
    async def test_get_context_respects_max_items(self):
        """测试遵守最大数量限制"""
        memory = LoomMemory(node_id="test-node")

        # 添加多个任务
        for i in range(10):
            task = Task(
                task_id=f"task-{i}",
                action="test_action",
                parameters={"content": f"任务{i}"},
            )
            task.status = TaskStatus.COMPLETED
            memory.add_task(task)

        source = MemoryContextSource(memory)
        current_task = Task(task_id="current", action="test")

        context = await source.get_context(current_task, max_items=5)

        assert len(context) <= 5


class TestContextBudgeter:
    """测试 ContextBudgeter"""

    def test_init_default_config(self):
        """测试默认配置初始化"""
        counter = MockTokenCounter()
        budgeter = ContextBudgeter(counter, max_tokens=4000)

        assert budgeter.max_tokens == 4000
        assert budgeter.config.l1_ratio > 0
        assert budgeter.config.l2_ratio > 0
        assert budgeter.config.l3_l4_ratio > 0

    def test_normalize_config(self):
        """测试配置归一化"""
        from loom.memory.task_context import BudgetConfig

        counter = MockTokenCounter()
        config = BudgetConfig(l1_ratio=0.6, l2_ratio=0.3, l3_l4_ratio=0.1)
        budgeter = ContextBudgeter(counter, config=config)

        # 比例应该被归一化
        total = budgeter.config.l1_ratio + budgeter.config.l2_ratio + budgeter.config.l3_l4_ratio
        assert abs(total - 1.0) < 0.01

    def test_allocate_budget_basic(self):
        """测试基本预算分配"""
        counter = MockTokenCounter()
        budgeter = ContextBudgeter(counter, max_tokens=4000)

        allocation = budgeter.allocate_budget(system_prompt_tokens=500)

        assert allocation.system_tokens == 500
        assert allocation.l1_tokens > 0
        assert allocation.l2_tokens > 0
        assert allocation.l3_l4_tokens > 0
        assert allocation.total <= 4000 - 500

    def test_allocate_budget_no_space(self):
        """测试没有可用空间时的预算分配"""
        counter = MockTokenCounter()
        budgeter = ContextBudgeter(counter, max_tokens=1000)

        allocation = budgeter.allocate_budget(system_prompt_tokens=1500)

        assert allocation.system_tokens == 1500
        assert allocation.l1_tokens == 0
        assert allocation.l2_tokens == 0
        assert allocation.l3_l4_tokens == 0

    def test_budget_allocation_total_property(self):
        """测试 BudgetAllocation.total 属性"""
        from loom.memory.task_context import BudgetAllocation

        allocation = BudgetAllocation(
            l1_tokens=100, l2_tokens=200, l3_l4_tokens=150, eventbus_tokens=50, system_tokens=500
        )

        assert allocation.total == 500  # 不包括 system_tokens

    def test_rank_events_empty_list(self):
        """测试空事件列表排序"""
        counter = MockTokenCounter()
        budgeter = ContextBudgeter(counter)
        current_task = Task(task_id="current", action="execute", parameters={"content": "test"})

        candidates = budgeter.rank_events([], current_task)

        assert len(candidates) == 0

    def test_rank_events_with_keywords(self):
        """测试带关键词的事件排序"""
        from datetime import UTC, datetime

        counter = MockTokenCounter()
        budgeter = ContextBudgeter(counter)

        # 创建测试事件
        event1 = Task(
            task_id="event-1",
            action="node.thinking",
            parameters={"content": "thinking about python programming"},
            created_at=datetime.now(UTC),
        )
        event2 = Task(
            task_id="event-2",
            action="execute",
            parameters={"content": "execute database query"},
            created_at=datetime.now(UTC),
        )

        current_task = Task(
            task_id="current", action="execute", parameters={"content": "python code"}
        )

        candidates = budgeter.rank_events(
            [event1, event2], current_task, keywords=["python", "code"]
        )

        assert len(candidates) == 2
        # event1 应该排在前面，因为包含 "python"
        assert candidates[0].task.task_id == "event-1"
        assert candidates[0].score > candidates[1].score

    def test_calc_time_score(self):
        """测试时间衰减分数计算"""
        from datetime import UTC, datetime, timedelta

        counter = MockTokenCounter()
        budgeter = ContextBudgeter(counter)

        now = datetime.now(UTC)
        recent_event = Task(
            task_id="recent", action="test", parameters={}, created_at=now - timedelta(minutes=5)
        )
        old_event = Task(
            task_id="old", action="test", parameters={}, created_at=now - timedelta(hours=5)
        )

        recent_score = budgeter._calc_time_score(recent_event, now)
        old_score = budgeter._calc_time_score(old_event, now)

        assert recent_score > old_score
        assert 0 <= recent_score <= 1
        assert 0 <= old_score <= 1

    def test_calc_action_score(self):
        """测试动作权重分数计算"""
        counter = MockTokenCounter()
        budgeter = ContextBudgeter(counter)

        thinking_task = Task(task_id="t1", action="node.thinking", parameters={})
        tool_task = Task(task_id="t2", action="node.tool_call", parameters={})
        unknown_task = Task(task_id="t3", action="unknown", parameters={})

        thinking_score = budgeter._calc_action_score(thinking_task)
        tool_score = budgeter._calc_action_score(tool_task)
        unknown_score = budgeter._calc_action_score(unknown_task)

        assert thinking_score == 1.0
        assert tool_score == 0.8
        assert unknown_score == 0.5

    def test_calc_relevance_score(self):
        """测试相关性分数计算"""
        counter = MockTokenCounter()
        budgeter = ContextBudgeter(counter)

        relevant_task = Task(
            task_id="t1", action="test", parameters={"content": "python programming code"}
        )
        irrelevant_task = Task(
            task_id="t2", action="test", parameters={"content": "database query"}
        )

        relevant_score = budgeter._calc_relevance_score(relevant_task, ["python", "code"])
        irrelevant_score = budgeter._calc_relevance_score(irrelevant_task, ["python", "code"])

        assert relevant_score > irrelevant_score

    def test_calc_node_score(self):
        """测试节点权重分数计算"""
        counter = MockTokenCounter()
        budgeter = ContextBudgeter(counter)

        parent_event = Task(task_id="e1", action="test", parameters={"node_id": "parent-node"})
        current_event = Task(task_id="e2", action="test", parameters={"node_id": "current-node"})
        other_event = Task(task_id="e3", action="test", parameters={"node_id": "other-node"})

        parent_score = budgeter._calc_node_score(parent_event, "current-node", "parent-node")
        current_score = budgeter._calc_node_score(current_event, "current-node", "parent-node")
        other_score = budgeter._calc_node_score(other_event, "current-node", "parent-node")

        assert parent_score == 1.0
        assert current_score == 0.8
        assert other_score == 0.5

    def test_fallback_keywords_english(self):
        """测试英文关键词提取"""
        counter = MockTokenCounter()
        budgeter = ContextBudgeter(counter)

        keywords = budgeter._fallback_keywords("The quick brown fox jumps over the lazy dog")

        assert "quick" in keywords
        assert "brown" in keywords
        assert "the" not in keywords  # stopword
        assert "a" not in keywords  # stopword

    def test_fallback_keywords_chinese(self):
        """测试中文关键词提取"""
        counter = MockTokenCounter()
        budgeter = ContextBudgeter(counter)

        keywords = budgeter._fallback_keywords("我在学习Python编程")

        assert len(keywords) > 0  # 应该提取出中文二/三元组


class TestMemoryScopeContextSource:
    """测试 MemoryScopeContextSource"""

    @pytest.mark.asyncio
    async def test_init_with_default_scopes(self):
        """测试默认作用域初始化"""
        from unittest.mock import AsyncMock

        from loom.memory.task_context import MemoryScopeContextSource

        mock_memory = AsyncMock()
        source = MemoryScopeContextSource(mock_memory)

        assert source.memory == mock_memory
        assert len(source.scopes) == 3  # INHERITED, SHARED, GLOBAL
        assert source.max_items == 6
        assert source.include_additional is True

    @pytest.mark.asyncio
    async def test_get_context_with_root_goal(self):
        """测试获取包含root goal的上下文"""
        from unittest.mock import AsyncMock

        from loom.memory.task_context import MemoryScopeContextSource

        mock_memory = AsyncMock()

        # Mock read to return root goal entry
        async def mock_read(entry_id):
            if entry_id == "root-goal-123":
                return type(
                    "Entry",
                    (),
                    {
                        "content": "Complete the project",
                        "scope": type("Scope", (), {"value": "shared"}),
                    },
                )()
            return None

        mock_memory.read = mock_read
        mock_memory.list_by_scope = AsyncMock(return_value=[])

        source = MemoryScopeContextSource(mock_memory, max_items=10, include_additional=False)

        current_task = Task(
            task_id="current",
            action="execute",
            parameters={"root_context_id": "root-goal-123", "content": "work on task"},
        )

        context = await source.get_context(current_task, max_items=10)

        assert len(context) >= 1
        # 应该包含root goal
        root_tasks = [t for t in context if "ROOT GOAL" in t.parameters.get("content", "")]
        assert len(root_tasks) == 1
        assert "Complete the project" in root_tasks[0].parameters["content"]

    @pytest.mark.asyncio
    async def test_get_context_with_parent_task(self):
        """测试获取包含parent task的上下文"""
        from unittest.mock import AsyncMock

        from loom.memory.task_context import MemoryScopeContextSource

        mock_memory = AsyncMock()

        async def mock_read(entry_id):
            if entry_id == "task:parent-123:content":
                return type(
                    "Entry",
                    (),
                    {
                        "content": "Parent task description",
                        "scope": type("Scope", (), {"value": "shared"}),
                    },
                )()
            return None

        mock_memory.read = mock_read
        mock_memory.list_by_scope = AsyncMock(return_value=[])

        source = MemoryScopeContextSource(mock_memory, max_items=10, include_additional=False)

        current_task = Task(
            task_id="current",
            action="execute",
            parent_task_id="parent-123",
            parameters={"content": "child task"},
        )

        context = await source.get_context(current_task, max_items=10)

        assert len(context) >= 1
        parent_tasks = [t for t in context if "PARENT TASK" in t.parameters.get("content", "")]
        assert len(parent_tasks) == 1

    @pytest.mark.asyncio
    async def test_extract_keywords(self):
        """测试关键词提取"""
        from unittest.mock import AsyncMock

        from loom.memory.task_context import MemoryScopeContextSource

        mock_memory = AsyncMock()
        source = MemoryScopeContextSource(mock_memory)

        keywords = source._extract_keywords("The quick brown fox jumps over the lazy dog")

        assert "quick" in keywords
        assert "brown" in keywords
        assert "the" not in keywords  # stopword
        assert len(keywords) > 0

    @pytest.mark.asyncio
    async def test_score_entry(self):
        """测试条目评分"""
        from unittest.mock import AsyncMock

        from loom.fractal.memory import MemoryScope
        from loom.memory.task_context import MemoryScopeContextSource

        mock_memory = AsyncMock()
        source = MemoryScopeContextSource(mock_memory)

        keywords = {"python", "programming"}

        # 测试包含关键词的内容
        score1 = source._score_entry("python programming tutorial", keywords, MemoryScope.SHARED)
        # 测试不包含关键词的内容
        score2 = source._score_entry("database query optimization", keywords, MemoryScope.SHARED)

        assert score1 > score2

    @pytest.mark.asyncio
    async def test_get_context_empty_when_no_entries(self):
        """测试没有条目时返回空列表"""
        from unittest.mock import AsyncMock

        from loom.memory.task_context import MemoryScopeContextSource

        mock_memory = AsyncMock()
        mock_memory.read = AsyncMock(return_value=None)
        mock_memory.list_by_scope = AsyncMock(return_value=[])

        source = MemoryScopeContextSource(mock_memory, max_items=10, include_additional=False)

        current_task = Task(
            task_id="current", action="execute", parameters={"content": "test task"}
        )

        context = await source.get_context(current_task, max_items=10)

        # 没有条目时应该返回空列表
        assert isinstance(context, list)
        assert len(context) == 0

    @pytest.mark.asyncio
    async def test_score_entry_with_no_keywords(self):
        """测试无关键词时的评分"""
        from unittest.mock import AsyncMock

        from loom.fractal.memory import MemoryScope
        from loom.memory.task_context import MemoryScopeContextSource

        mock_memory = AsyncMock()
        source = MemoryScopeContextSource(mock_memory)

        score = source._score_entry("some content", set(), MemoryScope.SHARED)

        # 无关键词时应该返回scope权重
        assert score > 0

    @pytest.mark.asyncio
    async def test_score_entry_length_penalty(self):
        """测试长内容的惩罚"""
        from unittest.mock import AsyncMock

        from loom.fractal.memory import MemoryScope
        from loom.memory.task_context import MemoryScopeContextSource

        mock_memory = AsyncMock()
        source = MemoryScopeContextSource(mock_memory)

        keywords = {"test"}
        short_content = "test content"
        long_content = "test " + "x" * 500  # 超过400字符

        score_short = source._score_entry(short_content, keywords, MemoryScope.SHARED)
        score_long = source._score_entry(long_content, keywords, MemoryScope.SHARED)

        # 长内容应该有惩罚，分数更低
        assert score_short > score_long
