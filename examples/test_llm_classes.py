import asyncio
import os
from loom.builtin.llms import CustomLLM, OpenAILLM
from loom.execution import Agent
from loom.core.message import UserMessage

async def main():
    print("🚀 Testing Class-First Architecture...")
    
    # 1. Test CustomLLM instantiation
    # Using the same custom endpoint as before
    api_key = "sk-9OepGVqrZzYYJsUR9NrxyJ15fR4BRblfFXCd3gmcu4cKbHoX"
    base_url = "https://api.ssopen.top/v1"
    
    print(f"\n1️⃣  Initializing CustomLLM with base_url={base_url}")
    llm = CustomLLM(
        api_key=api_key,
        base_url=base_url,
        model="gpt-4o-mini", # Explicitly set model
        temperature=0.5
    )
    
    print(f"   Model Name: {llm.model_name}")
    assert llm.model_name == "custom/gpt-4o-mini"
    
    # 2. Test Agent integration
    print("\n2️⃣  Initializing Agent with CustomLLM instance")
    agent = Agent(
        name="ClassBot",
        llm=llm
    )
    
    # 3. specific test invoke
    print("\n3️⃣  Invoking Agent...")
    response = await agent.invoke("Hello, say 'Class-First works!'")
    print(f"   Response: {response.content}")
    
    assert "Class-First works" in response.content or "works" in response.content
    print("\n✅ Verification Successful!")

if __name__ == "__main__":
    asyncio.run(main())
