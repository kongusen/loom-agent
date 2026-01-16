"""
Embedding Provider Abstraction
Allows users to plug in their preferred embedding service.
"""

import hashlib
from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    """
    Abstract base class for embedding providers.
    Users can implement this to use their preferred embedding service.
    """

    @abstractmethod
    async def embed_text(self, text: str) -> list[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Input text

        Returns:
            Embedding vector
        """
        pass

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for multiple texts (batch processing).

        Args:
            texts: List of input texts

        Returns:
            List of embedding vectors
        """
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the dimension of embeddings produced."""
        pass


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """
    OpenAI embedding provider.

    Usage:
        provider = OpenAIEmbeddingProvider(
            api_key="sk-...",
            model="text-embedding-3-small"
        )
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "text-embedding-3-small",
        dimensions: int | None = None,
    ):
        try:
            from openai import AsyncOpenAI
        except ImportError:
            raise ImportError("openai not installed. " "Install with: pip install openai") from None

        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self._dimensions = dimensions

        # Model dimension mapping
        self._model_dims = {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536,
        }

    async def embed_text(self, text: str) -> list[float]:
        import openai

        # Determine dimensions (use NOT_GIVEN if None)
        dims = self._dimensions or openai.NOT_GIVEN

        response = await self.client.embeddings.create(
            input=text,
            model=self.model,
            dimensions=dims,  # type: ignore
        )
        return response.data[0].embedding

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts (batch processing)."""
        import openai

        # Determine dimensions (use NOT_GIVEN if None)
        dims = self._dimensions or openai.NOT_GIVEN

        response = await self.client.embeddings.create(
            input=texts,
            model=self.model,
            dimensions=dims,  # type: ignore
        )
        return [item.embedding for item in response.data]

    @property
    def dimension(self) -> int:
        if self._dimensions:
            return self._dimensions
        return self._model_dims.get(self.model, 1536)


class CachedEmbeddingProvider(EmbeddingProvider):
    """
    Wrapper that adds caching to any embedding provider.
    Useful to avoid redundant API calls for the same text.

    Usage:
        base_provider = OpenAIEmbeddingProvider()
        provider = CachedEmbeddingProvider(base_provider)
    """

    def __init__(self, base_provider: EmbeddingProvider, max_cache_size: int = 10000):
        self.base_provider = base_provider
        self.max_cache_size = max_cache_size
        self._cache: dict[str, list[float]] = {}

    async def embed_text(self, text: str) -> list[float]:
        cache_key = self._get_cache_key(text)

        if cache_key in self._cache:
            return self._cache[cache_key]

        embedding = await self.base_provider.embed_text(text)

        # Add to cache with LRU eviction
        if len(self._cache) >= self.max_cache_size:
            # Remove oldest entry (simple FIFO for now)
            self._cache.pop(next(iter(self._cache)))

        self._cache[cache_key] = embedding
        return embedding

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        results = []
        uncached_texts = []
        uncached_indices = []

        # Check cache
        for i, text in enumerate(texts):
            cache_key = self._get_cache_key(text)
            if cache_key in self._cache:
                results.append(self._cache[cache_key])
            else:
                results.append([])  # Placeholder using empty list instead of None
                uncached_texts.append(text)
                uncached_indices.append(i)

        # Fetch uncached
        if uncached_texts:
            embeddings = await self.base_provider.embed_batch(uncached_texts)

            for idx, embedding in zip(uncached_indices, embeddings, strict=False):
                cache_key = self._get_cache_key(texts[idx])
                self._cache[cache_key] = embedding
                results[idx] = embedding

        return results

    @property
    def dimension(self) -> int:
        return self.base_provider.dimension

    def _get_cache_key(self, text: str) -> str:
        """Generate cache key from text."""
        return hashlib.md5(text.encode()).hexdigest()


class BGEEmbeddingProvider(EmbeddingProvider):
    """
    BGE (BAAI General Embedding) provider with ONNX Runtime optimization.

    Uses BAAI/bge-small-zh-v1.5 model with Int8 quantization for fast CPU inference.

    Performance:
    - Model size: ~25MB (Int8 quantized)
    - Latency: ~5ms per embedding (CPU)
    - 3-5x faster than PyTorch native

    Usage:
        provider = BGEEmbeddingProvider(
            model_name="BAAI/bge-small-zh-v1.5",
            use_onnx=True,
            use_quantization=True
        )
    """

    def __init__(
        self,
        model_name: str = "BAAI/bge-small-zh-v1.5",
        use_onnx: bool = True,
        use_quantization: bool = True,
        cache_dir: str | None = None,
    ):
        self.model_name = model_name
        self.use_onnx = use_onnx
        self.use_quantization = use_quantization
        self.cache_dir = cache_dir
        self._dimension = 512  # bge-small-zh-v1.5 dimension

        # Lazy loading - will be initialized on first use
        self._model = None
        self._tokenizer = None
        self._onnx_session = None

    def _initialize(self):
        """Lazy initialization of model and tokenizer."""
        if self._model is not None or self._onnx_session is not None:
            return

        try:
            from transformers import AutoModel, AutoTokenizer

            # Load tokenizer
            self._tokenizer = AutoTokenizer.from_pretrained(
                self.model_name, cache_dir=self.cache_dir
            )

            # Try ONNX Runtime optimization
            if self.use_onnx:
                try:
                    self._initialize_onnx()
                    return
                except Exception:
                    # Fallback to PyTorch if ONNX fails
                    pass

            # Fallback: Load PyTorch model
            self._model = AutoModel.from_pretrained(self.model_name, cache_dir=self.cache_dir)
            if self._model:
                self._model.eval()

        except ImportError:
            raise ImportError(
                "transformers not installed. " "Install with: pip install transformers torch"
            ) from None

    def _initialize_onnx(self):
        """Initialize ONNX Runtime session with optional quantization."""
        try:
            import os
            from pathlib import Path

            import onnxruntime as ort

            # Determine ONNX model path
            cache_dir = self.cache_dir or os.path.expanduser("~/.cache/loom/onnx")
            Path(cache_dir).mkdir(parents=True, exist_ok=True)

            model_safe_name = self.model_name.replace("/", "_")
            onnx_path = os.path.join(
                cache_dir, f"{model_safe_name}_{'int8' if self.use_quantization else 'fp32'}.onnx"
            )

            # Check if ONNX model already exists
            if not os.path.exists(onnx_path):
                # Convert PyTorch model to ONNX
                self._convert_to_onnx(onnx_path)

            # Create ONNX Runtime session
            sess_options = ort.SessionOptions()
            sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

            self._onnx_session = ort.InferenceSession(
                onnx_path, sess_options=sess_options, providers=["CPUExecutionProvider"]
            )

        except ImportError:
            raise ImportError(
                "onnxruntime not installed. " "Install with: pip install onnxruntime"
            ) from None

    def _convert_to_onnx(self, onnx_path: str):
        """Convert PyTorch model to ONNX format with optional quantization."""
        import os

        import torch
        from transformers import AutoModel

        # Load PyTorch model temporarily
        model = AutoModel.from_pretrained(self.model_name, cache_dir=self.cache_dir)
        model.eval()

        # Create dummy input
        dummy_input = {
            "input_ids": torch.randint(0, 1000, (1, 128)),
            "attention_mask": torch.ones(1, 128, dtype=torch.long),
            "token_type_ids": torch.zeros(1, 128, dtype=torch.long),
        }

        # Export to ONNX
        temp_onnx_path = onnx_path + ".tmp"
        torch.onnx.export(
            model,
            (dummy_input,),
            temp_onnx_path,
            input_names=["input_ids", "attention_mask", "token_type_ids"],
            output_names=["last_hidden_state"],
            dynamic_axes={
                "input_ids": {0: "batch", 1: "sequence"},
                "attention_mask": {0: "batch", 1: "sequence"},
                "token_type_ids": {0: "batch", 1: "sequence"},
                "last_hidden_state": {0: "batch", 1: "sequence"},
            },
            opset_version=14,
        )

        # Apply Int8 quantization if requested
        if self.use_quantization:
            try:
                from onnxruntime.quantization import QuantType, quantize_dynamic

                quantize_dynamic(temp_onnx_path, onnx_path, weight_type=QuantType.QInt8)
                os.remove(temp_onnx_path)
            except Exception:
                # If quantization fails, use unquantized version
                os.rename(temp_onnx_path, onnx_path)
        else:
            os.rename(temp_onnx_path, onnx_path)

    def _mean_pooling(self, token_embeddings, attention_mask):
        """Apply mean pooling to get sentence embedding."""
        import torch

        # Expand attention mask to match token embeddings dimensions
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()

        # Sum embeddings and divide by number of tokens
        sum_embeddings = torch.sum(token_embeddings * input_mask_expanded, 1)
        sum_mask = torch.clamp(input_mask_expanded.sum(1), min=1e-9)

        return sum_embeddings / sum_mask

    async def embed_text(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        self._initialize()

        # Prepare model/tokenizer
        if self._model is None and self._onnx_session is None:
            raise RuntimeError("Model not initialized")

        # Tokenize (assuming self._tokenizer is not None if _initialize passed)
        if self._tokenizer is None:
            raise RuntimeError("Tokenizer not initialized")

        encoded = self._tokenizer(
            text,
            padding=True,
            truncation=True,
            max_length=512,
            return_tensors="pt" if self._model else "np",
        )

        # Generate embedding
        if self._onnx_session:
            # ONNX Runtime inference
            import numpy as np

            onnx_inputs = {
                "input_ids": encoded["input_ids"].numpy(),
                "attention_mask": encoded["attention_mask"].numpy(),
                "token_type_ids": encoded.get(
                    "token_type_ids", np.zeros_like(encoded["input_ids"])
                ).numpy(),
            }

            outputs = self._onnx_session.run(None, onnx_inputs)
            token_embeddings = outputs[0]

            # Mean pooling
            attention_mask = encoded["attention_mask"].numpy()
            input_mask_expanded = np.expand_dims(attention_mask, -1)
            input_mask_expanded = np.broadcast_to(
                input_mask_expanded, token_embeddings.shape
            ).astype(float)

            sum_embeddings = np.sum(token_embeddings * input_mask_expanded, axis=1)
            sum_mask = np.clip(input_mask_expanded.sum(axis=1), a_min=1e-9, a_max=None)

            sentence_embedding = sum_embeddings / sum_mask
            embedding = sentence_embedding[0].tolist()

        else:
            # PyTorch inference
            import torch

            with torch.no_grad():
                outputs = self._model(**encoded)
                token_embeddings = outputs.last_hidden_state

                # Mean pooling
                sentence_embedding = self._mean_pooling(token_embeddings, encoded["attention_mask"])
                embedding = sentence_embedding[0].tolist()

        # Normalize embedding
        import math

        norm = math.sqrt(sum(x * x for x in embedding))
        if norm > 0:
            embedding = [x / norm for x in embedding]

        return embedding

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts (batch processing)."""
        self._initialize()

        # Prepare model/tokenizer
        if self._model is None and self._onnx_session is None:
            raise RuntimeError("Model not initialized")

        # Tokenize (assuming self._tokenizer is not None if _initialize passed)
        if self._tokenizer is None:
            raise RuntimeError("Tokenizer not initialized")

        # Tokenize batch
        encoded = self._tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=512,
            return_tensors="pt" if self._model else "np",
        )

        # Generate embeddings
        if self._onnx_session:
            # ONNX Runtime inference
            import numpy as np

            onnx_inputs = {
                "input_ids": encoded["input_ids"].numpy(),
                "attention_mask": encoded["attention_mask"].numpy(),
                "token_type_ids": encoded.get(
                    "token_type_ids", np.zeros_like(encoded["input_ids"])
                ).numpy(),
            }

            outputs = self._onnx_session.run(None, onnx_inputs)
            token_embeddings = outputs[0]

            # Mean pooling
            attention_mask = encoded["attention_mask"].numpy()
            input_mask_expanded = np.expand_dims(attention_mask, -1)
            input_mask_expanded = np.broadcast_to(
                input_mask_expanded, token_embeddings.shape
            ).astype(float)

            sum_embeddings = np.sum(token_embeddings * input_mask_expanded, axis=1)
            sum_mask = np.clip(input_mask_expanded.sum(axis=1), a_min=1e-9, a_max=None)

            sentence_embeddings = sum_embeddings / sum_mask
            embeddings = sentence_embeddings.tolist()

        else:
            # PyTorch inference
            import torch

            with torch.no_grad():
                outputs = self._model(**encoded)
                token_embeddings = outputs.last_hidden_state

                # Mean pooling
                sentence_embeddings = self._mean_pooling(
                    token_embeddings, encoded["attention_mask"]
                )
                embeddings = sentence_embeddings.tolist()

        # Normalize embeddings
        import math

        normalized_embeddings = []
        for embedding in embeddings:
            norm = math.sqrt(sum(x * x for x in embedding))
            if norm > 0:
                embedding = [x / norm for x in embedding]
            normalized_embeddings.append(embedding)

        return normalized_embeddings

    @property
    def dimension(self) -> int:
        """Return the dimension of embeddings produced."""
        return self._dimension


class MockEmbeddingProvider(EmbeddingProvider):
    """
    Mock embedding provider for testing.
    Generates deterministic random embeddings based on text hash.
    """

    def __init__(self, dimension: int = 1536):
        self._dimension = dimension

    async def embed_text(self, text: str) -> list[float]:
        import random

        # Use text hash as seed for deterministic results
        seed = hash(text) % (2**32)
        random.seed(seed)
        return [random.random() for _ in range(self._dimension)]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [await self.embed_text(text) for text in texts]

    @property
    def dimension(self) -> int:
        return self._dimension
