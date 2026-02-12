"""SharedPoolSource 单元测试"""

import pytest

from loom.context.sources.shared_pool import SharedPoolSource
from loom.memory.shared_pool import SharedMemoryPool
from loom.memory.tokenizer import EstimateCounter


@pytest.fixture
def counter():
    return EstimateCounter()


@pytest.fixture
def pool():
    return SharedMemoryPool(pool_id="src-test")


@pytest.mark.asyncio
async def test_source_name(pool: SharedMemoryPool):
    source = SharedPoolSource(pool)
    assert source.source_name == "shared_pool"


@pytest.mark.asyncio
async def test_collect_empty(pool: SharedMemoryPool, counter: EstimateCounter):
    source = SharedPoolSource(pool)
    blocks = await source.collect("query", token_budget=1000, token_counter=counter)
    assert blocks == []


@pytest.mark.asyncio
async def test_collect_returns_blocks(pool: SharedMemoryPool, counter: EstimateCounter):
    await pool.write("finding", "The sky is blue", writer_id="agent-a")
    await pool.write("result", "Water is wet", writer_id="agent-b")

    source = SharedPoolSource(pool)
    blocks = await source.collect("query", token_budget=5000, token_counter=counter)
    assert len(blocks) == 2
    # 最新的优先级最高
    assert blocks[0].priority > blocks[1].priority


@pytest.mark.asyncio
async def test_collect_respects_budget(pool: SharedMemoryPool, counter: EstimateCounter):
    # 写入大量数据
    for i in range(50):
        await pool.write(f"key-{i}", f"content-{i}" * 20, writer_id="agent")

    source = SharedPoolSource(pool)
    # 给很小的预算
    blocks = await source.collect("query", token_budget=100, token_counter=counter)
    # 应该被截断
    assert len(blocks) < 50


@pytest.mark.asyncio
async def test_block_metadata(pool: SharedMemoryPool, counter: EstimateCounter):
    await pool.write("k1", "v1", writer_id="agent-x")

    source = SharedPoolSource(pool)
    blocks = await source.collect("query", token_budget=5000, token_counter=counter)
    assert len(blocks) == 1

    meta = blocks[0].metadata
    assert meta["pool_id"] == "src-test"
    assert meta["key"] == "k1"
    assert meta["version"] == 1
    assert meta["writer"] == "agent-x"


@pytest.mark.asyncio
async def test_collect_with_prefix(pool: SharedMemoryPool, counter: EstimateCounter):
    await pool.write("ns:a", "data-a")
    await pool.write("ns:b", "data-b")
    await pool.write("other:c", "data-c")

    source = SharedPoolSource(pool, prefix="ns:")
    blocks = await source.collect("query", token_budget=5000, token_counter=counter)
    assert len(blocks) == 2
    assert all("[SHARED:ns:" in b.content for b in blocks)
