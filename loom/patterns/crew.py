from typing import Any, Optional, Dict, List
from loom.core.runnable import Runnable, RunnableConfig
from loom.core.message import Message, AssistantMessage
from loom.builtin.memory.base import BaseMemory

class Crew(Runnable[Any, Any]):
    """
    A Crew is a lightweight container that orchestrates a workflow.
    It provides a shared memory space for the agents involved in the workflow.
    """

    def __init__(
        self,
        workflow: Runnable,
        memory: Optional[BaseMemory] = None,
        name: str = "Crew"
    ):
        self.workflow = workflow
        self.memory = memory
        self.name = name

    async def invoke(
        self,
        input: Any,
        config: Optional[RunnableConfig] = None,
        **kwargs
    ) -> Any:
        """
        Execute the crew's workflow.
        """
        # In a more complex implementation, we might inject the memory 
        # into the config or context of the runnables here.
        # For now, we simply delegate to the workflow.
        
        # TODO: Potential hook for setting up shared state
        
        result = await self.workflow.invoke(input, config, **kwargs)
        
        # TODO: Potential hook for tearing down or persisting state
        
        return result
