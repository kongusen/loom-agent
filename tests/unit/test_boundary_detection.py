"""测试边界检测"""

import pytest

from loom.agent import Agent
from loom.agent.boundary import BoundaryType, BoundaryResponse
from loom.config import AgentConfig
from tests.conftest import MockLLMProvider


class TestBoundaryDetection:
    """验证边界检测器"""

    async def test_physical_boundary_context_full(self):
        """检测上下文满的物理边界"""
        agent = Agent(provider=MockLLMProvider([]), config=AgentConfig())

        # 模拟上下文接近满（decay > 0.9）
        agent.partition_mgr.partitions["history"].tokens = 120000  # 120k/128k = 0.9375

        boundary = agent.boundary_detector.detect()

        assert boundary is not None
        assert boundary[0] == BoundaryType.PHYSICAL
        assert "context_full" in boundary[1]["reason"]

    async def test_physical_boundary_quota_exceeded(self):
        """检测资源配额超限的物理边界"""
        agent = Agent(provider=MockLLMProvider([]), config=AgentConfig())

        # 设置超配额
        agent.resource_guard._max_tokens = 100
        agent.resource_guard._used_tokens = 150

        boundary = agent.boundary_detector.detect()

        assert boundary is not None
        assert boundary[0] == BoundaryType.PHYSICAL

    async def test_no_boundary_when_normal(self):
        """正常情况下不检测到边界"""
        agent = Agent(provider=MockLLMProvider([]), config=AgentConfig())

        boundary = agent.boundary_detector.detect()

        assert boundary is None

    async def test_boundary_handler_renew(self):
        """验证边界处理器可以执行 renew"""
        agent = Agent(provider=MockLLMProvider([]), config=AgentConfig())

        # 模拟可以续存的情况
        agent.partition_mgr.partitions["history"].tokens = 115000

        response = await agent.boundary_handler.handle(
            BoundaryType.PHYSICAL, {"reason": "context_full"}
        )

        assert response == BoundaryResponse.RENEW
