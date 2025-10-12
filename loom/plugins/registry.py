from __future__ import annotations

from typing import Any, Dict, Optional, Type

from loom.interfaces.llm import BaseLLM
from loom.interfaces.memory import BaseMemory
from loom.interfaces.tool import BaseTool


class PluginRegistry:
    """插件注册中心：注册/获取 LLM、Tool、Memory 实现。"""

    _llms: Dict[str, Type[BaseLLM]] = {}
    _tools: Dict[str, Type[BaseTool]] = {}
    _memories: Dict[str, Type[BaseMemory]] = {}

    @classmethod
    def register_llm(cls, name: str):
        def decorator(impl: Type[BaseLLM]):
            cls._llms[name] = impl
            return impl
        return decorator

    @classmethod
    def register_tool(cls, name: str):
        def decorator(impl: Type[BaseTool]):
            cls._tools[name] = impl
            return impl
        return decorator

    @classmethod
    def register_memory(cls, name: str):
        def decorator(impl: Type[BaseMemory]):
            cls._memories[name] = impl
            return impl
        return decorator

    @classmethod
    def get_llm(cls, name: str, **kwargs: Any) -> BaseLLM:
        if name not in cls._llms:
            raise ValueError(f"LLM '{name}' not registered")
        return cls._llms[name](**kwargs)

    @classmethod
    def get_tool(cls, name: str, **kwargs: Any) -> BaseTool:
        if name not in cls._tools:
            raise ValueError(f"Tool '{name}' not registered")
        return cls._tools[name](**kwargs)

    @classmethod
    def get_memory(cls, name: str, **kwargs: Any) -> BaseMemory:
        if name not in cls._memories:
            raise ValueError(f"Memory '{name}' not registered")
        return cls._memories[name](**kwargs)

