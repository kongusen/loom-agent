"""
LLM Providers

包含各种 LLM 实现。
"""

# Always available
# Optional providers - import only if dependencies are available
from loom.llm.interface import LLMProvider
from loom.llm.providers.mock import MockLLMProvider

__all__: list[str] = ["MockLLMProvider"]
PROVIDERS: dict[str, type[LLMProvider]] = {"MockLLMProvider": MockLLMProvider}

try:
    from loom.llm.providers.openai import OpenAIProvider

    __all__.append("OpenAIProvider")
    PROVIDERS["OpenAIProvider"] = OpenAIProvider
except ImportError:
    pass

try:
    from loom.llm.providers.anthropic import AnthropicProvider

    __all__.append("AnthropicProvider")
    PROVIDERS["AnthropicProvider"] = AnthropicProvider
except ImportError:
    pass

try:
    from loom.llm.providers.gemini import GeminiProvider

    __all__.append("GeminiProvider")
    PROVIDERS["GeminiProvider"] = GeminiProvider
except ImportError:
    pass

try:
    from loom.llm.providers.deepseek import DeepSeekProvider

    __all__.append("DeepSeekProvider")
    PROVIDERS["DeepSeekProvider"] = DeepSeekProvider
except ImportError:
    pass

try:
    from loom.llm.providers.zhipu import ZhipuProvider

    __all__.append("ZhipuProvider")
    PROVIDERS["ZhipuProvider"] = ZhipuProvider
except ImportError:
    pass

try:
    from loom.llm.providers.kimi import KimiProvider

    __all__.append("KimiProvider")
    PROVIDERS["KimiProvider"] = KimiProvider
except ImportError:
    pass

try:
    from loom.llm.providers.qwen import QwenProvider

    __all__.append("QwenProvider")
    PROVIDERS["QwenProvider"] = QwenProvider
except ImportError:
    pass

try:
    from loom.llm.providers.doubao import DoubaoProvider

    __all__.append("DoubaoProvider")
    PROVIDERS["DoubaoProvider"] = DoubaoProvider
except ImportError:
    pass

try:
    from loom.llm.providers.ollama import OllamaProvider

    __all__.append("OllamaProvider")
    PROVIDERS["OllamaProvider"] = OllamaProvider
except ImportError:
    pass

try:
    from loom.llm.providers.vllm import VLLMProvider

    __all__.append("VLLMProvider")
    PROVIDERS["VLLMProvider"] = VLLMProvider
except ImportError:
    pass

try:
    from loom.llm.providers.gpustack import GPUStackProvider

    __all__.append("GPUStackProvider")
    PROVIDERS["GPUStackProvider"] = GPUStackProvider
except ImportError:
    pass

try:
    from loom.llm.providers.custom import CustomProvider

    __all__.append("CustomProvider")
    PROVIDERS["CustomProvider"] = CustomProvider
except ImportError:
    pass
