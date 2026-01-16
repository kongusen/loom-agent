"""
Tests for PostgreSQL Vector Store using mocks.
"""
from unittest.mock import AsyncMock, MagicMock

import pytest

from loom.memory.vector_store import PostgreSQLVectorStore


@pytest.fixture
def mock_asyncpg(mocker):
    """Mock asyncpg module."""
    mock = mocker.patch("asyncpg.create_pool", new_callable=AsyncMock)
    return mock

@pytest.fixture
def mock_pgvector(mocker):
    """Mock pgvector module."""
    mock = mocker.patch("pgvector.asyncpg.register_vector", new_callable=AsyncMock)
    return mock

@pytest.fixture
def mock_pool_connection():
    """Create a mock pool and connection."""
    pool = MagicMock() # Pool object itself isn't awaited, it's the result of create_pool
    connection = AsyncMock()

    # Configure pool.acquire() to act as an async context manager
    # async with pool.acquire() as conn:
    acquire_ctx = MagicMock()
    acquire_ctx.__aenter__.return_value = connection
    acquire_ctx.__aexit__.return_value = None

    pool.acquire.return_value = acquire_ctx
    return pool, connection

@pytest.mark.asyncio
class TestPostgreSQLVectorStore:

    async def test_initialization(self, mock_asyncpg, mock_pgvector, mock_pool_connection):
        """Test store initialization creates table and index."""
        pool, conn = mock_pool_connection
        mock_asyncpg.return_value = pool

        store = PostgreSQLVectorStore(
            connection_string="postgres://user:pass@localhost/db",
            table_name="test_memory"
        )

        # Trigger pool creation
        await store._get_pool()

        # Verify connection and pool creation
        mock_asyncpg.assert_called_once_with("postgres://user:pass@localhost/db")

        # Verify extension creation
        conn.execute.assert_any_call("CREATE EXTENSION IF NOT EXISTS vector")

        # Verify vector registration
        mock_pgvector.assert_called()

        # Verify table creation (partial match on SQL)
        # We check if execute was called with CREATE TABLE
        create_table_calls = [
            call for call in conn.execute.call_args_list
            if "CREATE TABLE IF NOT EXISTS test_memory" in call[0][0]
        ]
        assert len(create_table_calls) > 0

        # Verify index creation
        create_index_calls = [
            call for call in conn.execute.call_args_list
            if "CREATE INDEX IF NOT EXISTS test_memory_embedding_idx" in call[0][0]
        ]
        assert len(create_index_calls) > 0

    async def test_add_vector(self, mock_asyncpg, mock_pgvector, mock_pool_connection):
        """Test adding a vector."""
        pool, conn = mock_pool_connection
        mock_asyncpg.return_value = pool

        store = PostgreSQLVectorStore("postgres://...")

        await store.add(
            id="doc1",
            text="hello",
            embedding=[0.1, 0.2, 0.3],
            metadata={"source": "test"}
        )

        # Check INSERT query
        insert_calls = [
            call for call in conn.execute.call_args_list
            if "INSERT INTO loom_memory" in call[0][0]
        ]
        assert len(insert_calls) > 0

        # Check params
        args = insert_calls[0][0]
        assert args[1] == "doc1"
        assert args[2] == "hello"
        assert args[3] == [0.1, 0.2, 0.3]
        assert '"source": "test"' in args[4] # JSON dumped string

    async def test_search_vector(self, mock_asyncpg, mock_pgvector, mock_pool_connection):
        """Test searching vectors."""
        pool, conn = mock_pool_connection
        mock_asyncpg.return_value = pool

        # Mock search results
        # row needs to act like a dict/record
        mock_row = MagicMock()
        mock_row.__getitem__.side_effect = lambda k: {
            'id': 'doc1',
            'text': 'hello',
            'metadata': '{"source": "test"}',
            'distance': 0.1 # similarity = 0.9
        }[k]

        conn.fetch.return_value = [mock_row]

        store = PostgreSQLVectorStore("postgres://...")

        results = await store.search(
            query_embedding=[0.1, 0.2, 0.3],
            top_k=5,
            filter_metadata={"type": "chat"}
        )

        assert len(results) == 1
        assert results[0].id == "doc1"
        assert results[0].score == 0.9 # 1.0 - 0.1
        assert results[0].metadata == {"source": "test"}

        # Check SELECT query
        select_calls = [
            call for call in conn.fetch.call_args_list
            if "SELECT id, text, metadata" in call[0][0]
        ]
        assert len(select_calls) > 0

        # Check filter clause usage
        query = select_calls[0][0][0]
        assert "metadata->>'type' = $2" in query
        assert select_calls[0][0][2] == "chat"

    async def test_delete_vector(self, mock_asyncpg, mock_pgvector, mock_pool_connection):
        """Test deleting a vector."""
        pool, conn = mock_pool_connection
        mock_asyncpg.return_value = pool
        conn.execute.return_value = "DELETE 1"

        store = PostgreSQLVectorStore("postgres://...")
        result = await store.delete("doc1")

        assert result is True

        delete_calls = [
            call for call in conn.execute.call_args_list
            if "DELETE FROM loom_memory" in call[0][0]
        ]
        assert len(delete_calls) > 0
        assert delete_calls[0][0][1] == "doc1"

    async def test_update_vector(self, mock_asyncpg, mock_pgvector, mock_pool_connection):
        """Test updating a vector."""
        pool, conn = mock_pool_connection
        mock_asyncpg.return_value = pool
        conn.execute.return_value = "UPDATE 1"

        store = PostgreSQLVectorStore("postgres://...")

        await store.update(
            id="doc1",
            embedding=[0.9, 0.9, 0.9],
            metadata={"new": "val"}
        )

        update_calls = [
            call for call in conn.execute.call_args_list
            if "UPDATE loom_memory" in call[0][0]
        ]
        assert len(update_calls) > 0

        query = update_calls[0][0][0]
        assert "embedding = $2" in query
        assert "metadata = metadata || $3" in query

    async def test_get_vector(self, mock_asyncpg, mock_pgvector, mock_pool_connection):
        """Test getting a vector by ID."""
        pool, conn = mock_pool_connection
        mock_asyncpg.return_value = pool

        mock_row = MagicMock()
        mock_row.__getitem__.side_effect = lambda k: {
            'id': 'doc1',
            'metadata': '{"source": "test"}'
        }[k]

        conn.fetchrow.return_value = mock_row

        store = PostgreSQLVectorStore("postgres://...")
        result = await store.get("doc1")

        assert result is not None
        assert result.id == "doc1"
        assert result.metadata == {"source": "test"}

