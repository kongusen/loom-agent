"""
LLM Providers - 语言模型提供者（懒加载版本）

基于第一性原理简化的LLM提供者系统。
使用 __getattr__ 实现懒加载，只在实际使用时才加载对应的 Provider。

## 核心接口（始终加载）
- LLMProvider: LLM提供者抽象接口
- LLMResponse: 标准化的LLM响应
- StreamChunk: 流式输出的结构化块
- BaseResponseHandler: 响应处理器基类
- ToolCallAggregator: 工具调用聚合器

## Providers（懒加载）
- OpenAIProvider, AnthropicProvider, GeminiProvider
- DeepSeekProvider, QwenProvider, ZhipuProvider, KimiProvider, DoubaoProvider
- OllamaProvider, VLLMProvider, GPUStackProvider
- OpenAICompatibleProvider, CustomProvider, MockLLMProvider
"""

from loom.providers.llm.base_handler import BaseResponseHandler, ToolCallAggregator

# 核心接口 - 始终加载（轻量级，无外部依赖）
from loom.providers.llm.interface import LLMProvider, LLMResponse, StreamChunk
from loom.providers.llm.retry_handler import RetryConfig, retry_async

# Provider 注册表（懒加载映射）
_PROVIDER_REGISTRY: dict[str, str] = {
    # 核心 Providers
    "AnthropicProvider": "loom.providers.llm.anthropic",
    "OpenAIProvider": "loom.providers.llm.openai",
    "GeminiProvider": "loom.providers.llm.gemini",
    # 国内 LLM Providers
    "DeepSeekProvider": "loom.providers.llm.deepseek",
    "QwenProvider": "loom.providers.llm.qwen",
    "ZhipuProvider": "loom.providers.llm.zhipu",
    "KimiProvider": "loom.providers.llm.kimi",
    "DoubaoProvider": "loom.providers.llm.doubao",
    # 本地部署 Providers
    "OllamaProvider": "loom.providers.llm.ollama",
    "VLLMProvider": "loom.providers.llm.vllm",
    "GPUStackProvider": "loom.providers.llm.gpustack",
    # 通用 Providers
    "OpenAICompatibleProvider": "loom.providers.llm.openai_compatible",
    "CustomProvider": "loom.providers.llm.custom",
    # 测试工具
    "MockLLMProvider": "loom.providers.llm.mock",
}

# 缓存已加载的 Provider
_loaded_providers: dict[str, type] = {}


def __getattr__(name: str):
    """懒加载 Provider - 只在首次访问时导入"""
    if name in _PROVIDER_REGISTRY:
        if name not in _loaded_providers:
            import importlib
            module = importlib.import_module(_PROVIDER_REGISTRY[name])
            _loaded_providers[name] = getattr(module, name)
        return _loaded_providers[name]
    raise AttributeError(f"module 'loom.providers.llm' has no attribute '{name}'")


__all__ = [
    # 核心接口（始终加载）
    "LLMProvider",
    "LLMResponse",
    "StreamChunk",
    "BaseResponseHandler",
    "ToolCallAggregator",
    "RetryConfig",
    "retry_async",
    # Providers（懒加载）
    "OpenAIProvider",
    "AnthropicProvider",
    "GeminiProvider",
    "OpenAICompatibleProvider",
    "DeepSeekProvider",
    "QwenProvider",
    "ZhipuProvider",
    "KimiProvider",
    "DoubaoProvider",
    "OllamaProvider",
    "VLLMProvider",
    "GPUStackProvider",
    "CustomProvider",
    "MockLLMProvider",
]
