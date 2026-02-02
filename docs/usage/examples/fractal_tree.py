"""
Fractal Tree Example

This example demonstrates how to build a fractal tree of agents using CompositeNode.
We will create a 'Research Team' composed of a 'Supervisor', a 'Researcher', and a 'Writer'.
"""

import asyncio

from loom.agent import Agent
from loom.fractal.composite import CompositeNode
from loom.fractal.strategies import ParallelStrategy
from loom.providers.llm import OpenAIProvider
from loom.types.core import Task


async def main():
    # 1. Setup LLM Provider
    llm = OpenAIProvider(api_key="sk-mock", model="gpt-4")  # Use mock key for example

    # 2. Create Leaf Agents
    researcher = Agent.from_llm(
        llm=llm,
        node_id="researcher",
        system_prompt="You find facts.",
    )

    writer = Agent.from_llm(
        llm=llm,
        node_id="writer",
        system_prompt="You write reports based on facts.",
    )

    # 3. Create a Composite Node (The Team)
    # This team executes the researcher and writer in parallel (for demonstration)
    # Realistically, you might want Sequential: Research -> Write.
    team_node = CompositeNode(
        node_id="research_team",
        agent_card=None,  # Composite nodes might not need a card if they are just containers
        children=[researcher, writer],
        strategy=ParallelStrategy(),
    )

    # 4. Execute
    task = Task(
        id="task_1",
        action="execute_task",
        data={"instruction": "Research AI history and write a short summary."},
    )

    print("Starting Fractal Execution...")
    result = await team_node.execute_task(task)
    print("Execution Complete:", result)


if __name__ == "__main__":
    asyncio.run(main())
