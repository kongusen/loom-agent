"""08 - Skill System

Demonstrates the Skill system for progressive disclosure of tools.

Skills are markdown files with YAML frontmatter that define:
- name: unique identifier
- description: what the skill does
- whenToUse: keywords for matching
- allowedTools: tools this skill can use

Run:
    python examples/08_skill_system.py
"""

import asyncio
from loom.tools.builtin.skill_operations import skill_discover, skill_invoke


async def main():
    print("=== Skill Discovery ===")

    # Discover all available skills
    result = await skill_discover()

    if result["success"]:
        print(f"Found {result['count']} skills:\n")
        for skill in result["skills"]:
            print(f"  • {skill['name']}")
            print(f"    Description: {skill['description']}")
            print(f"    When to use: {skill['when_to_use']}")
            print(f"    Allowed tools: {skill['allowed_tools']}")
            print()
    else:
        print(f"Discovery failed: {result.get('message', 'Unknown error')}")
        return

    print("\n=== Skill Invocation ===")

    # Invoke a specific skill
    skill_name = "code-reviewer"
    print(f"Invoking skill: {skill_name}\n")

    result = await skill_invoke(skill_name)

    if result["success"]:
        print(f"Skill: {result['skill']}")
        print(f"Description: {result['description']}")
        print(f"Allowed tools: {result['allowed_tools']}")
        print(f"Content length: {len(result['content'])} chars")
        print(f"\nFirst 200 chars of content:")
        print(result['content'][:200] + "...")
    else:
        print(f"Invocation failed: {result.get('error', 'Unknown error')}")
        if "available_skills" in result:
            print(f"Available skills: {result['available_skills']}")

    print("\n=== Skill with Arguments ===")

    # Test argument substitution (if skill supports it)
    result = await skill_invoke("debug-assistant", args="TypeError in app.py")

    if result["success"]:
        print(f"Skill: {result['skill']}")
        print(f"Args: {result['args']}")
        print(f"Content includes args: {'$ARGUMENTS' not in result['content']}")


asyncio.run(main())
