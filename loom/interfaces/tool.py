from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class BaseTool(ABC):
    """
    工具基础接口。

    Attributes:
        name: Tool name (unique identifier)
        description: Tool description for LLM
        args_schema: Pydantic model for argument validation
        is_read_only: Whether tool only reads data (safe to parallelize) 🆕
        category: Tool category (general/destructive/network) 🆕
        requires_confirmation: Whether tool requires user confirmation 🆕
    """

    name: str
    description: str
    args_schema: type[BaseModel]

    # 🆕 Loom 2.0 - Orchestration attributes
    is_read_only: bool = False
    """Whether this tool only reads data (safe to parallelize with other read-only tools)."""

    category: str = "general"
    """Tool category: 'general', 'destructive', 'network'."""

    requires_confirmation: bool = False
    """Whether this tool requires explicit user confirmation before execution."""

    @abstractmethod
    async def run(self, **kwargs) -> Any:
        raise NotImplementedError

    @property
    def is_async(self) -> bool:
        return True

    @property
    def is_concurrency_safe(self) -> bool:
        """Legacy attribute for backward compatibility."""
        return True

