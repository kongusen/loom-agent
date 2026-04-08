"""09 - Advanced Skill Features

Demonstrates advanced skill features:
- Effort levels (1-5) for token budget control
- Agent types (general-purpose, code-expert)
- Execution contexts (inline, fork, isolated)
- Path restrictions
- Version control

Run:
    python examples/09_advanced_skills.py
"""

import asyncio

from loom.tools.builtin.skill_operations import skill_discover, skill_invoke


async def main():
    print("=== Advanced Skill Features ===\n")

    # Discover all skills
    result = await skill_discover()

    if not result["success"]:
        print(f"Discovery failed: {result.get('message', 'Unknown error')}")
        return

    # Filter skills with advanced features
    advanced_skills = [
        s for s in result["skills"]
        if s.get("effort") or s.get("agent") or s.get("paths")
    ]

    print(f"Found {len(advanced_skills)} skills with advanced features:\n")

    for skill in advanced_skills:
        print(f"📦 {skill['name']}")
        print(f"   Description: {skill['description']}")

        if skill.get("effort"):
            print(f"   💪 Effort: {skill['effort']}/5")

        if skill.get("agent"):
            print(f"   🤖 Agent: {skill['agent']}")

        if skill.get("context"):
            print(f"   🔒 Context: {skill['context']}")

        if skill.get("paths"):
            print(f"   📁 Paths: {skill['paths']}")

        if skill.get("version"):
            print(f"   🏷️  Version: {skill['version']}")

        print()

    # Test effort levels
    print("\n=== Effort Level Demonstration ===\n")

    # High effort skill
    print("1. High Effort Skill (complex-analysis)")
    result = await skill_invoke("complex-analysis")
    if result["success"]:
        print(f"   Effort: {result['effort']}/5")
        print(f"   Token Limit: {result['effort_token_limit']:,} tokens")
        print(f"   Agent: {result['agent']}")
        print(f"   Context: {result['context']}")
        print(f"   Paths: {result['paths']}")
        print()

    # Low effort skill
    print("2. Low Effort Skill (quick-fix)")
    result = await skill_invoke("quick-fix")
    if result["success"]:
        print(f"   Effort: {result['effort']}/5")
        print(f"   Token Limit: {result['effort_token_limit']:,} tokens")
        print(f"   Agent: {result['agent']}")
        print(f"   Context: {result['context']}")
        print()

    # Compare token budgets
    print("\n=== Effort Level Token Budgets ===\n")
    from loom.ecosystem.skill import get_effort_token_limit

    for level in range(1, 6):
        tokens = get_effort_token_limit(level)
        print(f"   Level {level}: {tokens:>6,} tokens")

    print(f"   Default: {get_effort_token_limit(None):>6,} tokens")


asyncio.run(main())
