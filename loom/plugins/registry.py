"""
Component Registry - Centralized registration for LLM, Tool, and Memory implementations

This is a simple registry for managing core loom components. It is separate from
the ToolPluginRegistry which manages plugin-based tools.

Use cases:
- Register built-in LLM providers (OpenAI, Anthropic, etc.)
- Register built-in tools
- Register memory implementations

Note: For plugin-based tools, use ToolPluginRegistry from loom.plugins.tool_plugin

Example:
    ```python
    from loom.plugins.registry import ComponentRegistry
    from loom.interfaces.llm import BaseLLM

    # Register an LLM implementation
    @ComponentRegistry.register_llm("my-llm")
    class MyLLM:
        # Implementation...
        pass

    # Get registered LLM
    llm = ComponentRegistry.get_llm("my-llm", api_key="...")
    ```
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Type

from loom.interfaces.llm import BaseLLM
from loom.interfaces.memory import BaseMemory
from loom.interfaces.tool import BaseTool


class ComponentRegistry:
    """
    Centralized component registry for built-in LLM, Tool, and Memory implementations.

    This registry is for built-in components, not plugin-based tools.
    For plugin tools, use ToolPluginRegistry instead.
    """

    _llms: Dict[str, Type[BaseLLM]] = {}
    _tools: Dict[str, Type[BaseTool]] = {}
    _memories: Dict[str, Type[BaseMemory]] = {}

    @classmethod
    def register_llm(cls, name: str):
        """Register an LLM implementation"""
        def decorator(impl: Type[BaseLLM]):
            cls._llms[name] = impl
            return impl
        return decorator

    @classmethod
    def register_tool(cls, name: str):
        """Register a tool implementation"""
        def decorator(impl: Type[BaseTool]):
            cls._tools[name] = impl
            return impl
        return decorator

    @classmethod
    def register_memory(cls, name: str):
        """Register a memory implementation"""
        def decorator(impl: Type[BaseMemory]):
            cls._memories[name] = impl
            return impl
        return decorator

    @classmethod
    def get_llm(cls, name: str, **kwargs: Any) -> BaseLLM:
        """Get an LLM instance by name"""
        if name not in cls._llms:
            raise ValueError(f"LLM '{name}' not registered")
        return cls._llms[name](**kwargs)

    @classmethod
    def get_tool(cls, name: str, **kwargs: Any) -> BaseTool:
        """Get a tool instance by name"""
        if name not in cls._tools:
            raise ValueError(f"Tool '{name}' not registered")
        return cls._tools[name](**kwargs)

    @classmethod
    def get_memory(cls, name: str, **kwargs: Any) -> BaseMemory:
        """Get a memory instance by name"""
        if name not in cls._memories:
            raise ValueError(f"Memory '{name}' not registered")
        return cls._memories[name](**kwargs)


# For backward compatibility - deprecated
PluginRegistry = ComponentRegistry

