from typing import List, Optional, Union, Dict, Any
from loom.core.runnable import Runnable, RunnableConfig
from loom.core.message import Message, UserMessage, AssistantMessage
from loom.builtin.llms.base import BaseLLM
from loom.builtin.tools.base import BaseTool
from loom.builtin.memory.base import BaseMemory
from loom.execution.engine import RecursiveEngine

class Agent(Runnable[Union[str, Message], AssistantMessage]):
    """
    Agent component wrapping the RecursiveEngine.
    Implements the Runnable protocol for easy composition.
    """

    def __init__(
        self,
        name: str,
        llm: BaseLLM,
        tools: Optional[List[BaseTool]] = None,
        memory: Optional[BaseMemory] = None,
        system_prompt: Optional[str] = None,
        max_depth: int = 20,
        **kwargs # Forward compatible
    ):
        if not isinstance(llm, BaseLLM):
             raise TypeError(f"Agent 'llm' argument must be an instance of BaseLLM, got {type(llm)}. Please instantiate the LLM class directly (e.g. `llm = OpenAILLM(...)`).")

        self.name = name
        self.llm = llm
        self.tools = tools or []
        self.memory = memory
        self.system_prompt = system_prompt
        self.max_depth = max_depth
        
        # Initialize the Engine
        self.engine = RecursiveEngine(
            llm=self.llm,
            tools=self.tools,
            memory=self.memory,
            max_depth=max_depth,
            system_prompt=system_prompt
        )

    # _init_llm is no longer needed as we enforce BaseLLM in __init__

    async def invoke(
        self, 
        input: Union[str, Message], 
        config: Optional[RunnableConfig] = None, 
        **kwargs
    ) -> AssistantMessage:
        """
        Execute the agent.
        Converts string input to UserMessage if needed.
        """
        if isinstance(input, str):
            input_msg = UserMessage(content=input)
        else:
            input_msg = input
            
        return await self.engine.run(input_msg, config)
