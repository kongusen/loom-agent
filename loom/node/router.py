"""
Router Node (Attention Mechanism)
"""

from typing import Any

from loom.kernel.core import Dispatcher
from loom.llm import LLMProvider
from loom.node.base import Node
from loom.protocol.cloudevents import CloudEvent
from loom.protocol.interfaces import NodeProtocol


class AttentionRouter(Node):
    """
    Intelligent Router that routes tasks to the best suited Node based on description.

    FIXED: Now accepts List[NodeProtocol] instead of List[AgentNode].
    This enables fractal routing:
    - Can route to AgentNode
    - Can route to CrewNode (sub-teams)
    - Can route to other RouterNode (nested routing)
    - Any Node type that implements NodeProtocol

    This adheres to "Protocol-First" and "Fractal Uniformity" principles.
    """

    def __init__(
        self,
        node_id: str,
        dispatcher: Dispatcher,
        agents: list[NodeProtocol],
        provider: LLMProvider
    ):
        super().__init__(node_id, dispatcher)
        self.agents = {agent.node_id: agent for agent in agents}
        self.provider = provider
        # Agent descriptions map
        self.registry = {agent.node_id: getattr(agent, 'role', 'agent') for agent in agents}
    async def process(self, event: CloudEvent) -> Any:
        data = event.data or {}
        task = str(data.get("task", ""))
        if not task:
            return {"error": "No task provided"}

        # 1. Construct Prompt
        options = "\n".join([f"- {aid}: {getattr(self.agents[aid], 'role', 'agent')}" for aid in self.agents])
        prompt = f"""
        You are a routing system. Given the task, select the best agent ID to handle it.
        Return ONLY the agent ID.

        Agents:
        {options}

        Task: {task}
        """

        # 2. LLM Select
        # Simple chat call
        response = await self.provider.chat([{"role": "user", "content": prompt}])
        selected_id = response.content.strip()

        # Clean up potential extra chars/whitespace
        # Iterate keys to find match if fuzzy
        target_agent = None
        for aid in self.agents:
            if aid in selected_id:
                target_agent = self.agents[aid]
                break

        if not target_agent:
             return {"error": f"Could not route task. Selected: {selected_id}"}

        # 3. Dispatch to Target
        # Request-Reply: We wait for the agent and return its result.
        # Use our Node.call mechanism!

        result = await self.call(target_agent.source_uri, {"task": task})
        return {"result": result, "routed_to": target_agent.node_id}
