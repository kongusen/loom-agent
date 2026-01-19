"""
State Store Unit Tests

测试状态存储的功能
"""

import pytest

from loom.runtime.state_store import MemoryStateStore, StateStore


class TestStateStoreABC:
    """测试 StateStore 抽象基类"""

    def test_state_store_is_abstract(self):
        """测试 StateStore 不能直接实例化"""
        with pytest.raises(TypeError):
            StateStore()


class TestMemoryStateStoreInit:
    """测试 MemoryStateStore 初始化"""

    def test_init(self):
        """测试默认初始化"""
        store = MemoryStateStore()

        assert store._store == {}


class TestMemoryStateStoreSet:
    """测试 MemoryStateStore.save 方法"""

    @pytest.mark.asyncio
    async def test_save_new_key(self):
        """测试保存新键"""
        store = MemoryStateStore()
        await store.save("key1", "value1")

        assert store._store["key1"] == "value1"

    @pytest.mark.asyncio
    async def test_save_existing_key_overwrites(self):
        """测试覆盖已存在的键"""
        store = MemoryStateStore()
        await store.save("key1", "value1")
        await store.save("key1", "value2")

        assert store._store["key1"] == "value2"

    @pytest.mark.asyncio
    async def test_save_multiple_keys(self):
        """测试保存多个键"""
        store = MemoryStateStore()
        await store.save("key1", "value1")
        await store.save("key2", "value2")
        await store.save("key3", "value3")

        assert len(store._store) == 3
        assert store._store["key1"] == "value1"
        assert store._store["key2"] == "value2"
        assert store._store["key3"] == "value3"


class TestMemoryStateStoreGet:
    """测试 MemoryStateStore.get 方法"""

    @pytest.mark.asyncio
    async def test_get_existing_key(self):
        """测试获取存在的键"""
        store = MemoryStateStore()
        await store.save("key1", "value1")
        result = await store.get("key1")

        assert result == "value1"

    @pytest.mark.asyncio
    async def test_get_nonexistent_key(self):
        """测试获取不存在的键"""
        store = MemoryStateStore()
        result = await store.get("nonexistent")

        assert result is None


class TestMemoryStateStoreDelete:
    """测试 MemoryStateStore.delete 方法"""

    @pytest.mark.asyncio
    async def test_delete_existing_key(self):
        """测试删除存在的键"""
        store = MemoryStateStore()
        await store.save("key1", "value1")
        await store.delete("key1")

        assert "key1" not in store._store

    @pytest.mark.asyncio
    async def test_delete_nonexistent_key_no_error(self):
        """测试删除不存在的键不报错"""
        store = MemoryStateStore()
        # 应该不抛出异常
        await store.delete("nonexistent")

        assert store._store == {}


class TestMemoryStateStoreListKeys:
    """测试 MemoryStateStore.list_keys 方法"""

    @pytest.mark.asyncio
    async def test_list_keys_empty_store(self):
        """测试列出空存储的键"""
        store = MemoryStateStore()
        keys = await store.list_keys()

        assert keys == []

    @pytest.mark.asyncio
    async def test_list_keys_with_data(self):
        """测试列出有数据的存储的键"""
        store = MemoryStateStore()
        await store.save("key1", "value1")
        await store.save("key2", "value2")
        await store.save("key3", "value3")
        keys = await store.list_keys()

        assert len(keys) == 3
        assert "key1" in keys
        assert "key2" in keys
        assert "key3" in keys


class TestMemoryStateStoreClear:
    """测试 MemoryStateStore.clear 方法"""

    @pytest.mark.asyncio
    async def test_clear_empty_store(self):
        """测试清空空存储（触发line 109）"""
        store = MemoryStateStore()
        await store.clear()

        assert store._store == {}

    @pytest.mark.asyncio
    async def test_clear_with_data(self):
        """测试清空有数据的存储（触发line 109）"""
        store = MemoryStateStore()
        await store.save("key1", "value1")
        await store.save("key2", "value2")
        await store.clear()

        assert store._store == {}

    @pytest.mark.asyncio
    async def test_clear_then_add_new_data(self):
        """测试清空后添加新数据"""
        store = MemoryStateStore()
        await store.save("key1", "value1")
        await store.clear()
        await store.save("key2", "value2")

        assert store._store == {"key2": "value2"}
