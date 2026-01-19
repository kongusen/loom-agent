"""
Tests for Memory Types
"""

from datetime import datetime

import pytest

from loom.memory.types import (
    Fact,
    FactType,
    MemoryQuery,
    MemoryStatus,
    MemoryTier,
    MemoryType,
    MemoryUnit,
    TaskSummary,
)


class TestMemoryTier:
    """Test suite for MemoryTier enum"""

    def test_memory_tier_values(self):
        """Test MemoryTier enum values"""
        assert MemoryTier.L1_RAW_IO.value == 1
        assert MemoryTier.L2_WORKING.value == 2
        assert MemoryTier.L3_SESSION.value == 3
        assert MemoryTier.L4_GLOBAL.value == 4


class TestMemoryType:
    """Test suite for MemoryType enum"""

    def test_memory_type_values(self):
        """Test MemoryType enum values"""
        assert MemoryType.MESSAGE.value == "message"
        assert MemoryType.THOUGHT.value == "thought"
        assert MemoryType.TOOL_CALL.value == "tool_call"
        assert MemoryType.TOOL_RESULT.value == "tool_result"
        assert MemoryType.PLAN.value == "plan"
        assert MemoryType.FACT.value == "fact"
        assert MemoryType.CONTEXT.value == "context"
        assert MemoryType.SUMMARY.value == "summary"


class TestMemoryStatus:
    """Test suite for MemoryStatus enum"""

    def test_memory_status_values(self):
        """Test MemoryStatus enum values"""
        assert MemoryStatus.ACTIVE.value == "active"
        assert MemoryStatus.ARCHIVED.value == "archived"
        assert MemoryStatus.EVICTED.value == "evicted"
        assert MemoryStatus.SUMMARIZED.value == "summarized"


