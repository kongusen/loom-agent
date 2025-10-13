import asyncio
import pytest

import loom
from loom.builtin.llms import MockLLM


@pytest.mark.asyncio
async def test_agent_minimal_with_mockllm():
    agent = loom.agent(llm=MockLLM(responses=["hello"]))
    out = await agent.ainvoke("Say anything")
    assert out == "hello"

