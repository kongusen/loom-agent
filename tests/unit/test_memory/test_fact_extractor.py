"""
Fact Extractor Unit Tests

测试事实提取器的核心功能
"""

import pytest

from loom.memory.fact_extractor import FactExtractor
from loom.memory.types import FactType
from loom.protocol import Task, TaskStatus


class TestExtractApiFacts:
    """测试API事实提取"""

    @pytest.mark.asyncio
    async def test_extract_api_facts_with_endpoint_and_method(self):
        """测试提取API事实（有endpoint和method）"""
        extractor = FactExtractor()
        task = Task(
            task_id="task_1", action="api_call", parameters={"endpoint": "/users", "method": "GET"}
        )

        facts = await extractor.extract_facts(task)

        assert len(facts) == 1
        assert facts[0].fact_type == FactType.API_SCHEMA
        assert "/users" in facts[0].content
        assert "GET" in facts[0].content
        assert "api" in facts[0].tags

    @pytest.mark.asyncio
    async def test_extract_api_facts_without_parameters(self):
        """测试无参数时不提取API事实"""
        extractor = FactExtractor()
        task = Task(task_id="task_1", action="api_call", parameters={})

        facts = await extractor.extract_facts(task)

        assert len(facts) == 0


class TestExtractPreferenceFacts:
    """测试用户偏好事实提取"""

    @pytest.mark.asyncio
    async def test_extract_preference_facts_with_user_choice(self):
        """测试提取用户偏好事实"""
        extractor = FactExtractor()
        task = Task(
            task_id="task_1", action="user_interaction", parameters={"user_choice": "dark_mode"}
        )

        facts = await extractor.extract_facts(task)

        assert len(facts) == 1
        assert facts[0].fact_type == FactType.USER_PREFERENCE
        assert "dark_mode" in facts[0].content
        assert "preference" in facts[0].tags

    @pytest.mark.asyncio
    async def test_extract_preference_facts_without_choice(self):
        """测试无user_choice时不提取偏好事实"""
        extractor = FactExtractor()
        task = Task(task_id="task_1", action="user_interaction", parameters={})

        facts = await extractor.extract_facts(task)

        assert len(facts) == 0


class TestExtractToolFacts:
    """测试工具使用事实提取"""

    @pytest.mark.asyncio
    async def test_extract_tool_facts_with_tool_and_result(self):
        """测试提取工具使用事实"""
        extractor = FactExtractor()
        task = Task(
            task_id="task_1",
            action="tool_call",
            parameters={"tool": "calculator"},
            result={"output": "42"},
        )

        facts = await extractor.extract_facts(task)

        assert len(facts) == 1
        assert facts[0].fact_type == FactType.TOOL_USAGE
        assert "calculator" in facts[0].content
        assert "tool" in facts[0].tags

    @pytest.mark.asyncio
    async def test_extract_tool_facts_without_result(self):
        """测试无result时不提取工具事实"""
        extractor = FactExtractor()
        task = Task(task_id="task_1", action="tool_call", parameters={"tool": "calculator"})

        facts = await extractor.extract_facts(task)

        assert len(facts) == 0


class TestExtractErrorFacts:
    """测试错误模式事实提取"""

    @pytest.mark.asyncio
    async def test_extract_error_facts_with_failed_task(self):
        """测试提取错误事实"""
        extractor = FactExtractor()
        task = Task(
            task_id="task_1",
            action="api_call",
            status=TaskStatus.FAILED,
            error="Connection timeout",
        )

        facts = await extractor.extract_facts(task)

        assert len(facts) == 1
        assert facts[0].fact_type == FactType.ERROR_PATTERN
        assert "Connection timeout" in facts[0].content
        assert "error" in facts[0].tags

    @pytest.mark.asyncio
    async def test_extract_error_facts_without_error(self):
        """测试无error时不提取错误事实"""
        extractor = FactExtractor()
        task = Task(task_id="task_1", action="api_call", status=TaskStatus.FAILED)

        facts = await extractor.extract_facts(task)

        assert len(facts) == 0


class TestExtractMultipleFacts:
    """测试提取多种类型的事实"""

    @pytest.mark.asyncio
    async def test_extract_multiple_fact_types(self):
        """测试同时提取多种类型的事实"""
        extractor = FactExtractor()
        task = Task(
            task_id="task_1",
            action="api_call_with_user_interaction",
            parameters={"endpoint": "/users", "method": "POST", "user_choice": "json_format"},
            status=TaskStatus.FAILED,
            error="Invalid request",
        )

        facts = await extractor.extract_facts(task)

        # 应该提取3种事实：API、用户偏好、错误
        assert len(facts) == 3
        fact_types = {f.fact_type for f in facts}
        assert FactType.API_SCHEMA in fact_types
        assert FactType.USER_PREFERENCE in fact_types
        assert FactType.ERROR_PATTERN in fact_types