class TestMemoryUnit:
    """Test suite for MemoryUnit class"""

    def test_memory_unit_creation(self):
        """Test creating a MemoryUnit instance"""
        memory = MemoryUnit(
            content="test content",
            type=MemoryType.MESSAGE,
            tier=MemoryTier.L1_RAW_IO,
        )

        assert memory.content == "test content"
        assert memory.type == MemoryType.MESSAGE
        assert memory.tier == MemoryTier.L1_RAW_IO
        assert memory.importance == 0.5

    def test_memory_unit_with_all_fields(self):
        """Test MemoryUnit with all fields"""
        memory = MemoryUnit(
            content="test",
            type=MemoryType.THOUGHT,
            tier=MemoryTier.L2_WORKING,
            importance=0.8,
            metadata={"key": "value"},
        )

        assert memory.importance == 0.8
        assert memory.metadata == {"key": "value"}

    def test_to_message_with_message_type_string(self):
        """Test to_message with MESSAGE type and string content"""
        memory = MemoryUnit(
            content="Hello world",
            type=MemoryType.MESSAGE,
            tier=MemoryTier.L1_RAW_IO,
        )

        result = memory.to_message()

        assert result == {"role": "user", "content": "Hello world"}

    def test_to_message_with_message_type_dict(self):
        """Test to_message with MESSAGE type and dict content"""
        memory = MemoryUnit(
            content={"key": "value"},
            type=MemoryType.MESSAGE,
            tier=MemoryTier.L1_RAW_IO,
        )

        result = memory.to_message()

        # Dict content converts keys and values to strings
        assert result == {"key": "value"}

    def test_to_message_with_message_type_other(self):
        """Test to_message with MESSAGE type and non-string/dict content"""
        memory = MemoryUnit(
            content=12345,
            type=MemoryType.MESSAGE,
            tier=MemoryTier.L1_RAW_IO,
        )

        result = memory.to_message()

        assert result["role"] == "system"
        assert result["content"] == "12345"

    def test_to_message_with_thought_type(self):
        """Test to_message with THOUGHT type"""
        memory = MemoryUnit(
            content="Thinking about something",
            type=MemoryType.THOUGHT,
            tier=MemoryTier.L2_WORKING,
        )

        result = memory.to_message()

        assert result["role"] == "assistant"
        assert "💭" in result["content"]
        assert "Thinking about something" in result["content"]

    def test_to_message_with_tool_call_type(self):
        """Test to_message with TOOL_CALL type"""
        memory = MemoryUnit(
            content="bash.run",
            type=MemoryType.TOOL_CALL,
            tier=MemoryTier.L1_RAW_IO,
        )

        result = memory.to_message()

        assert result["role"] == "assistant"
        assert "🔧" in result["content"]
        assert "Tool Call" in result["content"]

    def test_to_message_with_tool_result_type(self):
        """Test to_message with TOOL_RESULT type"""
        memory = MemoryUnit(
            content="Command completed",
            type=MemoryType.TOOL_RESULT,
            tier=MemoryTier.L1_RAW_IO,
        )

        result = memory.to_message()

        assert result["role"] == "system"
        assert "🔧" in result["content"]
        assert "Tool Result" in result["content"]

    def test_to_message_with_plan_type(self):
        """Test to_message with PLAN type"""
        memory = MemoryUnit(
            content="Step 1: Do this",
            type=MemoryType.PLAN,
            tier=MemoryTier.L2_WORKING,
        )

        result = memory.to_message()

        assert result["role"] == "assistant"
        assert "📋" in result["content"]
        assert "Plan" in result["content"]

    def test_to_message_with_fact_type(self):
        """Test to_message with FACT type"""
        memory = MemoryUnit(
            content="Python is a programming language",
            type=MemoryType.FACT,
            tier=MemoryTier.L4_GLOBAL,
        )

        result = memory.to_message()

        assert result["role"] == "system"
        assert "📚" in result["content"]
        assert "Fact" in result["content"]

    def test_to_message_with_summary_type(self):
        """Test to_message with SUMMARY type"""
        memory = MemoryUnit(
            content="Task completed successfully",
            type=MemoryType.SUMMARY,
            tier=MemoryTier.L3_SESSION,
        )

        result = memory.to_message()

        assert result["role"] == "system"
        assert "📝" in result["content"]
        assert "Summary" in result["content"]

    def test_to_message_with_context_type(self):
        """Test to_message with CONTEXT type (default case)"""
        memory = MemoryUnit(
            content="Some context",
            type=MemoryType.CONTEXT,
            tier=MemoryTier.L2_WORKING,
        )

        result = memory.to_message()

        assert result["role"] == "system"
        assert result["content"] == "Some context"

    def test_to_message_with_preformatted_message(self):
        """Test to_message when content is already a message dict"""
        memory = MemoryUnit(
            content={"role": "user", "content": "Already formatted"},
            type=MemoryType.MESSAGE,
            tier=MemoryTier.L1_RAW_IO,
        )

        result = memory.to_message()

        assert result == {"role": "user", "content": "Already formatted"}

    def test_to_message_with_preformatted_message_different_role(self):
        """Test to_message when content has role key"""
        memory = MemoryUnit(
            content={"role": "assistant", "content": "Response"},
            type=MemoryType.MESSAGE,
            tier=MemoryTier.L1_RAW_IO,
        )

        result = memory.to_message()

        assert result == {"role": "assistant", "content": "Response"}


class TestTaskSummary:
    """Test suite for TaskSummary"""

    def test_task_summary_creation(self):
        """Test creating TaskSummary"""
        summary = TaskSummary(
            task_id="task_1",
            action="test_action",
            param_summary="params: {}",
            result_summary="success",
        )

        assert summary.task_id == "task_1"
        assert summary.action == "test_action"
        assert summary.param_summary == "params: {}"
        assert summary.result_summary == "success"
        assert summary.tags == []
        assert summary.importance == 0.5

    def test_task_summary_with_tags(self):
        """Test TaskSummary with custom tags"""
        summary = TaskSummary(
            task_id="task_1",
            action="test_action",
            param_summary="params",
            result_summary="result",
            tags=["important", "user-request"],
        )

        assert summary.tags == ["important", "user-request"]

    def test_task_summary_with_importance(self):
        """Test TaskSummary with custom importance"""
        summary = TaskSummary(
            task_id="task_1",
            action="test_action",
            param_summary="params",
            result_summary="result",
            importance=0.9,
        )

        assert summary.importance == 0.9

    def test_task_summary_created_at(self):
        """Test TaskSummary has created_at timestamp"""
        before = datetime.now()
        summary = TaskSummary(
            task_id="task_1",
            action="test",
            param_summary="p",
            result_summary="r",
        )
        after = datetime.now()

        assert before <= summary.created_at <= after


