from __future__ import annotations

from typing import Any, Awaitable, Callable, List


Step = Callable[[Any], Awaitable[Any]]


class Chain:
    """链式调用组件 - 最基础的组合单元。"""

    def __init__(self, steps: List[Step]):
        self.steps = steps

    async def run(self, input: Any) -> Any:
        result = input
        for step in self.steps:
            result = await step(result)
        return result

    def __or__(self, other: "Chain") -> "Chain":
        return Chain(self.steps + other.steps)

