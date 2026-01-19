"""
LLM Providers - 语言模型提供者

基于第一性原理简化的LLM提供者系统。

## 核心接口
- LLMProvider: LLM提供者抽象接口
- LLMResponse: 标准化的LLM响应
- StreamChunk: 流式输出的结构化块
- BaseResponseHandler: 响应处理器基类
- ToolCallAggregator: 工具调用聚合器

## 核心 Providers
- OpenAIProvider: OpenAI (GPT-4, GPT-3.5等)
- AnthropicProvider: Anthropic Claude
- GeminiProvider: Google Gemini

## 国内 LLM Providers
- DeepSeekProvider: DeepSeek
- QwenProvider: 通义千问
- ZhipuProvider: 智谱AI
- KimiProvider: Kimi (月之暗面)
- DoubaoProvider: 豆包 (字节跳动)

## 本地部署 Providers
- OllamaProvider: Ollama 本地模型
- VLLMProvider: vLLM 高性能推理
- GPUStackProvider: GPU Stack 集群

## 通用 Providers
- OpenAICompatibleProvider: OpenAI 兼容 API 基类
- CustomProvider: 自定义 Provider

## 测试工具
- MockLLMProvider: Mock Provider (用于测试)

## 辅助工具
- RetryConfig: 重试配置
- retry_async: 异步重试包装器
"""

# 核心接口
# 核心 Providers
from loom.providers.llm.anthropic import AnthropicProvider
from loom.providers.llm.base_handler import BaseResponseHandler, ToolCallAggregator

# 通用 Providers
from loom.providers.llm.custom import CustomProvider

# 国内 LLM Providers
from loom.providers.llm.deepseek import DeepSeekProvider
from loom.providers.llm.doubao import DoubaoProvider
from loom.providers.llm.gemini import GeminiProvider

# 本地部署 Providers
from loom.providers.llm.gpustack import GPUStackProvider
from loom.providers.llm.interface import LLMProvider, LLMResponse, StreamChunk
from loom.providers.llm.kimi import KimiProvider

# 测试工具
from loom.providers.llm.mock import MockLLMProvider
from loom.providers.llm.ollama import OllamaProvider
from loom.providers.llm.openai import OpenAIProvider

# OpenAI 兼容基类
from loom.providers.llm.openai_compatible import OpenAICompatibleProvider
from loom.providers.llm.qwen import QwenProvider

# 辅助工具
from loom.providers.llm.retry_handler import RetryConfig, retry_async
from loom.providers.llm.vllm import VLLMProvider
from loom.providers.llm.zhipu import ZhipuProvider

__all__ = [
    # 核心接口
    "LLMProvider",
    "LLMResponse",
    "StreamChunk",
    "BaseResponseHandler",
    "ToolCallAggregator",
    # 核心 Providers
    "OpenAIProvider",
    "AnthropicProvider",
    "GeminiProvider",
    # OpenAI 兼容基类
    "OpenAICompatibleProvider",
    # 国内 LLM Providers
    "DeepSeekProvider",
    "QwenProvider",
    "ZhipuProvider",
    "KimiProvider",
    "DoubaoProvider",
    # 本地部署 Providers
    "OllamaProvider",
    "VLLMProvider",
    "GPUStackProvider",
    # 通用 Providers
    "CustomProvider",
    # 测试工具
    "MockLLMProvider",
    # 辅助工具
    "RetryConfig",
    "retry_async",
]