class TestFactType:
    """Test suite for FactType enum"""

    def test_fact_type_values(self):
        """Test FactType enum values"""
        assert FactType.API_SCHEMA.value == "api_schema"
        assert FactType.USER_PREFERENCE.value == "user_preference"
        assert FactType.DOMAIN_KNOWLEDGE.value == "domain_knowledge"
        assert FactType.TOOL_USAGE.value == "tool_usage"
        assert FactType.ERROR_PATTERN.value == "error_pattern"
        assert FactType.BEST_PRACTICE.value == "best_practice"


class TestFact:
    """Test suite for Fact class"""

    def test_fact_creation(self):
        """Test creating a Fact"""
        fact = Fact(
            fact_id="fact_1",
            content="Python lists are mutable",
            fact_type=FactType.DOMAIN_KNOWLEDGE,
        )

        assert fact.fact_id == "fact_1"
        assert fact.content == "Python lists are mutable"
        assert fact.fact_type == FactType.DOMAIN_KNOWLEDGE
        assert fact.confidence == 0.8
        assert fact.source_task_ids == []
        assert fact.tags == []
        assert fact.access_count == 0

    def test_fact_with_source_tasks(self):
        """Test Fact with source task IDs"""
        fact = Fact(
            fact_id="fact_1",
            content="Test",
            fact_type=FactType.TOOL_USAGE,
            source_task_ids=["task_1", "task_2"],
        )

        assert fact.source_task_ids == ["task_1", "task_2"]

    def test_fact_with_custom_confidence(self):
        """Test Fact with custom confidence"""
        fact = Fact(
            fact_id="fact_1",
            content="Test",
            fact_type=FactType.BEST_PRACTICE,
            confidence=0.95,
        )

        assert fact.confidence == 0.95

    def test_fact_update_access(self):
        """Test update_access method"""
        fact = Fact(
            fact_id="fact_1",
            content="Test",
            fact_type=FactType.API_SCHEMA,
        )

        initial_count = fact.access_count
        initial_time = fact.last_accessed

        import time

        time.sleep(0.01)  # Small delay to ensure timestamp changes
        fact.update_access()

        assert fact.access_count == initial_count + 1
        assert fact.last_accessed > initial_time


class TestMemoryQuery:
    """Test suite for MemoryQuery"""

    def test_memory_query_defaults(self):
        """Test MemoryQuery with default values"""
        query = MemoryQuery(query="test query")

        assert query.query == "test query"
        assert query.tier is None
        assert query.type is None
        assert query.limit == 10
        assert query.min_importance == 0.0

    def test_memory_query_with_tier(self):
        """Test MemoryQuery with tier filter"""
        query = MemoryQuery(
            query="test",
            tier=MemoryTier.L2_WORKING,
        )

        assert query.tier == MemoryTier.L2_WORKING

    def test_memory_query_with_type(self):
        """Test MemoryQuery with type filter"""
        query = MemoryQuery(
            query="test",
            type=MemoryType.TOOL_CALL,
        )

        assert query.type == MemoryType.TOOL_CALL

    def test_memory_query_with_limit(self):
        """Test MemoryQuery with custom limit"""
        query = MemoryQuery(query="test", limit=50)

        assert query.limit == 50

    def test_memory_query_with_min_importance(self):
        """Test MemoryQuery with min importance"""
        query = MemoryQuery(query="test", min_importance=0.7)

        assert query.min_importance == 0.7

    def test_memory_query_with_all_parameters(self):
        """Test MemoryQuery with all parameters"""
        query = MemoryQuery(
            query="search query",
            tier=MemoryTier.L3_SESSION,
            type=MemoryType.MESSAGE,
            limit=100,
            min_importance=0.8,
        )

        assert query.query == "search query"
        assert query.tier == MemoryTier.L3_SESSION
        assert query.type == MemoryType.MESSAGE
        assert query.limit == 100
        assert query.min_importance == 0.8
