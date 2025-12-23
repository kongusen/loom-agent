# Multi-Agent Crew Example

This example demonstrates how to orchestrate multiple agents to perform a complex task: Researching a topic and writing a summary.

## The Goal
1. **Researcher Agent**: Takes a topic, simulates "searching", and produces key facts.
2. **Writer Agent**: Takes the facts and writes a polished blog post.
3. **Crew**: Orchestrates them sequentially.

## `crew_example.py`

```python
import asyncio
from loom.api.main import LoomApp
from loom.node.agent import AgentNode
from loom.node.crew import CrewNode
from loom.infra.llm.mock import MockLLMProvider  # Using Mock for runnable demo without keys

# 1. Setup Mock Providers to simulate intelligent behavior
researcher_llm = MockLLMProvider([
    "Thought: I need to find facts about AI.",
    "Final Answer: FACT 1: AI is growing. FACT 2: Transformers are key."
])

writer_llm = MockLLMProvider([
    "Thought: I will write a blog post using these facts.",
    "Final Answer: # The Future of AI\n\nAI is growing rapidly, driven by Transformer architecture..."
])

async def main():
    app = LoomApp()

    # 2. Define Agents
    researcher = AgentNode(
        "researcher", 
        app.dispatcher, 
        role="Researcher",
        provider=researcher_llm,
        system_prompt="Find key facts."
    )
    
    writer = AgentNode(
        "writer", 
        app.dispatcher, 
        role="Writer", 
        provider=writer_llm,
        system_prompt="Write a blog post based on facts."
    )
    app.add_node(researcher)
    app.add_node(writer)

    # 3. Define Crew (Sequential Pattern)
    # Flow: Input -> Researcher -> (Facts) -> Writer -> (Blog Post) -> Output
    crew = CrewNode(
        "content-crew",
        app.dispatcher,
        agents=[researcher, writer],
        pattern="sequential"
    )
    app.add_node(crew)

    # 4. Run
    print("Starting Content Crew...")
    result = await app.run("Hype about AI agents", "content-crew")
    
    print("\n--- Final Output ---")
    print(result["final_output"])
    
    print("\n--- Execution Trace ---")
    for step in result["trace"]:
        print(f"[{step['agent']}]: {step['output'][:50]}...")

if __name__ == "__main__":
    asyncio.run(main())
```
