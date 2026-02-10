"""
ContextController Distribution Tests

测试 Task 分发功能
"""

import pytest

from loom.events import ContextController, Session
from loom.events.context_controller import DistributionResult, DistributionStrategy
from loom.runtime import Task


class TestDistributionStrategy:
    """测试分发策略枚举"""

    def test_strategy_values(self):
        """测试策略值"""
        assert DistributionStrategy.BROADCAST == "broadcast"
        assert DistributionStrategy.TARGETED == "targeted"
        assert DistributionStrategy.FILTERED == "filtered"


class TestDistributionResult:
    """测试分发结果"""

    def test_empty_result(self):
        """测试空结果"""
        result = DistributionResult()
        assert result.success_count == 0
        assert result.failed_count == 0

    def test_with_success(self):
        """测试成功结果"""
        task = Task(action="test")
        result = DistributionResult(success={"s1": task})
        assert result.success_count == 1
        assert result.failed_count == 0


class TestBroadcast:
    """测试广播分发"""

    @pytest.fixture
    def controller(self):
        return ContextController()

    @pytest.fixture
    def sessions(self, controller):
        s1 = Session(session_id="s1")
        s2 = Session(session_id="s2")
        controller.register_session(s1)
        controller.register_session(s2)
        return [s1, s2]

    @pytest.mark.asyncio
    async def test_broadcast_to_all(self, controller, sessions):
        """测试广播到所有 Session"""
        task = Task(action="test")
        result = await controller.broadcast(task)

        assert result.success_count == 2
        assert result.failed_count == 0
