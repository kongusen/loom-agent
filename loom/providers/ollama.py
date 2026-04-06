"""Ollama provider (local, OpenAI-compatible)."""

from .openai import OpenAIProvider

_OLLAMA_BASE_URL = "http://localhost:11434/v1"


class OllamaProvider(OpenAIProvider):
    """Local Ollama provider via its OpenAI-compatible API.

    Args:
        model: Any model pulled in Ollama, e.g. ``llama3``, ``qwen2.5``,
               ``mistral``, ``deepseek-r1``, etc.
        base_url: Ollama server URL. Defaults to ``http://localhost:11434/v1``.
    """

    def __init__(
        self,
        base_url: str = _OLLAMA_BASE_URL,
    ):
        # Ollama does not require a real API key
        super().__init__(api_key="ollama", base_url=base_url)
