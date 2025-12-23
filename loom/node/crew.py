"""
Crew Node (Orchestrator)
"""

from typing import Any, List, Literal

from loom.protocol.cloudevents import CloudEvent
from loom.node.agent import AgentNode
from loom.node.base import Node
from loom.kernel.dispatcher import Dispatcher
from loom.protocol.memory_operations import ContextSanitizer
from loom.builtin.memory.sanitizers import BubbleUpSanitizer

class CrewNode(Node):
    """
    A Node that orchestrates other Nodes (recursive composition).
    """
    
    def __init__(
        self,
        node_id: str,
        dispatcher: Dispatcher,
        agents: List[AgentNode],
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
        """
        current_input = task
        chain_results = []
        
        for agent in self.agents:
            # 1. Create Event for Agent
            event = CloudEvent.create(
                source=self.source_uri,
                type="node.request",
                data={"task": current_input},
                subject=agent.source_uri,
                traceparent=traceparent
            )
            
            # 2. Invoke (Directly for MVP sync flow, see AgentNode discussion)
            try:
                result = await agent.process(event)
            except Exception as e:
                # Robustness: Capture error but don't crash chain immediately?
                # Or abort?
                # For now, we abort but return error struct.
                return {
                    "error": f"Agent {agent.node_id} failed: {str(e)}",
                    "trace": chain_results
                }
            
            # 3. Process output
            response = result.get("response", "")
            
            # Sanitization (Fractal Metabolism)
            # Limit the bubble-up context to ~200 chars or reasonable token limit per agent to prevent pollution
            sanitized_response = await self.sanitizer.sanitize(str(response), target_token_limit=100)
            
            chain_results.append({
                "agent": agent.node_id,
                "output": response, # Full output in trace
                "sanitized": sanitized_response
            })
            
            # 4. Pass to next
            # We pass the full output to the immediate next strictly?
            # Or do we pass the accumulated context? 
            # In "Sequential", A's output is B's input.
            # If A outputs 5000 tokens, B is overwhelmed.
            # So passing sanitized response is better for long chains unless full data needed.
            # But "task" usually implies specific instruction. 
            # If sequential is "Refine this artifact", we need full artifact.
            # If sequential is "Research -> Planner", we need summary.
            
            # Design choice: For generic Crew, we pass full output (trusting agent to handle it or memory to metabolize it).
            # BUT the return value of THIS CrewNode to its parent should be sanitized or structured.
            
            current_input = response
            
        return {
            "final_output": current_input,
            "trace": chain_results
        }
