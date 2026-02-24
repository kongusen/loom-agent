"""Provider presets — OpenAI-compatible LLM factories."""

from __future__ import annotations

from ..config import AgentConfig
from .openai import OpenAIProvider


def create_deepseek(api_key: str, model: str = "deepseek-chat", **kw) -> OpenAIProvider:
    return OpenAIProvider(
        AgentConfig(api_key=api_key, model=model, base_url="https://api.deepseek.com/v1", **kw)
    )


def create_qwen(api_key: str, model: str = "qwen-plus", **kw) -> OpenAIProvider:
    return OpenAIProvider(
        AgentConfig(
            api_key=api_key,
            model=model,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            **kw,
        )
    )


def create_zhipu(api_key: str, model: str = "glm-4-flash", **kw) -> OpenAIProvider:
    return OpenAIProvider(
        AgentConfig(
            api_key=api_key, model=model, base_url="https://open.bigmodel.cn/api/paas/v4", **kw
        )
    )


def create_moonshot(api_key: str, model: str = "moonshot-v1-8k", **kw) -> OpenAIProvider:
    return OpenAIProvider(
        AgentConfig(api_key=api_key, model=model, base_url="https://api.moonshot.cn/v1", **kw)
    )


def create_baichuan(api_key: str, model: str = "Baichuan4", **kw) -> OpenAIProvider:
    return OpenAIProvider(
        AgentConfig(api_key=api_key, model=model, base_url="https://api.baichuan-ai.com/v1", **kw)
    )


def create_yi(api_key: str, model: str = "yi-large", **kw) -> OpenAIProvider:
    return OpenAIProvider(
        AgentConfig(api_key=api_key, model=model, base_url="https://api.lingyiwanwu.com/v1", **kw)
    )


def create_doubao(api_key: str, model: str = "doubao-pro-4k", **kw) -> OpenAIProvider:
    return OpenAIProvider(
        AgentConfig(
            api_key=api_key, model=model, base_url="https://ark.cn-beijing.volces.com/api/v3", **kw
        )
    )


# --- Local / self-hosted (OpenAI-compatible) ---


def create_ollama(
    model: str = "llama3", base_url: str = "http://localhost:11434/v1", **kw
) -> OpenAIProvider:
    return OpenAIProvider(AgentConfig(api_key="ollama", model=model, base_url=base_url, **kw))


def create_vllm(
    model: str = "default", base_url: str = "http://localhost:8000/v1", **kw
) -> OpenAIProvider:
    return OpenAIProvider(AgentConfig(api_key="vllm", model=model, base_url=base_url, **kw))


def create_gpustack(
    api_key: str, model: str = "default", base_url: str = "http://localhost:80/v1", **kw
) -> OpenAIProvider:
    return OpenAIProvider(AgentConfig(api_key=api_key, model=model, base_url=base_url, **kw))


def create_custom(api_key: str, model: str, base_url: str, **kw) -> OpenAIProvider:
    return OpenAIProvider(AgentConfig(api_key=api_key, model=model, base_url=base_url, **kw))
