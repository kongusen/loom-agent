"""
Crew Node (Orchestrator)
"""

from typing import Any, Literal

from loom.kernel.core import Dispatcher
from loom.memory.sanitizers import BubbleUpSanitizer
from loom.node.base import Node
from loom.protocol.cloudevents import CloudEvent
from loom.protocol.interfaces import NodeProtocol
from loom.protocol.memory_operations import ContextSanitizer


class CrewNode(Node):
    """
    A Node that orchestrates other Nodes (recursive composition).

    FIXED: Now accepts List[NodeProtocol] instead of List[AgentNode].
    This enables TRUE fractal recursion:
    - CrewNode can contain AgentNode
    - CrewNode can contain other CrewNode (nested crews)
    - CrewNode can contain RouterNode
    - Any Node type that implements NodeProtocol

    This adheres to "Protocol-First" and "Fractal Uniformity" principles.
    """

    def __init__(
        self,
        node_id: str,
        dispatcher: Dispatcher,
        agents: list[NodeProtocol],
        pattern: Literal["sequential", "parallel"] = "sequential",
        sanitizer: ContextSanitizer = None
    ):
        super().__init__(node_id, dispatcher)
        self.agents = agents
        self.pattern = pattern
        self.sanitizer = sanitizer or BubbleUpSanitizer()

    async def process(self, event: CloudEvent) -> Any:
        """
        Execute the crew pattern.
        """
        task = event.data.get("task", "")

        if self.pattern == "sequential":
            return await self._execute_sequential(task, event.traceparent)

        return {"error": "Unsupported pattern"}

    async def _execute_sequential(self, task: str, traceparent: str = None) -> Any:
        """
        Chain agents sequentially. A -> B -> C

        FIXED: Now uses self.call() to ensure all calls go through event bus.
        This ensures:
        - Interceptor hooks are triggered
        - Studio can capture events
        - Distributed deployment is supported
        - Fractal uniformity is maintained
        """
        current_input = task
        chain_results = []

        for agent in self.agents:
            # Use self.call() to invoke through event bus
            # This ensures proper event flow: request -> dispatch -> interceptors -> agent -> response
            try:
                result = await self.call(
                    target_node=agent.source_uri,
                    data={"task": current_input}
                )
            except Exception as e:
                # Error already propagated through event bus
                return {
                    "error": f"Agent {agent.node_id} failed: {str(e)}",
                    "trace": chain_results
                }

            # Extract response
            # self.call() returns the result data from node.response event
            if isinstance(result, dict):
                response = result.get("response", str(result))
            else:
                response = str(result)

            # Sanitization (Fractal Metabolism)
            # Limit the bubble-up context to prevent context pollution in long chains
            sanitized_response = await self.sanitizer.sanitize(str(response), target_token_limit=100)

            chain_results.append({
                "agent": agent.node_id,
                "output": response, # Full output in trace
                "sanitized": sanitized_response
            })

            # Pass to next agent
            # Design choice: pass full output (agent's memory will metabolize if needed)
            current_input = response

        return {
            "final_output": current_input,
            "trace": chain_results
        }
