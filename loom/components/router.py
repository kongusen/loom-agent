from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict

from .chain import Chain


Condition = Callable[[Any], Awaitable[str]]


class Router:
    """路由组件 - 条件分支到不同 Chain。"""

    def __init__(self, condition: Condition, routes: Dict[str, Chain]):
        self.condition = condition
        self.routes = routes

    async def run(self, input: Any) -> Any:
        key = await self.condition(input)
        chain = self.routes.get(key)
        if chain is None:
            raise ValueError(f"Route '{key}' not found")
        return await chain.run(input)

