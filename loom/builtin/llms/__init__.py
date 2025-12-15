"""
Loom Builtin LLMs - 内置 LLM 实现

提供主流 LLM 提供商的支持，分为两类：

## 1. OpenAI 兼容提供商（使用 UnifiedLLM）

支持的提供商：
- OpenAI (原生)
- DeepSeek (深度求索)
- Qwen (阿里通义千问)
- Kimi (月之暗面)
- 智谱 GLM
- 豆包 (字节跳动)
- 零一万物 Yi

使用方式：
```python
from loom.builtin import UnifiedLLM

# 方式 1：使用 UnifiedLLM（推荐）
llm = UnifiedLLM(provider="deepseek", api_key="...")

# 方式 2：使用别名（更简洁）
llm = DeepSeekLLM(api_key="...")
```

## 2. 非兼容提供商（使用专门适配器）

支持的提供商：
- Anthropic Claude（使用 Anthropic SDK）

使用方式：
```python
from loom.builtin import AnthropicLLM

llm = AnthropicLLM(api_key="sk-ant-...")
```

## 依赖

- OpenAI 兼容提供商：需要 `pip install openai`
- Anthropic：需要 `pip install anthropic`
"""

from loom.builtin.llms.unified import UnifiedLLM
from loom.builtin.llms.providers import (
    OPENAI_COMPATIBLE_PROVIDERS,
    NON_COMPATIBLE_PROVIDERS,
    list_providers,
    get_provider_info,
)

# ============================================================================
# 导出主要类
# ============================================================================

__all__ = [
    # 统一 LLM
    "UnifiedLLM",
    # OpenAI（使用 UnifiedLLM 的别名）
    "OpenAILLM",
    # 国产主流 LLM（使用 UnifiedLLM 的别名）
    "DeepSeekLLM",
    "QwenLLM",
    "KimiLLM",
    "ZhipuLLM",
    "DoubaoLLM",
    "YiLLM",
    # 工具函数
    "list_providers",
    "get_provider_info",
]

# ============================================================================
# 创建便捷别名
# ============================================================================


class OpenAILLM(UnifiedLLM):
    """OpenAI LLM - UnifiedLLM 的便捷别名"""

    def __init__(self, api_key: str, **kwargs):
        super().__init__(api_key=api_key, provider="openai", **kwargs)


class DeepSeekLLM(UnifiedLLM):
    """DeepSeek LLM - UnifiedLLM 的便捷别名"""

    def __init__(self, api_key: str, **kwargs):
        super().__init__(api_key=api_key, provider="deepseek", **kwargs)


class QwenLLM(UnifiedLLM):
    """Qwen/通义千问 LLM - UnifiedLLM 的便捷别名"""

    def __init__(self, api_key: str, **kwargs):
        super().__init__(api_key=api_key, provider="qwen", **kwargs)


class KimiLLM(UnifiedLLM):
    """Kimi/月之暗面 LLM - UnifiedLLM 的便捷别名"""

    def __init__(self, api_key: str, **kwargs):
        super().__init__(api_key=api_key, provider="kimi", **kwargs)


class ZhipuLLM(UnifiedLLM):
    """智谱/GLM LLM - UnifiedLLM 的便捷别名"""

    def __init__(self, api_key: str, **kwargs):
        super().__init__(api_key=api_key, provider="zhipu", **kwargs)


class DoubaoLLM(UnifiedLLM):
    """豆包/字节跳动 LLM - UnifiedLLM 的便捷别名"""

    def __init__(self, api_key: str, **kwargs):
        super().__init__(api_key=api_key, provider="doubao", **kwargs)


class YiLLM(UnifiedLLM):
    """零一万物 Yi LLM - UnifiedLLM 的便捷别名"""

    def __init__(self, api_key: str, **kwargs):
        super().__init__(api_key=api_key, provider="yi", **kwargs)
