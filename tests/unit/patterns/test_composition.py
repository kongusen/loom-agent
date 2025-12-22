import pytest
from typing import Dict, Any
from loom.core.runnable import Runnable
from loom.patterns.composition import Sequence, Group, Router

# --- Mocks ---
class AddOne(Runnable):
    async def invoke(self, input: int, config=None, **kwargs) -> int:
        return input + 1

class MultiplyByTwo(Runnable):
    async def invoke(self, input: int, config=None, **kwargs) -> int:
        return input * 2

class Echo(Runnable):
    async def invoke(self, input: Any, config=None, **kwargs) -> Any:
        return f"Echo: {input}"

# --- Tests ---

@pytest.mark.asyncio
async def test_sequence():
    """Verify Sequence combinator: (x + 1) * 2"""
    seq = Sequence([AddOne(), MultiplyByTwo()])
    
    # (10 + 1) * 2 = 22
    result = await seq.invoke(10)
    assert result == 22

@pytest.mark.asyncio
async def test_group():
    """Verify Group combinator: Parallel execution"""
    grp = Group(steps={
        "plus": AddOne(),
        "times": MultiplyByTwo()
    })
    
    # plus: 10 + 1 = 11
    # times: 10 * 2 = 20
    result = await grp.invoke(10)
    assert result == {"plus": 11, "times": 20}

@pytest.mark.asyncio
async def test_router():
    """Verify Router combinator: Conditional branching"""
    router = Router(
        routes={
            "math": AddOne(),
            "text": Echo()
        },
        classifier=lambda x: "math" if isinstance(x, int) else "text"
    )
    
    # Case 1: Math
    assert await router.invoke(10) == 11
    
    # Case 2: Text
    assert await router.invoke("hello") == "Echo: hello"
    
    # Case 3: Missing route (should error without default)
    router_no_default = Router(
        routes={"math": AddOne()},
        classifier=lambda x: "unknown"
    )
    with pytest.raises(ValueError):
        await router_no_default.invoke(10)
