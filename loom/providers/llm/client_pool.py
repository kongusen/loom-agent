"""
LLM Client Connection Pool

缓存 AsyncOpenAI / AsyncAnthropic 客户端实例，
多个 Provider 共享同一连接级配置的客户端，减少 TCP 连接开销。

cache_key = (client_class_name, api_key, base_url, timeout, max_retries, frozen_kwargs)
temperature / max_tokens / model 是请求级参数，不入 key。
"""

from __future__ import annotations

import threading
from typing import Any


def _freeze(value: Any) -> Any:
    """递归将可变值转为 hashable"""
    if isinstance(value, dict):
        return tuple(sorted((k, _freeze(v)) for k, v in value.items()))
    if isinstance(value, list):
        return tuple(_freeze(v) for v in value)
    if isinstance(value, set):
        return frozenset(_freeze(v) for v in value)
    return value


def _make_cache_key(
    client_class_name: str,
    api_key: str | None,
    base_url: str | None,
    timeout: int,
    max_retries: int,
    **kwargs: Any,
) -> tuple:
    """构建 hashable 缓存键"""
    frozen_kwargs = tuple(sorted(
        (k, _freeze(v)) for k, v in kwargs.items()
    ))
    return (client_class_name, api_key, base_url, timeout, max_retries, frozen_kwargs)


class LLMClientPool:
    """
    线程安全的 LLM 客户端连接池（单例）

    用法：
        client = LLMClientPool.get_instance().get_or_create(
            AsyncOpenAI,
            api_key="sk-...",
            base_url=None,
            timeout=60,
            max_retries=3,
        )
    """

    _instance: LLMClientPool | None = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._pool: dict[tuple, Any] = {}
        self._pool_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> LLMClientPool:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def get_or_create(
        self,
        client_class: type,
        *,
        api_key: str | None,
        base_url: str | None,
        timeout: int,
        max_retries: int,
        **kwargs: Any,
    ) -> Any:
        """获取缓存的客户端或创建新实例"""
        key = _make_cache_key(
            client_class.__name__,
            api_key,
            base_url,
            timeout,
            max_retries,
            **kwargs,
        )
        with self._pool_lock:
            if key not in self._pool:
                self._pool[key] = client_class(
                    api_key=api_key,
                    base_url=base_url,
                    timeout=timeout,
                    max_retries=max_retries,
                    **kwargs,
                )
            return self._pool[key]

    @property
    def pool_size(self) -> int:
        """当前缓存的客户端数"""
        with self._pool_lock:
            return len(self._pool)

    def clear(self) -> None:
        """清空连接池"""
        with self._pool_lock:
            self._pool.clear()

    @classmethod
    def reset(cls) -> None:
        """重置单例（仅用于测试）"""
        with cls._lock:
            if cls._instance is not None:
                cls._instance.clear()
            cls._instance = None
