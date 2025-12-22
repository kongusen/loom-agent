import asyncio
from loom.execution import Agent
from loom.builtin.llms import UnifiedLLM

async def main():
    print("🚀 Testing Legacy Config (Should Fail)...")
    
    # Test 1: String config
    print("\n1️⃣  Testing Agent(llm='openai')...")
    try:
        agent = Agent(name="LegacyBot", llm="openai") # type: ignore
        print("❌ FAILED: Should have raised TypeError for string config")
    except TypeError as e:
        print(f"✅ PASSED: Caught expected error: {e}")
        
    # Test 2: Dict config
    print("\n2️⃣  Testing Agent(llm={'provider': 'openai'})...")
    try:
        agent = Agent(name="LegacyBot", llm={"provider": "openai", "api_key": "x"}) # type: ignore
        print("❌ FAILED: Should have raised TypeError for dict config")
    except TypeError as e:
        print(f"✅ PASSED: Caught expected error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
