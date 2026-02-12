"""
LLMClientPool 连接池测试
"""

import threading

import pytest

from loom.providers.llm.client_pool import LLMClientPool, _freeze, _make_cache_key


@pytest.fixture(autouse=True)
def reset_pool():
    """每个测试前后重置单例"""
    LLMClientPool.reset()
    yield
    LLMClientPool.reset()


class FakeClient:
    """模拟 LLM 客户端"""

    def __init__(self, *, api_key=None, base_url=None, timeout=60, max_retries=3, **kwargs):
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.kwargs = kwargs


class AnotherFakeClient:
    """模拟另一种 LLM 客户端"""

    def __init__(self, *, api_key=None, base_url=None, timeout=60, max_retries=3, **kwargs):
        self.api_key = api_key


class TestLLMClientPool:
    def test_same_config_same_client(self):
        """相同配置返回同一实例"""
        pool = LLMClientPool.get_instance()
        c1 = pool.get_or_create(
            FakeClient,
            api_key="sk-1",
            base_url=None,
            timeout=60,
            max_retries=3,
        )
        c2 = pool.get_or_create(
            FakeClient,
            api_key="sk-1",
            base_url=None,
            timeout=60,
            max_retries=3,
        )
        assert c1 is c2

    def test_different_api_key_different_client(self):
        """不同 api_key 返回不同实例"""
        pool = LLMClientPool.get_instance()
        c1 = pool.get_or_create(
            FakeClient,
            api_key="sk-1",
            base_url=None,
            timeout=60,
            max_retries=3,
        )
        c2 = pool.get_or_create(
            FakeClient,
            api_key="sk-2",
            base_url=None,
            timeout=60,
            max_retries=3,
        )
        assert c1 is not c2

    def test_different_base_url_different_client(self):
        """不同 base_url 返回不同实例"""
        pool = LLMClientPool.get_instance()
        c1 = pool.get_or_create(
            FakeClient,
            api_key="sk-1",
            base_url=None,
            timeout=60,
            max_retries=3,
        )
        c2 = pool.get_or_create(
            FakeClient,
            api_key="sk-1",
            base_url="https://custom.api",
            timeout=60,
            max_retries=3,
        )
        assert c1 is not c2

    def test_pool_size(self):
        """验证池大小"""
        pool = LLMClientPool.get_instance()
        assert pool.pool_size == 0

        pool.get_or_create(FakeClient, api_key="sk-1", base_url=None, timeout=60, max_retries=3)
        assert pool.pool_size == 1

        pool.get_or_create(FakeClient, api_key="sk-2", base_url=None, timeout=60, max_retries=3)
        assert pool.pool_size == 2

        # Same config → no new entry
        pool.get_or_create(FakeClient, api_key="sk-1", base_url=None, timeout=60, max_retries=3)
        assert pool.pool_size == 2

    def test_clear_pool(self):
        """清空连接池"""
        pool = LLMClientPool.get_instance()
        pool.get_or_create(FakeClient, api_key="sk-1", base_url=None, timeout=60, max_retries=3)
        assert pool.pool_size == 1
        pool.clear()
        assert pool.pool_size == 0

    def test_reset_singleton(self):
        """重置单例"""
        pool1 = LLMClientPool.get_instance()
        pool1.get_or_create(FakeClient, api_key="sk-1", base_url=None, timeout=60, max_retries=3)

        LLMClientPool.reset()
        pool2 = LLMClientPool.get_instance()
        assert pool2.pool_size == 0
        assert pool1 is not pool2

    def test_different_client_class_no_collision(self):
        """不同 client_class 不冲突"""
        pool = LLMClientPool.get_instance()
        c1 = pool.get_or_create(
            FakeClient,
            api_key="sk-1",
            base_url=None,
            timeout=60,
            max_retries=3,
        )
        c2 = pool.get_or_create(
            AnotherFakeClient,
            api_key="sk-1",
            base_url=None,
            timeout=60,
            max_retries=3,
        )
        assert c1 is not c2
        assert pool.pool_size == 2

    def test_thread_safety(self):
        """多线程并发创建无崩溃"""
        pool = LLMClientPool.get_instance()
        results = []
        errors = []

        def create_client(key):
            try:
                c = pool.get_or_create(
                    FakeClient,
                    api_key=key,
                    base_url=None,
                    timeout=60,
                    max_retries=3,
                )
                results.append(c)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=create_client, args=(f"sk-{i}",)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert pool.pool_size == 20


class TestFreeze:
    def test_freeze_dict(self):
        result = _freeze({"b": 2, "a": 1})
        assert isinstance(result, tuple)
        # Sorted by key
        assert result == (("a", 1), ("b", 2))

    def test_freeze_list(self):
        result = _freeze([1, 2, 3])
        assert result == (1, 2, 3)

    def test_freeze_set(self):
        result = _freeze({1, 2})
        assert isinstance(result, frozenset)

    def test_freeze_nested(self):
        result = _freeze({"key": [1, {"nested": True}]})
        assert isinstance(result, tuple)

    def test_freeze_primitive(self):
        assert _freeze(42) == 42
        assert _freeze("hello") == "hello"
        assert _freeze(None) is None


class TestMakeCacheKey:
    def test_basic_key(self):
        key = _make_cache_key("AsyncOpenAI", "sk-1", None, 60, 3)
        assert key == ("AsyncOpenAI", "sk-1", None, 60, 3, ())

    def test_key_with_kwargs(self):
        key = _make_cache_key("AsyncOpenAI", "sk-1", None, 60, 3, org="my-org")
        assert ("org", "my-org") in key[-1]
