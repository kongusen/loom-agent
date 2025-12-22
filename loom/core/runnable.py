from typing import (
    TypeVar, Generic, Optional, AsyncGenerator,
    Dict, Any, Callable, Awaitable, Union, List
)
from abc import abstractmethod, ABC
from dataclasses import dataclass, field
import asyncio

InputT = TypeVar('InputT', contravariant=True)
OutputT = TypeVar('OutputT', covariant=True)

@dataclass
class RunnableConfig:
    """Unified runtime configuration for all Runnable components."""
    # Execution control
    max_concurrency: Optional[int] = None
    timeout: Optional[float] = None  # seconds
    retry_on_error: bool = False
    max_retries: int = 3

    # Context propagation
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    run_id: Optional[str] = None

    # Callback system
    callbacks: List[Callable] = field(default_factory=list)

    # Observability
    enable_tracing: bool = True
    trace_level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR

    # Recursion control
    max_depth: int = 20
    current_depth: int = 0


class Runnable(ABC, Generic[InputT, OutputT]):
    """
    Base abstract class for all executable components.

    Philosophy:
    - Single Responsibility: Only defines execution interface
    - Type Safety: Generics support input/output type constraints
    - Composable: Supports sequential, parallel, and conditional execution
    """

    @abstractmethod
    async def invoke(
        self,
        input: InputT,
        config: Optional[RunnableConfig] = None,
        **kwargs
    ) -> OutputT:
        """
        Execute the runnable.

        Args:
            input: Input data
            config: Runtime configuration
            **kwargs: Additional arguments (backward compatibility)

        Returns:
            Output data

        Raises:
            RunnableError: If execution fails
        """
        ...

    async def stream(
        self,
        input: InputT,
        config: Optional[RunnableConfig] = None,
        **kwargs
    ) -> AsyncGenerator[OutputT, None]:
        """
        Stream the execution output.
        Default implementation returns result as a single chunk.

        Args:
            input: Input data
            config: Runtime configuration

        Yields:
            Output chunks
        """
        result = await self.invoke(input, config, **kwargs)
        yield result

    async def batch(
        self,
        inputs: List[InputT],
        config: Optional[RunnableConfig] = None,
        **kwargs
    ) -> List[OutputT]:
        """
        Execute a batch of inputs.

        Args:
            inputs: List of inputs
            config: Runtime configuration

        Returns:
            List of outputs (preserving order)
        """
        if config and config.max_concurrency:
            # Limit concurrency
            semaphore = asyncio.Semaphore(config.max_concurrency)

            async def _execute_with_limit(inp):
                async with semaphore:
                    return await self.invoke(inp, config, **kwargs)

            return await asyncio.gather(*[_execute_with_limit(inp) for inp in inputs])
        else:
            # Unlimited concurrency
            return await asyncio.gather(*[self.invoke(inp, config, **kwargs) for inp in inputs])


# Combinators

class RunnableSequence(Runnable[InputT, OutputT]):
    """
    Sequential composition: output = step3(step2(step1(input)))

    Example:
        pipeline = RunnableSequence([researcher, analyzer, writer])
        result = await pipeline.invoke("Research AI")
    """

    def __init__(self, steps: List[Runnable]):
        self.steps = steps

    async def invoke(self, input: InputT, config: Optional[RunnableConfig] = None, **kwargs) -> OutputT:
        result = input
        for step in self.steps:
            # Check if previous result needs to be passed, or if we need to handle specific logic
            # For now, simplistic chaining
            result = await step.invoke(result, config, **kwargs)
        return result


class RunnableParallel(Runnable[InputT, Dict[str, Any]]):
    """
    Parallel composition: {k1: r1(input), k2: r2(input), ...}

    Example:
        parallel = RunnableParallel({
            "facts": researcher,
            "sentiment": sentiment_analyzer
        })
        result = await parallel.invoke("Analyze this text")
        # result = {"facts": [...], "sentiment": "positive"}
    """

    def __init__(self, runnables: Dict[str, Runnable]):
        self.runnables = runnables

    async def invoke(self, input: InputT, config: Optional[RunnableConfig] = None, **kwargs) -> Dict[str, Any]:
        tasks = {
            key: runnable.invoke(input, config, **kwargs)
            for key, runnable in self.runnables.items()
        }
        # Gather all results
        # Note: dict ordering is preserved in modern Python
        keys = list(tasks.keys())
        coroutines = list(tasks.values())
        results = await asyncio.gather(*coroutines)
        return dict(zip(keys, results))


class RunnableBranch(Runnable[InputT, OutputT]):
    """
    Conditional branching: if condition(input) then branch_a else branch_b

    Example:
        router = RunnableBranch(
            condition=lambda x: "code" in x.lower(),
            if_true=code_agent,
            if_false=chat_agent
        )
    """

    def __init__(
        self,
        condition: Callable[[InputT], Union[bool, Awaitable[bool]]],
        if_true: Runnable[InputT, OutputT],
        if_false: Runnable[InputT, OutputT]
    ):
        self.condition = condition
        self.if_true = if_true
        self.if_false = if_false

    async def invoke(self, input: InputT, config: Optional[RunnableConfig] = None, **kwargs) -> OutputT:
        # Support both sync and async conditions
        cond_result = self.condition(input)
        if asyncio.iscoroutine(cond_result):
            cond_result = await cond_result

        branch = self.if_true if cond_result else self.if_false
        return await branch.invoke(input, config, **kwargs)
