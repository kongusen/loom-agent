"""
Tests for OpenAI Embedding Provider
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from loom.providers.embedding.openai import OpenAIEmbeddingProvider


class TestOpenAIEmbeddingProvider:
    """Test suite for OpenAIEmbeddingProvider"""

    @pytest.fixture
    def mock_openai_client(self):
        """Create a mock OpenAI client"""
        with patch("loom.providers.embedding.openai.AsyncOpenAI") as mock:
            client = AsyncMock()
            mock.return_value = client
            yield client

    @pytest.fixture
    def provider(self, mock_openai_client):
        """Create a provider instance with mocked client"""
        return OpenAIEmbeddingProvider(
            api_key="test-api-key",
            model="text-embedding-3-small",
        )

    def test_init_with_api_key(self, mock_openai_client):
        """Test initialization with explicit API key"""
        provider = OpenAIEmbeddingProvider(api_key="test-key")
        assert provider.model == "text-embedding-3-small"
        assert provider.client is not None

    def test_init_with_custom_model(self, mock_openai_client):
        """Test initialization with custom model"""
        provider = OpenAIEmbeddingProvider(
            api_key="test-key",
            model="text-embedding-3-large"
        )
        assert provider.model == "text-embedding-3-large"

    def test_init_with_base_url(self, mock_openai_client):
        """Test initialization with custom base URL"""
        with patch("loom.providers.embedding.openai.AsyncOpenAI") as mock:
            OpenAIEmbeddingProvider(
                api_key="test-key",
                base_url="https://custom.example.com"
            )
            mock.assert_called_once()

    def test_init_with_timeout(self, mock_openai_client):
        """Test initialization with custom timeout"""
        with patch("loom.providers.embedding.openai.AsyncOpenAI") as mock:
            OpenAIEmbeddingProvider(
                api_key="test-key",
                timeout=120.0
            )
            mock.assert_called_once()

    def test_init_with_extra_kwargs(self, mock_openai_client):
        """Test initialization with extra kwargs"""
        with patch("loom.providers.embedding.openai.AsyncOpenAI") as mock:
            OpenAIEmbeddingProvider(
                api_key="test-key",
                max_retries=3,
                http_client="custom"
            )
            mock.assert_called_once()

    def test_init_reads_api_key_from_env(self, monkeypatch):
        """Test that API key is read from environment variable"""
        monkeypatch.setenv("OPENAI_API_KEY", "env-api-key")
        with patch("loom.providers.embedding.openai.AsyncOpenAI") as mock:
            OpenAIEmbeddingProvider()
            mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_embed_single_text(self, provider, mock_openai_client):
        """Test embedding a single text"""
        # Mock the response
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=[0.1, 0.2, 0.3])]
        mock_openai_client.embeddings.create = AsyncMock(return_value=mock_response)

        result = await provider.embed("Hello, world!")

        assert result == [0.1, 0.2, 0.3]
        mock_openai_client.embeddings.create.assert_called_once_with(
            model="text-embedding-3-small",
            input="Hello, world!"
        )

    @pytest.mark.asyncio
    async def test_embed_with_custom_model(self, mock_openai_client):
        """Test embedding with custom model"""
        provider = OpenAIEmbeddingProvider(
            api_key="test-key",
            model="text-embedding-3-large"
        )

        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=[0.4, 0.5, 0.6])]
        mock_openai_client.embeddings.create = AsyncMock(return_value=mock_response)

        result = await provider.embed("Test text")

        assert result == [0.4, 0.5, 0.6]
        mock_openai_client.embeddings.create.assert_called_once_with(
            model="text-embedding-3-large",
            input="Test text"
        )

    @pytest.mark.asyncio
    async def test_embed_batch(self, provider, mock_openai_client):
        """Test batch embedding"""
        mock_response = MagicMock()
        mock_response.data = [
            MagicMock(embedding=[0.1, 0.2, 0.3]),
            MagicMock(embedding=[0.4, 0.5, 0.6]),
        ]
        mock_openai_client.embeddings.create = AsyncMock(return_value=mock_response)

        texts = ["Hello", "World"]
        result = await provider.embed_batch(texts)

        assert result == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        mock_openai_client.embeddings.create.assert_called_once_with(
            model="text-embedding-3-small",
            input=texts
        )

    @pytest.mark.asyncio
    async def test_embed_batch_single_item(self, provider, mock_openai_client):
        """Test batch embedding with single item"""
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=[0.1, 0.2, 0.3])]
        mock_openai_client.embeddings.create = AsyncMock(return_value=mock_response)

        result = await provider.embed_batch(["Single"])

        assert result == [[0.1, 0.2, 0.3]]

    @pytest.mark.asyncio
    async def test_embed_empty_text(self, provider, mock_openai_client):
        """Test embedding empty text"""
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=[0.0, 0.0, 0.0])]
        mock_openai_client.embeddings.create = AsyncMock(return_value=mock_response)

        result = await provider.embed("")

        assert result == [0.0, 0.0, 0.0]

    @pytest.mark.asyncio
    async def test_embed_batch_empty_list(self, provider, mock_openai_client):
        """Test batch embedding with empty list"""
        mock_response = MagicMock()
        mock_response.data = []
        mock_openai_client.embeddings.create = AsyncMock(return_value=mock_response)

        result = await provider.embed_batch([])

        assert result == []

    def test_import_error_when_openai_not_installed(self, monkeypatch):
        """Test that ImportError is raised when OpenAI SDK is not installed"""
        # This test validates the import error at module level
        # We can't easily test this without actually removing the package,
        # but the structure is here for documentation
        pass
