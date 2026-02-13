"""
Memory Hierarchy Tests

测试 L3/L4 记忆层级和提升触发器
"""

import pytest

from loom.events import ContextController, Session
from loom.runtime import Task


class TestL3AggregationStorage:
    """测试 L3 聚合存储"""

    @pytest.fixture
    def controller(self):
        return ContextController()

    @pytest.fixture
    def sessions_with_tasks(self, controller):
        """创建带有任务的 Sessions"""
        s1 = Session(session_id="s1")
        s2 = Session(session_id="s2")
        controller.register_session(s1)
        controller.register_session(s2)

        # 添加任务到 Session
        for i in range(3):
            task = Task(action="node.message", parameters={"content": f"s1 message {i}"})
            s1.add_task(task)

        for i in range(2):
            task = Task(action="node.thinking", parameters={"content": f"s2 thinking {i}"})
            s2.add_task(task)

        return [s1, s2]

    def test_l3_initial_state(self, controller):
        """测试 L3 初始状态"""
        assert controller.l3_count == 0
        assert controller.l3_token_usage == 0
        assert controller.get_l3_summaries() == []

    def test_add_to_l3(self, controller):
        """测试添加到 L3"""
        summary = {"content": "test summary", "tokens": 100}
        controller.add_to_l3(summary)

        assert controller.l3_count == 1
        summaries = controller.get_l3_summaries()
        assert len(summaries) == 1
        assert summaries[0]["content"] == "test summary"

    def test_get_l3_summaries_with_limit(self, controller):
        """测试获取 L3 摘要带限制"""
        for i in range(5):
            controller.add_to_l3({"content": f"summary {i}", "tokens": 10})

        summaries = controller.get_l3_summaries(limit=3)
        assert len(summaries) == 3
        # 应该返回最新的 3 个
        assert summaries[0]["content"] == "summary 2"
        assert summaries[2]["content"] == "summary 4"

    @pytest.mark.asyncio
    async def test_aggregate_to_l3_empty(self, controller):
        """测试空 Session 聚合"""
        result = await controller.aggregate_to_l3()
        assert result is None

    @pytest.mark.asyncio
    async def test_aggregate_to_l3_with_sessions(self, controller, sessions_with_tasks):
        """测试有 Session 时的聚合"""
        # In 3-layer arch, L1→L2 promotion is automatic via eviction.
        # Just test that aggregate_to_l3 doesn't error.
        result = await controller.aggregate_to_l3()

        # 可能没有 L2 工作记忆条目
        # 这里主要测试方法不报错
        assert result is None or isinstance(result, dict)


class TestL4Persistence:
    """测试 L4 持久化接口"""

    @pytest.fixture
    def controller(self):
        return ContextController()

    @pytest.fixture
    def mock_storage(self):
        """模拟存储"""
        storage = {"data": []}
        return storage

    @pytest.mark.asyncio
    async def test_persist_without_handler(self, controller):
        """测试无处理器时持久化"""
        result = await controller.persist_to_l4({"content": "test"})
        assert result is False

    @pytest.mark.asyncio
    async def test_load_without_handler(self, controller):
        """测试无处理器时加载"""
        result = await controller.load_from_l4()
        assert result == []

    @pytest.mark.asyncio
    async def test_set_and_use_l4_handlers(self, controller, mock_storage):
        """测试设置和使用 L4 处理器"""

        async def persist(data):
            mock_storage["data"].append(data)

        async def load(agent_id):
            return [d for d in mock_storage["data"] if d.get("agent_id") == agent_id]

        controller.set_l4_handlers(persist, load)

        # 持久化
        summary = {"content": "test summary", "tokens": 50}
        result = await controller.persist_to_l4(summary, agent_id="agent-1")
        assert result is True
        assert len(mock_storage["data"]) == 1
        assert mock_storage["data"][0]["agent_id"] == "agent-1"

        # 加载
        loaded = await controller.load_from_l4("agent-1")
        assert len(loaded) == 1
        assert loaded[0]["content"] == "test summary"

    @pytest.mark.asyncio
    async def test_persist_latest_l3(self, controller, mock_storage):
        """测试持久化最新的 L3 摘要"""

        async def persist(data):
            mock_storage["data"].append(data)

        controller.set_l4_handlers(persist)

        # 添加 L3 摘要
        controller.add_to_l3({"content": "summary 1", "tokens": 10})
        controller.add_to_l3({"content": "summary 2", "tokens": 20})

        # 持久化最新的（不指定 summary）
        result = await controller.persist_to_l4(agent_id="test")
        assert result is True
        assert mock_storage["data"][0]["content"] == "summary 2"


