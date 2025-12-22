
import pytest
import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from loom.core.runnable import (
    Runnable, RunnableConfig, RunnableSequence, RunnableParallel, RunnableBranch
)

# --- Mock Runnables for Testing ---

@dataclass
class AddRunnable(Runnable[int, int]):
    value: int

    async def invoke(self, input: int, config: Optional[RunnableConfig] = None, **kwargs) -> int:
        return input + self.value

@dataclass
class MultiplyRunnable(Runnable[int, int]):
    value: int

    async def invoke(self, input: int, config=None, **kwargs) -> int:
        return input * self.value

@dataclass
class DictRunnable(Runnable[str, Dict[str, str]]):
    suffix: str

    async def invoke(self, input: str, config=None, **kwargs) -> Dict[str, str]:
        return {"result": input + self.suffix}

# --- Tests ---

@pytest.mark.asyncio
async def test_runnable_sequence():
    # input -> +1 -> *2 -> output
    # 5 -> 6 -> 12
    seq = RunnableSequence([
        AddRunnable(1),
        MultiplyRunnable(2)
    ])
    result = await seq.invoke(5)
    assert result == 12

@pytest.mark.asyncio
async def test_runnable_parallel():
    # input: 10
    # branch1: +5 -> 15
    # branch2: *2 -> 20
    parallel = RunnableParallel({
        "add": AddRunnable(5),
        "mult": MultiplyRunnable(2)
    })
    result = await parallel.invoke(10)
    assert result == {"add": 15, "mult": 20}

@pytest.mark.asyncio
async def test_runnable_branch():
    # Condition: x > 10
    # True: * 2
    # False: + 1
    
    branch = RunnableBranch(
        condition=lambda x: x > 10,
        if_true=MultiplyRunnable(2),
        if_false=AddRunnable(1)
    )

    # Case 1: 5 (False) -> 5 + 1 = 6
    assert await branch.invoke(5) == 6

    # Case 2: 20 (True) -> 20 * 2 = 40
    assert await branch.invoke(20) == 40

@pytest.mark.asyncio
async def test_runnable_batch():
    runner = AddRunnable(10)
    inputs = [1, 2, 3]
    results = await runner.batch(inputs)
    assert results == [11, 12, 13]

@pytest.mark.asyncio
async def test_runnable_stream():
    runner = AddRunnable(10)
    chunks = []
    async for chunk in runner.stream(5):
        chunks.append(chunk)
    assert chunks == [15]
