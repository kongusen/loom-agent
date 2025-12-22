from typing import Any, List, Union, Callable, Dict, Optional
from loom.core.runnable import (
    Runnable, 
    RunnableSequence, 
    RunnableParallel, 
    RunnableBranch,
    RunnableConfig
)

# --- Sequence ---

class Sequence(RunnableSequence):
    """
    User-friendly wrapper for sequential composition.
    Output of step N becomes input of step N+1.
    """
    def __init__(self, steps: List[Runnable], **kwargs):
        super().__init__(steps=steps, **kwargs)

# --- Group ---

class Group(RunnableParallel):
    """
    User-friendly wrapper for parallel composition.
    Executes multiple runnables concurrently on the same input.
    Result is a dictionary mapping key to output.
    If aggregator is provided, passes the results dict to it.
    """
    def __init__(self, steps: Dict[str, Runnable], aggregator: Optional[Runnable] = None, **kwargs):
        super().__init__(runnables=steps, **kwargs)
        self.aggregator = aggregator

    async def invoke(self, input: Any, config: Optional[RunnableConfig] = None, **kwargs) -> Any:
        # Get results from parallel execution
        results = await super().invoke(input, config, **kwargs)
        
        # Aggregate if needed
        if self.aggregator:
            return await self.aggregator.invoke(results, config, **kwargs)
            
        return results

# --- Router ---

class Router(Runnable[Any, Any]):
    """
    Routes input to one of multiple runnables based on a condition.
    """
    
    def __init__(
        self, 
        routes: Dict[str, Runnable], 
        classifier: Callable[[Any], str],
        default: Optional[Runnable] = None
    ):
        """
        Args:
            routes: Map of route name to Runnable
            classifier: Function that takes input and returns route name
            default: Optional fallback Runnable if route name not found
        """
        self.routes = routes
        self.classifier = classifier
        self.default = default

    async def invoke(
        self, 
        input: Any, 
        config: Optional[RunnableConfig] = None, 
        **kwargs
    ) -> Any:
        route_key = self.classifier(input)
        target = self.routes.get(route_key, self.default)
        
        if not target:
             raise ValueError(f"No route found for key '{route_key}' and no default provided.")
             
        return await target.invoke(input, config, **kwargs)