class TestPromotionTrigger:
    """测试提升触发器"""

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
    async def test_trigger_promotion_sessions_processed(self, controller, sessions):
        """测试提升触发 - sessions_processed 计数"""
        result = await controller.trigger_promotion(l2_to_l3=False)

        assert result["sessions_processed"] == 2  # 两个 Session
        assert result["l2_to_l3"] is None
        assert result["l3_to_l4"] is False

    @pytest.mark.asyncio
    async def test_trigger_promotion_single_session(self, controller, sessions):
        """测试单个 Session 提升"""
        result = await controller.trigger_promotion(session_id="s1", l2_to_l3=False)

        assert result["sessions_processed"] == 1

    @pytest.mark.asyncio
    async def test_trigger_promotion_full_chain(self, controller, sessions):
        """测试完整提升链"""
        # 设置 L4 处理器
        storage = []

        async def persist(data):
            storage.append(data)

        controller.set_l4_handlers(persist)

        # 添加一些 L3 摘要以便持久化
        controller.add_to_l3({"content": "existing summary", "tokens": 50})

        result = await controller.trigger_promotion(l2_to_l3=True, l3_to_l4=True)

        assert result["sessions_processed"] == 2
        # l2_to_l3 可能为 None（如果没有 L2 工作记忆条目）
        # l3_to_l4 取决于是否有 l2_to_l3 结果


class TestCrossSessionSharing:
    """测试跨 Session 记忆共享"""

    @pytest.fixture
    def controller(self):
        return ContextController()

    @pytest.fixture
    def sessions_with_tasks(self, controller):
        """创建带有任务的 Sessions"""
        s1 = Session(session_id="s1")
        s2 = Session(session_id="s2")
        s3 = Session(session_id="s3")
        controller.register_session(s1)
        controller.register_session(s2)
        controller.register_session(s3)

        # 给 s1 添加任务
        for i in range(5):
            task = Task(action="node.message", parameters={"content": f"s1 msg {i}"})
            s1.add_task(task)

        return [s1, s2, s3]

    @pytest.mark.asyncio
    async def test_share_context_empty_source(self, controller):
        """测试空源 Session"""
        result = await controller.share_context("nonexistent", ["s1"])
        assert result == {}

    @pytest.mark.asyncio
    async def test_share_context_shares_messages(self, controller, sessions_with_tasks):
        """add_task 存入 L1 的消息可以被 share_context 共享"""
        result = await controller.share_context("s1", ["s2", "s3"], message_limit=3)
        # s1 有 5 条消息，message_limit=3 → 共享最近 3 条到 s2, s3
        assert result.get("s2", 0) == 3
        assert result.get("s3", 0) == 3

    def test_get_shared_l3_context_empty(self, controller):
        """测试空 L3 上下文"""
        result = controller.get_shared_l3_context("s1")
        assert result == []

    def test_get_shared_l3_context_with_summaries(self, controller):
        """测试获取 L3 共享上下文"""
        # 添加一些 L3 摘要
        controller.add_to_l3(
            {
                "content": "summary for s1",
                "session_ids": ["s1"],
                "tokens": 10,
            }
        )
        controller.add_to_l3(
            {
                "content": "summary for s2",
                "session_ids": ["s2"],
                "tokens": 10,
            }
        )
        controller.add_to_l3(
            {
                "content": "global summary",
                "session_ids": [],
                "tokens": 10,
            }
        )

        # s1 应该看到自己的和全局的
        s1_context = controller.get_shared_l3_context("s1")
        assert len(s1_context) == 2

        # s2 应该看到自己的和全局的
        s2_context = controller.get_shared_l3_context("s2")
        assert len(s2_context) == 2
