"""
Tests for BGE Embedding Provider
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from loom.memory.embedding import BGEEmbeddingProvider


class TestBGEEmbeddingProvider:
    """Test BGEEmbeddingProvider class."""

    def test_initialization(self):
        """Test BGEEmbeddingProvider initialization."""
        provider = BGEEmbeddingProvider(
            model_name="BAAI/bge-small-zh-v1.5",
            use_onnx=True,
            use_quantization=True
        )

        assert provider.model_name == "BAAI/bge-small-zh-v1.5"
        assert provider.use_onnx is True
        assert provider.use_quantization is True
        assert provider.dimension == 512

    def test_initialization_custom_params(self):
        """Test initialization with custom parameters."""
        provider = BGEEmbeddingProvider(
            model_name="custom-model",
            use_onnx=False,
            use_quantization=False,
            cache_dir="/tmp/cache"
        )

        assert provider.model_name == "custom-model"
        assert provider.use_onnx is False
        assert provider.use_quantization is False
        assert provider.cache_dir == "/tmp/cache"

    @pytest.mark.asyncio
    async def test_embed_text_mock(self):
        """Test embed_text with mocked model."""
        provider = BGEEmbeddingProvider()

        # Mock the initialization and model
        with patch.object(provider, '_initialize'):
            provider._tokenizer = MagicMock()
            provider._model = MagicMock()

            # Mock tokenizer output
            mock_encoded = {
                'input_ids': MagicMock(),
                'attention_mask': MagicMock(),
            }
            mock_encoded['input_ids'].numpy = MagicMock(return_value=[[1, 2, 3]])
            mock_encoded['attention_mask'].numpy = MagicMock(return_value=[[1, 1, 1]])
            provider._tokenizer.return_value = mock_encoded

            # Mock model output
            import torch
            mock_output = MagicMock()
            mock_output.last_hidden_state = torch.randn(1, 3, 512)
            provider._model.return_value = mock_output

            # Mock attention mask for mean pooling
            mock_encoded['attention_mask'] = torch.ones(1, 3)

            # Test embed_text
            embedding = await provider.embed_text("test text")

            assert isinstance(embedding, list)
            assert len(embedding) == 512
            assert all(isinstance(x, float) for x in embedding)

    @pytest.mark.asyncio
    async def test_embed_batch_mock(self):
        """Test embed_batch with mocked model."""
        provider = BGEEmbeddingProvider()

        # Mock the initialization and model
        with patch.object(provider, '_initialize'):
            provider._tokenizer = MagicMock()
            provider._model = MagicMock()

            # Mock tokenizer output
            mock_encoded = {
                'input_ids': MagicMock(),
                'attention_mask': MagicMock(),
            }
            mock_encoded['input_ids'].numpy = MagicMock(return_value=[[1, 2, 3], [4, 5, 6]])
            mock_encoded['attention_mask'].numpy = MagicMock(return_value=[[1, 1, 1], [1, 1, 1]])
            provider._tokenizer.return_value = mock_encoded

            # Mock model output
            import torch
            mock_output = MagicMock()
            mock_output.last_hidden_state = torch.randn(2, 3, 512)
            provider._model.return_value = mock_output

            # Mock attention mask for mean pooling
            mock_encoded['attention_mask'] = torch.ones(2, 3)

            # Test embed_batch
            embeddings = await provider.embed_batch(["text1", "text2"])

            assert isinstance(embeddings, list)
            assert len(embeddings) == 2
            assert all(len(emb) == 512 for emb in embeddings)
            assert all(isinstance(x, float) for emb in embeddings for x in emb)

    def test_dimension_property(self):
        """Test dimension property."""
        provider = BGEEmbeddingProvider()
        assert provider.dimension == 512


@pytest.mark.asyncio
@pytest.mark.integration
class TestBGEEmbeddingIntegration:
    """Integration tests for BGE embedding (requires transformers)."""

    @pytest.mark.skipif(
        not pytest.importorskip("transformers", reason="transformers not installed"),
        reason="transformers not installed"
    )
    async def test_real_embedding(self):
        """Test real embedding generation (slow, requires model download)."""
        # This test is marked as integration and will be skipped in regular test runs
        provider = BGEEmbeddingProvider(
            model_name="BAAI/bge-small-zh-v1.5",
            use_onnx=False,  # Use PyTorch for simplicity in test
            use_quantization=False
        )

        # Test single text
        embedding = await provider.embed_text("Hello world")
        assert isinstance(embedding, list)
        assert len(embedding) == 512
        assert all(isinstance(x, float) for x in embedding)

        # Test batch
        embeddings = await provider.embed_batch(["Hello", "World"])
        assert len(embeddings) == 2
        assert all(len(emb) == 512 for emb in embeddings)

    @pytest.mark.skipif(
        not pytest.importorskip("transformers", reason="transformers not installed"),
        reason="transformers not installed"
    )
    async def test_chinese_text(self):
        """Test embedding generation for Chinese text."""
        provider = BGEEmbeddingProvider(
            model_name="BAAI/bge-small-zh-v1.5",
            use_onnx=False,
            use_quantization=False
        )

        # Test Chinese text
        embedding = await provider.embed_text("你好世界")
        assert isinstance(embedding, list)
        assert len(embedding) == 512

        # Test mixed Chinese and English
        embedding = await provider.embed_text("Hello 世界")
        assert isinstance(embedding, list)
        assert len(embedding) == 512
