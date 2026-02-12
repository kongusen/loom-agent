"""SharedMemoryPool 单元测试"""

import asyncio

import pytest

from loom.memory.shared_pool import PoolEntry, SharedMemoryPool, VersionConflictError


@pytest.fixture
def pool():
    return SharedMemoryPool(pool_id="test-pool")


@pytest.mark.asyncio
async def test_write_and_read(pool: SharedMemoryPool):
    entry = await pool.write("key1", {"data": "hello"}, writer_id="agent-a")
    assert entry.key == "key1"
    assert entry.content == {"data": "hello"}
    assert entry.version == 1
    assert entry.created_by == "agent-a"

    result = await pool.read("key1")
    assert result is not None
    assert result.content == {"data": "hello"}


@pytest.mark.asyncio
async def test_version_increments(pool: SharedMemoryPool):
    await pool.write("k", "v1", writer_id="a")
    entry = await pool.write("k", "v2", writer_id="b")
    assert entry.version == 2
    assert entry.content == "v2"
    assert entry.created_by == "a"
    assert entry.updated_by == "b"


@pytest.mark.asyncio
async def test_read_nonexistent(pool: SharedMemoryPool):
    result = await pool.read("no-such-key")
    assert result is None


@pytest.mark.asyncio
async def test_delete(pool: SharedMemoryPool):
    await pool.write("k", "v")
    assert pool.size == 1
    deleted = await pool.delete("k")
    assert deleted is True
    assert pool.size == 0
    assert await pool.read("k") is None

    # delete nonexistent
    assert await pool.delete("k") is False


@pytest.mark.asyncio
async def test_list_entries_sorted(pool: SharedMemoryPool):
    await pool.write("a", 1)
    await pool.write("b", 2)
    await pool.write("c", 3)

    entries = await pool.list_entries()
    assert len(entries) == 3
    # 最新的在前
    assert entries[0].key == "c"
    assert entries[-1].key == "a"


@pytest.mark.asyncio
async def test_list_with_prefix(pool: SharedMemoryPool):
    await pool.write("research:topic1", "t1")
    await pool.write("research:topic2", "t2")
    await pool.write("plan:step1", "s1")

    entries = await pool.list_entries(prefix="research:")
    assert len(entries) == 2
    assert all(e.key.startswith("research:") for e in entries)


@pytest.mark.asyncio
async def test_optimistic_lock_success(pool: SharedMemoryPool):
    await pool.write("k", "v1")
    entry = await pool.write("k", "v2", expected_version=1)
    assert entry.version == 2


@pytest.mark.asyncio
async def test_optimistic_lock_conflict(pool: SharedMemoryPool):
    await pool.write("k", "v1")
    with pytest.raises(VersionConflictError) as exc_info:
        await pool.write("k", "v2", expected_version=99)
    assert exc_info.value.key == "k"
    assert exc_info.value.expected == 99
    assert exc_info.value.actual == 1


@pytest.mark.asyncio
async def test_concurrent_writes(pool: SharedMemoryPool):
    """并发写入不丢数据"""
    async def writer(i: int):
        await pool.write(f"key-{i}", f"value-{i}", writer_id=f"agent-{i}")

    await asyncio.gather(*(writer(i) for i in range(20)))
    assert pool.size == 20


@pytest.mark.asyncio
async def test_metadata_merge(pool: SharedMemoryPool):
    await pool.write("k", "v1", metadata={"source": "a"})
    entry = await pool.write("k", "v2", metadata={"quality": "high"})
    assert entry.metadata["source"] == "a"
    assert entry.metadata["quality"] == "high"


@pytest.mark.asyncio
async def test_event_emitted_on_write():
    """mock EventBus 验证事件发布"""
    class MockEventBus:
        def __init__(self):
            self.published = []

        async def publish(self, task, wait_result=False):
            self.published.append(task)

    bus = MockEventBus()
    pool = SharedMemoryPool(pool_id="evt-pool", event_bus=bus)
    await pool.write("k", "v", writer_id="agent-x")

    assert len(bus.published) == 1
    task = bus.published[0]
    assert task.action == "shared_pool.write"
    assert task.parameters["key"] == "k"
    assert task.parameters["writer"] == "agent-x"
