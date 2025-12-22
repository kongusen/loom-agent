
import asyncio
import os
from typing import Dict, Any, Optional, List
from pathlib import Path

# Loom Imports
from loom.builtin.llms.unified import UnifiedLLM
from loom.builtin.tools.base import BaseTool
from loom.execution.agent import Agent
from loom.patterns.composition import Sequence
from loom.core.message import UserMessage
from loom.core.runnable import RunnableConfig
from loom.skills.skill import Skill, SkillMetadata

# Configuration
API_KEY = "sk-9OepGVqrZzYYJsUR9NrxyJ15fR4BRblfFXCd3gmcu4cKbHoX"
BASE_URL = "https://api.ssopen.top/v1"
MODEL = "gpt-4o-mini"

# --- 1. Define Tool ---
class CalculatorTool(BaseTool):
    name: str = "calculator"
    description: str = "Useful for calculating math expressions. Input should be a valid python expression string."
    args_schema: type = type("Args", (), {"model_json_schema": lambda: {"type": "object", "properties": {"expression": {"type": "string"}}, "required": ["expression"]}})

    async def invoke(self, input: Dict[str, Any], config: Optional[RunnableConfig] = None, **kwargs) -> str:
        expression = input.get("expression", "")
        print(f"    [Tool:Calculator] Calculating: {expression}")
        try:
            # Safe eval
            allowed_names = {"abs": abs, "round": round, "min": min, "max": max}
            result = eval(expression, {"__builtins__": None}, allowed_names)
            return str(result)
        except Exception as e:
            return f"Error: {e}"

# --- 2. Define Skill (In-Memory) ---
def create_math_skill() -> Skill:
    metadata = SkillMetadata(
        name="MathExpert",
        description="Provides guidelines for solving math problems step-by-step.",
        category="logic",
        tags=["math", "logic"]
    )
    # We simulate a skill without a physical directory for this test
    skill = Skill(
        metadata=metadata,
        path=Path("."),
        quick_guide="Always use the calculator tool for calculations. Verify results."
    )
    # Inject detailed doc content manually for the prompt
    skill.detailed_doc = """
    # MathExpert Skill
    
    When solving math problems:
    1. Identify the core expression.
    2. detailed_doc content is usually read from file, here we mock it.
    3. YOU MUST USE THE calculator TOOL for any arithmetic. Do not calculate mentally.
    4. State the final answer clearly.
    """
    return skill

# --- 3. Main Test ---
async def main():
    print(f"\n🚀 Starting Advanced Capabilities Test (Real API: {MODEL})")
    
    # Init LLM
    llm = UnifiedLLM(
        provider="custom",
        api_key=API_KEY,
        base_url=BASE_URL,
        model=MODEL,
        temperature=0.7
    )
    print(f"✅ LLM Initialized: {llm.model_name}")

    # Prepare Skill Prompt
    math_skill = create_math_skill()
    skill_prompt_section = (
        "# Skills\n"
        f"{math_skill.to_system_prompt_entry()}\n"
        f"\nSkill Guidelines:\n{math_skill.detailed_doc}"
    )
    
    # Agent 1: Researcher (Solving the problem)
    researcher_system_prompt = (
        "You are a Researcher Agent. Use your skills and tools to solve problems.\n" 
        + skill_prompt_section
    )
    
    researcher = Agent(
        name="Researcher",
        llm=llm,
        tools=[CalculatorTool()],
        system_prompt=researcher_system_prompt
    )

    # Agent 2: Reviewer (Checking the answer)
    reviewer = Agent(
        name="Reviewer",
        llm=llm,
        system_prompt="You are a Reviewer Agent. Check the answer provided by the Researcher. If it looks correct, verify it and verify the tone is professional."
    )

    # Crew: Sequence
    crew = Sequence([researcher, reviewer])
    print("✅ Crew Assembled: Researcher -> Reviewer")

    # Execution
    task = "Calculate ((125 * 8) + 50) / 10 and explain the process."
    print(f"\n🎯 Task: {task}\n")
    
    try:
        # Run the crew
        # Note: In Sequence, output of step 1 is input to step 2.
        # Researcher returns AssistantMessage.
        # Reviewer takes AssistantMessage (or str) and returns AssistantMessage.
        result = await crew.invoke(task)
        
        print("\n\n🏁 Final Result from Crew:")
        print(f"Role: {result.role}")
        print(f"Content: {result.content}")
        
    except Exception as e:
        print(f"\n❌ Test Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
