"""
Budget Interceptor
"""

from loom.kernel.control.base import Interceptor
from loom.protocol.cloudevents import CloudEvent


class BudgetExceededError(Exception):
    pass


class BudgetInterceptor(Interceptor):
    """
    Controls resource usage (tokens/cost) per agent/node.
    """

    def __init__(self, max_tokens: int = 100000):
        self.max_tokens = max_tokens
        # Usage tracking: {node_id: tokens_used}
        self._usage: dict[str, int] = {}

    async def pre_invoke(self, event: CloudEvent) -> CloudEvent | None:
        # Check if this is a request that consumes budget?
        # Typically we check the SOURCE (Who is asking).
        # If Agent A asks Tool B, Agent A is spending budget?
        # Or if Agent A sends "node.response", it used tokens to generate it.

        # Policy: Check usage of the SOURCE node.
        # If usage > max, block.

        node_id = event.source.split("/")[-1]
        current_usage = self._usage.get(node_id, 0)

        if current_usage >= self.max_tokens:
            raise BudgetExceededError(
                f"Node {node_id} exceeded token budget: {current_usage}/{self.max_tokens}"
            )

        return event

    async def post_invoke(self, event: CloudEvent) -> None:
        # Update usage based on event type or result
        # For LLM-based agents, we usually get usage in the "agent.thought" or "node.response".
        # In this demo system, we don't have real token counts from MockLLM.
        # We'll heuristic: 1 char = 1 token for demo.

        node_id = event.source.split("/")[-1]

        tokens = 0
        if event.data and isinstance(event.data, dict):
            # If explicit usage field exists
            if "usage" in event.data:
                tokens = event.data["usage"].get("total_tokens", 0)
            else:
                # Heuristic
                content = str(event.data.get("thought", "") or event.data.get("result", "") or "")
                tokens = len(content) // 4  # Approx

        if tokens > 0:
            self._usage[node_id] = self._usage.get(node_id, 0) + tokens
