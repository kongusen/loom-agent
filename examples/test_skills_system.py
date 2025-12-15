"""
Skills System Integration Test

This script demonstrates the Loom Skills system functionality.
"""

import asyncio
import loom
from loom.builtin.llms import OpenAILLM
from loom.core.message import Message


async def test_skills_system():
    """Test the Skills system integration"""

    print("=" * 60)
    print("LOOM SKILLS SYSTEM TEST")
    print("=" * 60)
    print()

    # 1. Create agent with skills enabled
    print("1. Creating agent with Skills enabled...")
    agent = loom.agent(
        name="assistant",
        llm=OpenAILLM(api_key="test-key"),  # Mock LLM for testing
        enable_skills=True,
        skills_dir="./skills"
    )
    print(f"   ✓ Agent created: {agent.name}")
    print()

    # 2. Check loaded skills
    print("2. Checking loaded skills...")
    stats = agent.get_stats()
    if "skills" in stats:
        skills_stats = stats["skills"]
        print(f"   ✓ Total skills: {skills_stats['total_skills']}")
        print(f"   ✓ Enabled skills: {skills_stats['enabled_skills']}")
        print(f"   ✓ Categories: {skills_stats['categories']}")
    else:
        print("   ✗ Skills not loaded")
    print()

    # 3. List all skills
    print("3. Listing all skills...")
    skills = agent.list_skills()
    for skill in skills:
        print(f"   - {skill.metadata.name} ({skill.metadata.category})")
        print(f"     {skill.metadata.description}")
        print(f"     Tags: {', '.join(skill.metadata.tags)}")
    print()

    # 4. Get specific skill details
    print("4. Getting pdf_analyzer skill details...")
    pdf_skill = agent.get_skill("pdf_analyzer")
    if pdf_skill:
        print(f"   ✓ Name: {pdf_skill.metadata.name}")
        print(f"   ✓ Category: {pdf_skill.metadata.category}")
        print(f"   ✓ Version: {pdf_skill.metadata.version}")
        print(f"   ✓ Quick guide: {pdf_skill.quick_guide}")
        print(f"   ✓ Resources: {len(pdf_skill.resources)} files")
    print()

    # 5. Load detailed documentation
    print("5. Loading detailed documentation (Layer 2)...")
    detailed_doc = pdf_skill.load_detailed_doc()
    print(f"   ✓ Documentation loaded: {len(detailed_doc)} characters")
    print(f"   Preview: {detailed_doc[:100]}...")
    print()

    # 6. Access resources
    print("6. Accessing skill resources (Layer 3)...")
    examples_path = pdf_skill.get_resource_path("examples.json")
    if examples_path:
        print(f"   ✓ Examples file found: {examples_path}")
        import json
        with open(examples_path) as f:
            examples = json.load(f)
            print(f"   ✓ Loaded {len(examples.get('common_patterns', []))} example patterns")
    print()

    # 7. Test skill management
    print("7. Testing skill management...")

    # Disable a skill
    result = agent.disable_skill("web_research")
    print(f"   {'✓' if result else '✗'} Disabled web_research")

    # Enable it back
    result = agent.enable_skill("web_research")
    print(f"   {'✓' if result else '✗'} Enabled web_research")
    print()

    # 8. Check system prompt
    print("8. Checking system prompt integration...")
    system_prompt = agent.system_prompt
    if "Available Skills" in system_prompt:
        print("   ✓ Skills section found in system prompt")
        # Count skill entries
        skill_count = system_prompt.count("📄 Details:")
        print(f"   ✓ Skills in prompt: {skill_count}")
    else:
        print("   ✗ Skills section not found in system prompt")
    print()

    # 9. Create a new skill
    print("9. Creating a new skill programmatically...")
    try:
        new_skill = agent.create_skill(
            name="test_skill",
            description="A test skill for demonstration",
            category="general",
            quick_guide="This is a test skill",
            tags=["test", "demo"]
        )
        print(f"   ✓ Created skill: {new_skill.metadata.name}")

        # Verify it exists
        test_skill = agent.get_skill("test_skill")
        print(f"   ✓ Verified skill exists: {test_skill is not None}")

        # Clean up - delete the test skill
        agent.skill_manager.delete_skill("test_skill")
        print("   ✓ Cleaned up test skill")
    except Exception as e:
        print(f"   ✗ Failed to create skill: {e}")
    print()

    # 10. Final statistics
    print("10. Final statistics...")
    final_stats = agent.get_stats()
    print(f"   Agent: {agent.name}")
    print(f"   Tools: {final_stats['num_tools']}")
    if "skills" in final_stats:
        skills_stats = final_stats["skills"]
        print(f"   Skills: {skills_stats['enabled_skills']}/{skills_stats['total_skills']} enabled")
    print()

    print("=" * 60)
    print("SKILLS SYSTEM TEST COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    # Note: This test uses a mock LLM key
    # For actual usage, provide a real OpenAI API key
    print("Note: Using mock LLM key for testing skills system only")
    print("For actual agent execution, provide a real API key")
    print()

    asyncio.run(test_skills_system())
