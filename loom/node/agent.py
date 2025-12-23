"""
Agent Node (Fractal System)
"""

from typing import Any, Dict, List, Optional
import uuid

from loom.protocol.cloudevents import CloudEvent
from loom.node.base import Node
from loom.node.tool import ToolNode
from loom.kernel.dispatcher import Dispatcher

from loom.interfaces.llm import LLMProvider
from loom.infra.llm import MockLLMProvider
from loom.interfaces.memory import MemoryInterface
from loom.memory.hierarchical import HierarchicalMemory

class AgentNode(Node):
    """
    A Node that acts as an Intelligent Agent (MCP Client).
    """
    
    def __init__(
        self,
        node_id: str,
        dispatcher: Dispatcher,
        role: str = "Assistant",
        system_prompt: str = "You are a helpful assistant.",
        tools: Optional[List[ToolNode]] = None,
        provider: Optional[LLMProvider] = None,
        memory: Optional[MemoryInterface] = None
    ):
        super().__init__(node_id, dispatcher)
        self.role = role
        self.system_prompt = system_prompt
        self.known_tools = {t.tool_def.name: t for t in tools} if tools else {}
        # Replaced internal list list with Memory Interface
        self.memory = memory or HierarchicalMemory()
        self.provider = provider or MockLLMProvider()

    async def process(self, event: CloudEvent) -> Any:
        """
        Agent Loop with Memory:
        1. Receive Task -> Add to Memory
        2. Get Context from Memory
        3. Think (LLM)
        4. Tool Call -> Add Result to Memory
        5. Final Response
        """
        return await self._execute_loop(event)

    async def _execute_loop(self, event: CloudEvent) -> Any:
        """
        Execute the ReAct Loop.
        """
        task = event.data.get("task", "") or event.data.get("content", "")
        max_iterations = event.data.get("max_iterations", 5)
        
        # 1. Perceive (Add to Memory)
        await self.memory.add("user", task)
        
        iterations = 0
        final_response = ""
        
        while iterations < max_iterations:
            iterations += 1
            
            # 2. Recall (Get Context)
            history = await self.memory.get_recent(limit=20)
            messages = [{"role": "system", "content": self.system_prompt}] + history
            
            # 3. Think
            mcp_tools = [t.tool_def.model_dump() for t in self.known_tools.values()]
            response = await self.provider.chat(messages, tools=mcp_tools)
            final_text = response.content
            
            # 4. Act (Tool Usage or Final Answer)
            if response.tool_calls:
                # Record the "thought" / call intent
                # ALWAYS store assistant message with tool_calls (even if content is empty)
                await self.memory.add("assistant", final_text or "", metadata={
                    "tool_calls": response.tool_calls
                })
                
                # Execute tools (Parallel support possible, here sequential)
                for tc in response.tool_calls:
                    tc_name = tc.get("name")
                    tc_args = tc.get("arguments")
                    
                    # Emit thought event
                    await self.dispatcher.dispatch(CloudEvent.create(
                        source=self.source_uri,
                        type="agent.thought",
                        data={"thought": f"Calling {tc_name}", "tool_call": tc},
                        traceparent=event.traceparent
                    ))
                    
                    target_tool = self.known_tools.get(tc_name)
                    
                    if target_tool:
                        tool_event = CloudEvent.create(
                            source=self.source_uri,
                            type="node.request",
                            data={"arguments": tc_args},
                            subject=target_tool.source_uri,
                            traceparent=event.traceparent
                        )
                        
                        tool_result_evt = await target_tool.process(tool_event)
                        result_content = tool_result_evt.get("result")
                        
                        # Add Result to Memory (Observation)
                        # We use 'tool' role.
                        await self.memory.add("tool", str(result_content), metadata={"tool_name": tc_name, "tool_call_id": tc.get("id")})
                    else:
                        err_msg = f"Tool {tc_name} not found."
                        await self.memory.add("system", err_msg)
                
                # Loop continues to reflect on tool results
                continue
            
            else:
                # Final Answer
                await self.memory.add("assistant", final_text)
                final_response = final_text
                break
        
        if not final_response and iterations >= max_iterations:
             final_response = "Error: Maximum iterations reached without final answer."
             await self.memory.add("system", final_response)
             
        return {"response": final_response, "iterations": iterations}

