from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class BaseTool(ABC):
    """工具基础接口。"""

    name: str
    description: str
    args_schema: type[BaseModel]

    @abstractmethod
    async def run(self, **kwargs) -> Any:
        raise NotImplementedError

    @property
    def is_async(self) -> bool:
        return True

    @property
    def is_concurrency_safe(self) -> bool:
        return True

