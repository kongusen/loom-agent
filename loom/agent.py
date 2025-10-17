"""Convenience builder for Agent

Allows simple usage patterns like:

import loom
agent = loom.agent(provider="openai", model="gpt-4o", api_key="...")
text = await agent.ainvoke("Hello")
"""

from __future__ import annotations

import os
from typing import Dict, List, Optional, Union

from .components.agent import Agent as _Agent
from .interfaces.llm import BaseLLM
from .interfaces.memory import BaseMemory
from .interfaces.tool import BaseTool
from .interfaces.compressor import BaseCompressor
from .llm.config import LLMConfig, LLMProvider
from .llm.factory import LLMFactory
from .callbacks.base import BaseCallback
from .callbacks.metrics import MetricsCollector
from .core.steering_control import SteeringControl


def agent(
    *,
    # Provide one of: llm | config | (provider+model)
    llm: Optional[BaseLLM] = None,
    config: Optional[LLMConfig] = None,
    provider: Optional[Union[str, LLMProvider]] = None,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    # Agent options
    tools: Optional[List[BaseTool]] = None,
    memory: Optional[BaseMemory] = None,
    compressor: Optional[BaseCompressor] = None,
    max_iterations: int = 50,
    max_context_tokens: int = 16000,
    permission_policy: Optional[Dict[str, str]] = None,
    ask_handler=None,
    safe_mode: bool = False,
    permission_store=None,
    # Extra LLM config overrides
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    # Advanced
    context_retriever=None,
    system_instructions: Optional[str] = None,
    callbacks: Optional[list[BaseCallback]] = None,
    steering_control: Optional[SteeringControl] = None,
    metrics: Optional[MetricsCollector] = None,
) -> _Agent:
    """Create an Agent with minimal parameters.

    Priority:
    1) Use provided `llm`
    2) Build from `config`
    3) Build from `provider` + `model` (+ api_key/base_url)
    """

    if llm is None:
        if config is None and provider is not None and model is not None:
            cfg = _build_config_from_inputs(
                provider=provider,
                model=model,
                api_key=api_key,
                base_url=base_url,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            llm = LLMFactory.create(cfg)
        elif config is not None:
            llm = LLMFactory.create(config)
        else:
            raise ValueError("Please provide `llm`, or `config`, or `provider` + `model`.")

    return _Agent(
        llm=llm,
        tools=tools,
        memory=memory,
        compressor=compressor,
        max_iterations=max_iterations,
        max_context_tokens=max_context_tokens,
        permission_policy=permission_policy,
        ask_handler=ask_handler,
        safe_mode=safe_mode,
        permission_store=permission_store,
        context_retriever=context_retriever,
        system_instructions=system_instructions,
        callbacks=callbacks,
        steering_control=steering_control,
        metrics=metrics,
    )


def agent_from_env(
    *,
    provider: Optional[Union[str, LLMProvider]] = None,
    model: Optional[str] = None,
    # Agent options
    tools: Optional[List[BaseTool]] = None,
    memory: Optional[BaseMemory] = None,
    compressor: Optional[BaseCompressor] = None,
    max_iterations: int = 50,
    max_context_tokens: int = 16000,
    permission_policy: Optional[Dict[str, str]] = None,
    ask_handler=None,
    safe_mode: bool = False,
    permission_store=None,
    # Advanced
    context_retriever=None,
    system_instructions: Optional[str] = None,
    callbacks: Optional[list[BaseCallback]] = None,
    steering_control: Optional[SteeringControl] = None,
    metrics: Optional[MetricsCollector] = None,
) -> _Agent:
    """Construct an Agent using provider/model resolved from environment.

    Environment variables:
    - LOOM_PROVIDER (fallback if provider not given)
    - LOOM_MODEL (fallback if model not given)
    - Provider-specific: OPENAI_API_KEY, OPENAI_BASE_URL, ANTHROPIC_API_KEY, COHERE_API_KEY, AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT
    """
    env_provider = os.getenv("LOOM_PROVIDER")
    env_model = os.getenv("LOOM_MODEL")
    use_provider = provider or env_provider
    use_model = model or env_model
    if not use_provider or not use_model:
        raise ValueError("agent_from_env requires provider/model or LOOM_PROVIDER/LOOM_MODEL env")

    return agent(
        provider=use_provider,
        model=use_model,
        tools=tools,
        memory=memory,
        compressor=compressor,
        max_iterations=max_iterations,
        max_context_tokens=max_context_tokens,
        permission_policy=permission_policy,
        ask_handler=ask_handler,
        safe_mode=safe_mode,
        permission_store=permission_store,
        context_retriever=context_retriever,
        system_instructions=system_instructions,
        callbacks=callbacks,
        steering_control=steering_control,
        metrics=metrics,
    )


def _build_config_from_inputs(
    *,
    provider: Union[str, LLMProvider],
    model: str,
    api_key: Optional[str],
    base_url: Optional[str],
    temperature: Optional[float],
    max_tokens: Optional[int],
) -> LLMConfig:
    prov = provider.value if isinstance(provider, LLMProvider) else str(provider).lower()

    # fill missing api_key from environment if possible
    if api_key is None:
        if prov == "openai" or prov == "custom" or prov == "azure_openai":
            api_key = os.getenv("OPENAI_API_KEY") or os.getenv("AZURE_OPENAI_API_KEY")
        elif prov == "anthropic":
            api_key = os.getenv("ANTHROPIC_API_KEY")
        elif prov == "cohere":
            api_key = os.getenv("COHERE_API_KEY")

    # default base_url for compatible providers if provided via env
    if base_url is None and prov in {"openai", "custom", "azure_openai"}:
        base_url = os.getenv("OPENAI_BASE_URL") or os.getenv("OPENAI_API_BASE")

    kwargs = {}
    if temperature is not None:
        kwargs["temperature"] = temperature
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens
    if base_url is not None:
        kwargs["base_url"] = base_url

    if prov == "openai":
        if not api_key:
            raise ValueError("OPENAI provider requires api_key or OPENAI_API_KEY env")
        return LLMConfig.openai(api_key=api_key, model=model, **kwargs)
    if prov == "azure_openai":
        # Treat like OpenAI-compatible; users can pass endpoint via base_url
        if not api_key:
            raise ValueError("AZURE_OPENAI provider requires api_key or AZURE_OPENAI_API_KEY env")
        return LLMConfig.azure_openai(
            api_key=api_key,
            deployment_name=model,
            endpoint=kwargs.pop("base_url", os.getenv("AZURE_OPENAI_ENDPOINT", "")),
            **kwargs,
        )
    if prov == "anthropic":
        if not api_key:
            raise ValueError("ANTHROPIC provider requires api_key or ANTHROPIC_API_KEY env")
        return LLMConfig.anthropic(api_key=api_key, model=model, **kwargs)
    if prov == "cohere":
        if not api_key:
            raise ValueError("COHERE provider requires api_key or COHERE_API_KEY env")
        return LLMConfig.cohere(api_key=api_key, model=model, **kwargs)
    if prov == "google":
        if not api_key:
            raise ValueError("GOOGLE provider requires api_key env")
        return LLMConfig.google(api_key=api_key, model=model, **kwargs)
    if prov == "ollama":
        return LLMConfig.ollama(model=model, base_url=base_url or "http://localhost:11434", **kwargs)
    if prov == "custom":
        return LLMConfig.custom(model_name=model, base_url=base_url or "", api_key=api_key, **kwargs)

    raise ValueError(f"Unknown provider: {provider}")
