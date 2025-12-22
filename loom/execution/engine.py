from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
import asyncio

from loom.core.message import (
    Message, 
    AssistantMessage, 
    ToolMessage, 
    ToolCall,
    SystemMessage
)
from loom.core.runnable import RunnableConfig
from loom.builtin.llms.base import BaseLLM
from loom.builtin.tools.base import BaseTool
from loom.builtin.memory.base import BaseMemory
from loom.execution.context import ContextAssembler, ContextConfig

@dataclass
class EngineState:
    """State of the recursive engine."""
    depth: int = 0
    total_tokens: int = 0
    tool_calls_count: int = 0
    messages: List[Message] = field(default_factory=list)
    initial_user_message: Optional[Message] = None

class RecursiveEngine:
    """
    Recursive Execution Engine.
    
    Orchestrates the Think -> Act -> Observe loop.
    """

    def __init__(
        self,
        llm: BaseLLM,
        tools: List[BaseTool],
        memory: Optional[BaseMemory] = None,
        max_depth: int = 20,
        system_prompt: Optional[str] = None
    ):
        self.llm = llm
        self.tools = tools or []
        self.memory = memory
        self.max_depth = max_depth
        self.system_prompt = system_prompt
        
        # Helper map for tools
        self.tool_map = {t.name: t for t in self.tools}
        
        # Context assembler
        self.context_assembler = ContextAssembler(
            config=ContextConfig(keep_recent_n=max_depth * 2) # Heuristic
        )

    async def run(
        self, 
        input: Message, 
        config: Optional[RunnableConfig] = None
    ) -> AssistantMessage:
        """
        Entry point for the execution loop.
        """
        state = EngineState()
        state.initial_user_message = input
        
        # Initialize state with input
        # Note: We keep input separate from history in complex implementations, 
        # but for simplicity here we treat it as the start of the session.
        state.messages.append(input)

        # Start recursion
        return await self._loop(state, config)

    async def _loop(
        self, 
        state: EngineState,
        config: Optional[RunnableConfig] = None
    ) -> AssistantMessage:
        """Core recursive loop."""
        
        # 1. Check Limits
        if state.depth >= self.max_depth:
            # TODO: Return a proper error message or partial result instead of raising
            raise RecursionError(f"Max recursion depth {self.max_depth} reached")
        
        state.depth += 1

        # 2. Assemble Context
        context = await self._assemble_context(state)

        # 3. Think (LLM Call)
        response = await self._think(context, config)
        state.messages.append(response)

        # 4. Check (Tool Calls?)
        if not response.tool_calls:
            # Base Case: No tools called, return final response
            return response

        # 5. Act (Execute Tools)
        tool_results = await self._act(response.tool_calls, config)
        state.messages.extend(tool_results)
        state.tool_calls_count += len(response.tool_calls)

        # 6. Observe (Optional: Sync to memory)
        await self._observe(tool_results)

        # 7. Loop (Recurse)
        return await self._loop(state, config)

    async def _assemble_context(self, state: EngineState) -> List[Message]:
        """Assemble context for the LLM."""
        
        # Retrieve relevant memory if enabled
        relevant_memory = []
        if self.memory and state.initial_user_message:
            query = state.initial_user_message.get_text_content()
            try:
                relevant_memory = await self.memory.retrieve(query, top_k=3)
            except Exception:
                # Log error but don't fail
                pass

        return self.context_assembler.assemble(
            system_prompt=self.system_prompt,
            history=state.messages,
            relevant_memory=relevant_memory
        )

    async def _think(
        self, 
        context: List[Message],
        config: Optional[RunnableConfig] = None
    ) -> AssistantMessage:
        """Call the LLM."""
        tools_schema = [t.get_openai_schema() for t in self.tools] if self.tools else None
        
        return await self.llm.invoke(
            input=context,
            config=config,
            tools=tools_schema
        )

    async def _act(
        self, 
        tool_calls: List[ToolCall],
        config: Optional[RunnableConfig] = None
    ) -> List[ToolMessage]:
        """Execute tools in parallel."""
        
        async def _execute_single(tc: ToolCall) -> ToolMessage:
            tool = self.tool_map.get(tc.function.name)
            if not tool:
                return ToolMessage(
                    tool_call_id=tc.id, 
                    content=f"Error: Tool {tc.function.name} not found"
                )
            
            try:
                # Parse arguments (assuming JSON string)
                import json
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                     return ToolMessage(
                        tool_call_id=tc.id,
                        content="Error: Invalid JSON arguments"
                    )

                result = await tool.invoke(args, config)
                return ToolMessage(tool_call_id=tc.id, content=result)
            except Exception as e:
                return ToolMessage(
                    tool_call_id=tc.id,
                    content=f"Error executing tool: {str(e)}"
                )

        # Parallel execution
        if config and config.max_concurrency:
            semaphore = asyncio.Semaphore(config.max_concurrency)
            
            async def _execute_with_limit(tc):
                async with semaphore:
                    return await _execute_single(tc)
            
            tasks = [_execute_with_limit(tc) for tc in tool_calls]
        else:
            tasks = [_execute_single(tc) for tc in tool_calls]
            
        return await asyncio.gather(*tasks)

    async def _observe(self, tool_results: List[ToolMessage]):
        """Callback for memory or logging."""
        if self.memory:
            for msg in tool_results:
                await self.memory.add_message(msg)
