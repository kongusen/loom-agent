from loom.patterns.composition import Sequence

import asyncio
import loom
from loom import Message, Crew

async def main():
    # v0.2.0 style agent creation
    agent = Agent(
        name="TestBot",
        llm="gpt-4",
        tools=[]
    )
    
    # v0.2.0 style message and run
    msg = Message(role="user", content="Hello")
    reply = await agent.invoke(msg)
    
    # v0.2.0 style reply chaining
    reply2 = await reply.invoke( # TODO: Verify this was a reply "Follow up")
    
    # v0.2.0 style Crew
    crew = Crew(
        agents=[agent],
        workflow=Sequence([...]) # TODO: Fix arguments
    )
    
    result = await crew.invoke("Task")
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
