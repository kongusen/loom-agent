"""
Router Node (Attention Mechanism)
"""

from typing import Any, List, Dict
from loom.protocol.cloudevents import CloudEvent
from loom.node.base import Node
from loom.node.agent import AgentNode
from loom.kernel.dispatcher import Dispatcher
from loom.interfaces.llm import LLMProvider

class AttentionRouter(Node):
    """
    Intelligent Router that routes tasks to the best suited Agent based on description.
    """
    
    def __init__(
        self,
        node_id: str,
        dispatcher: Dispatcher,
        agents: List[AgentNode],
        provider: LLMProvider
    ):
        super().__init__(node_id, dispatcher)
        self.agents = {agent.node_id: agent for agent in agents}
        self.provider = provider
        # Agent descriptions map
        self.registry = {agent.node_id: agent.role for agent in agents}
        
    async def process(self, event: CloudEvent) -> Any:
        task = event.data.get("task", "")
        if not task:
            return {"error": "No task provided"}
            
        # 1. Construct Prompt
        options = "\n".join([f"- {aid}: {role}" for aid, role in self.registry.items()])
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
