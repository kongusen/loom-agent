"""
LLM Providers

包含各种 LLM 实现。
"""

# Always available
from loom.llm.providers.mock import MockLLMProvider

# Optional providers - import only if dependencies are available
__all__ = ["MockLLMProvider"]

try:
    from loom.llm.providers.openai import OpenAIProvider
    __all__.append("OpenAIProvider")
except ImportError:
    pass

try:
    from loom.llm.providers.anthropic import AnthropicProvider
    __all__.append("AnthropicProvider")
except ImportError:
    pass

try:
    from loom.llm.providers.gemini import GeminiProvider
    __all__.append("GeminiProvider")
except ImportError:
    pass

try:
    from loom.llm.providers.deepseek import DeepSeekProvider
    __all__.append("DeepSeekProvider")
except ImportError:
    pass

try:
    from loom.llm.providers.zhipu import ZhipuProvider
    __all__.append("ZhipuProvider")
except ImportError:
    pass

try:
    from loom.llm.providers.kimi import KimiProvider
    __all__.append("KimiProvider")
except ImportError:
    pass

try:
    from loom.llm.providers.qwen import QwenProvider
    __all__.append("QwenProvider")
except ImportError:
    pass

try:
    from loom.llm.providers.doubao import DoubaoProvider
    __all__.append("DoubaoProvider")
except ImportError:
    pass

try:
    from loom.llm.providers.ollama import OllamaProvider
    __all__.append("OllamaProvider")
except ImportError:
    pass

try:
    from loom.llm.providers.vllm import VLLMProvider
    __all__.append("VLLMProvider")
except ImportError:
    pass

try:
    from loom.llm.providers.gpustack import GPUStackProvider
    __all__.append("GPUStackProvider")
except ImportError:
    pass

try:
    from loom.llm.providers.custom import CustomProvider
    __all__.append("CustomProvider")
except ImportError:
    pass
