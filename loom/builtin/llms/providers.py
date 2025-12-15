"""
LLM 提供商配置

支持两类提供商：
1. OpenAI 兼容格式：使用统一的 UnifiedLLM 处理
2. 非兼容格式：使用专门的适配器

当前支持的提供商：
- OpenAI (原生)
- DeepSeek (兼容 OpenAI)
- Qwen/通义千问 (兼容 OpenAI)
- Kimi/月之暗面 (兼容 OpenAI)
- 智谱/GLM (兼容 OpenAI)
- Gemini (兼容 OpenAI)
- Anthropic (原生 API，非兼容)
"""

from typing import Dict, List, Optional

# ============================================================================
# OpenAI 兼容的提供商配置
# ============================================================================

OPENAI_COMPATIBLE_PROVIDERS: Dict[str, Dict] = {
    "openai": {
        "name": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4",
        "models": [
            "gpt-4",
            "gpt-4-turbo",
            "gpt-4o",
            "gpt-3.5-turbo",
            "o1-preview",
            "o1-mini",
        ],
        "description": "OpenAI 官方 API",
    },
    "custom": {
        "name": "自定义 OpenAI 兼容服务",
        "base_url": None,  # 必须由用户提供
        "default_model": "gpt-3.5-turbo",  # 默认模型，用户可覆盖
        "models": [],  # 由用户自定义
        "description": "支持任何 OpenAI 兼容的第三方服务，需要指定 base_url",
    },
    "deepseek": {
        "name": "DeepSeek",
        "base_url": "https://api.deepseek.com/v1",
        "default_model": "deepseek-chat",
        "models": [
            "deepseek-chat",
            "deepseek-coder",
        ],
        "description": "DeepSeek 深度求索（国产）",
    },
    "qwen": {
        "name": "Qwen/通义千问",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "default_model": "qwen-turbo",
        "models": [
            "qwen-turbo",
            "qwen-plus",
            "qwen-max",
            "qwen-long",
        ],
        "description": "阿里云通义千问（国产）",
    },
    "kimi": {
        "name": "Kimi/月之暗面",
        "base_url": "https://api.moonshot.cn/v1",
        "default_model": "moonshot-v1-8k",
        "models": [
            "moonshot-v1-8k",
            "moonshot-v1-32k",
            "moonshot-v1-128k",
        ],
        "description": "月之暗面 Kimi（国产）",
    },
    "zhipu": {
        "name": "智谱/GLM",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "default_model": "glm-4",
        "models": [
            "glm-4",
            "glm-4-air",
            "glm-4-flash",
            "glm-3-turbo",
        ],
        "description": "智谱 AI GLM（国产）",
    },
    "doubao": {
        "name": "豆包/字节跳动",
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "default_model": "doubao-pro-4k",
        "models": [
            "doubao-pro-4k",
            "doubao-pro-32k",
            "doubao-lite-4k",
        ],
        "description": "字节跳动豆包（国产）",
    },
    "yi": {
        "name": "零一万物",
        "base_url": "https://api.lingyiwanwu.com/v1",
        "default_model": "yi-large",
        "models": [
            "yi-large",
            "yi-medium",
            "yi-vision",
            "yi-medium-200k",
        ],
        "description": "零一万物 Yi（国产）",
    },
}

# ============================================================================
# 非 OpenAI 兼容的提供商（需要专门适配器）
# ============================================================================

NON_COMPATIBLE_PROVIDERS: Dict[str, Dict] = {
    "anthropic": {
        "name": "Anthropic Claude",
        "default_model": "claude-3-5-sonnet-20241022",
        "models": [
            "claude-3-5-sonnet-20241022",
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307",
        ],
        "description": "Anthropic Claude 系列（需要专门适配器）",
        "adapter": "AnthropicLLM",
    },
    "gemini": {
        "name": "Google Gemini",
        "default_model": "gemini-pro",
        "models": [
            "gemini-pro",
            "gemini-pro-vision",
            "gemini-1.5-pro",
            "gemini-1.5-flash",
        ],
        "description": "Google Gemini（可使用 OpenAI 兼容或原生 API）",
        "adapter": "GeminiLLM",
        "note": "也可以通过 OpenAI 兼容模式使用",
    },
}

# ============================================================================
# 工具函数
# ============================================================================


def get_provider_info(provider: str) -> Optional[Dict]:
    """
    获取提供商信息

    Args:
        provider: 提供商名称

    Returns:
        提供商配置字典，如果不存在返回 None
    """
    if provider in OPENAI_COMPATIBLE_PROVIDERS:
        return OPENAI_COMPATIBLE_PROVIDERS[provider]
    elif provider in NON_COMPATIBLE_PROVIDERS:
        return NON_COMPATIBLE_PROVIDERS[provider]
    return None


def is_openai_compatible(provider: str) -> bool:
    """
    检查提供商是否兼容 OpenAI 格式

    Args:
        provider: 提供商名称

    Returns:
        是否兼容 OpenAI 格式
    """
    return provider in OPENAI_COMPATIBLE_PROVIDERS


def list_providers() -> Dict[str, List[str]]:
    """
    列出所有支持的提供商

    Returns:
        提供商列表，按类型分组
    """
    return {
        "openai_compatible": list(OPENAI_COMPATIBLE_PROVIDERS.keys()),
        "non_compatible": list(NON_COMPATIBLE_PROVIDERS.keys()),
    }


def get_default_model(provider: str) -> Optional[str]:
    """
    获取提供商的默认模型

    Args:
        provider: 提供商名称

    Returns:
        默认模型名称
    """
    info = get_provider_info(provider)
    return info["default_model"] if info else None


def validate_model(provider: str, model: str) -> bool:
    """
    验证模型是否支持

    Args:
        provider: 提供商名称
        model: 模型名称

    Returns:
        是否支持该模型
    """
    info = get_provider_info(provider)
    if not info:
        return False
    return model in info.get("models", [])
