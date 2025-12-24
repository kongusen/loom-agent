"""
Agent Node (Fractal System)
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
import uuid

from loom.protocol.cloudevents import CloudEvent
from loom.protocol.interfaces import ReflectiveMemoryStrategy
from loom.node.base import Node
from loom.node.tool import ToolNode
from loom.kernel.dispatcher import Dispatcher

from loom.interfaces.llm import LLMProvider
from loom.infra.llm import MockLLMProvider
from loom.interfaces.memory import MemoryInterface
from loom.memory.hierarchical import HierarchicalMemory


@dataclass
class ReflectionConfig:
    """
    Configuration for Memory Reflection (Human Factors Engineering).

    Framework DETECTS when reflection is needed.
    Developer CONFIGURES how reflection should behave.
    System EXECUTES the reflection according to config.
    """
    threshold: int = 20
    """Number of entries before reflection is triggered"""

    candidate_count: int = 10
    """Number of memory entries to include in reflection"""

    remove_count: int = 10
    """Number of entries to remove after consolidation"""

    prompt_template: str = "Summarize the following conversation segment into a concise knowledge entry:\n\n{history}"
    """Template for the reflection prompt. {history} will be replaced with actual history."""

    enabled: bool = True
    """Whether reflection is enabled"""


class AgentNode(Node):
    """
    A Node that acts as an Intelligent Agent (MCP Client).

    FIXED: Now accepts ReflectionConfig for configurable memory reflection,
    following Human Factors Engineering principle (developer controls strategy).
    """

    def __init__(
        self,
        node_id: str,
        dispatcher: Dispatcher,
        role: str = "Assistant",
        system_prompt: str = "You are a helpful assistant.",
        tools: Optional[List[ToolNode]] = None,
        provider: Optional[LLMProvider] = None,
        memory: Optional[MemoryInterface] = None,
        enable_auto_reflection: bool = False,
        reflection_config: Optional[ReflectionConfig] = None
    ):
        super().__init__(node_id, dispatcher)
        self.role = role
        self.system_prompt = system_prompt
        self.known_tools = {t.tool_def.name: t for t in tools} if tools else {}
        # Replaced internal list list with Memory Interface
        self.memory = memory or HierarchicalMemory()
        self.provider = provider or MockLLMProvider()
        self.enable_auto_reflection = enable_auto_reflection
        # FIXED: Configurable reflection parameters (Human Factors Engineering)
        self.reflection_config = reflection_config or ReflectionConfig()

    async def _perform_reflection(self) -> None:
        """
        Check and perform metabolic memory reflection.

        FIXED: Now uses developer-configured parameters instead of hardcoded values.
        Framework DETECTS, Developer CONFIGURES, System EXECUTES.

        FIXED: Uses Protocol check instead of isinstance for better abstraction.
        """
        # 0. Check if reflection is enabled
        if not self.reflection_config.enabled:
            return

        # 1. Check if memory supports reflection (Protocol-First)
        if not isinstance(self.memory, ReflectiveMemoryStrategy):
            # Memory doesn't support reflection, skip silently
            return

        # 2. Check if memory needs reflection (Framework DETECTS)
        if not self.memory.should_reflect(threshold=self.reflection_config.threshold):
            return

        # 3. Get candidates (Developer CONFIGURED count)
        candidates = self.memory.get_reflection_candidates(
            count=self.reflection_config.candidate_count
        )

        # 4. Summarize with LLM (Developer CONFIGURED prompt)
        history_text = "\n".join([f"{e.role}: {e.content}" for e in candidates])
        prompt = self.reflection_config.prompt_template.format(history=history_text)

        try:
            # We use a separate call (not affecting main context)
            response = await self.provider.chat([{"role": "user", "content": prompt}])
            summary = response.content

            # 5. Consolidate (Developer CONFIGURED remove_count)
            await self.memory.consolidate(
                summary,
                remove_count=self.reflection_config.remove_count
            )

            # 6. Emit Event
            await self.dispatcher.dispatch(CloudEvent.create(
                source=self.source_uri,
                type="agent.reflection",
                data={"summary": summary},
            ))
        except Exception as e:
            # Reflection shouldn't crash the agent
            # FIXED: Should emit event instead of just print
            error_event = CloudEvent.create(
                source=self.source_uri,
                type="agent.reflection.failed",
                data={"error": str(e)}
            )
            await self.dispatcher.dispatch(error_event)

    async def process(self, event: CloudEvent) -> Any:
        """
        Agent Loop with Memory:
        1. Receive Task -> Add to Memory
        2. Get Context from Memory
        3. Think (LLM)
        4. Tool Call -> Add Result to Memory
        5. Final Response
        """
        # Hook: Auto Reflection
        if self.enable_auto_reflection:
             await self._perform_reflection()
             
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
            
            # Check for Adaptive Control Overrides (from Interceptors)
            llm_config = event.extensions.get("llm_config_override")
            
            response = await self.provider.chat(messages, tools=mcp_tools, config=llm_config)
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
                        # FIXED: Use self.call() to invoke through event bus
                        # This ensures:
                        # - Tool calls are visible in Studio
                        # - Interceptors can control tool execution
                        # - Supports distributed tool nodes
                        # - Maintains fractal uniformity
                        try:
                            tool_result = await self.call(
                                target_node=target_tool.source_uri,
                                data={"arguments": tc_args}
                            )

                            # Extract result content
                            if isinstance(tool_result, dict):
                                result_content = tool_result.get("result", str(tool_result))
                            else:
                                result_content = str(tool_result)

                            # Add Result to Memory (Observation)
                            await self.memory.add("tool", str(result_content), metadata={
                                "tool_name": tc_name,
                                "tool_call_id": tc.get("id")
                            })
                        except Exception as e:
                            # Tool call failed through event bus
                            err_msg = f"Tool {tc_name} failed: {str(e)}"
                            await self.memory.add("system", err_msg)
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
             
        # Hook: Check reflection after new memories added
        if self.enable_auto_reflection:
             await self._perform_reflection()

        return {"response": final_response, "iterations": iterations}

