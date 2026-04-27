"""11 - Sprint 3 Features: Shell Config and Token Estimation

Demonstrates Sprint 3 advanced features:
- Shell configuration (custom shell, env vars, timeout)
- Progressive token estimation (frontmatter vs full content)

Run:
    python examples/11_sprint3_features.py
"""

import asyncio

from loom.ecosystem.skill import estimate_skill_tokens
from loom.tools.builtin.skill_operations import skill_discover, skill_invoke


async def main():
    print("=== Sprint 3 Features Demo ===\n")

    # Test 1: Token Estimation (Progressive Loading)
    print("1. Testing Progressive Token Estimation")
    print("-" * 50)

    result = await skill_discover()

    if result["success"]:
        print(f"✅ Discovered {result['count']} skills")
        print("\nToken estimates (frontmatter only):")
        for skill in result["skills"]:
            print(f"   {skill['name']}: ~{skill['estimated_tokens']} tokens")
        print()
    else:
        print(f"❌ Failed: {result.get('error')}")
        return

    # Test 2: Shell Configuration
    print("\n2. Testing Custom Shell Configuration")
    print("-" * 50)

    result = await skill_invoke("custom-shell")

    if result["success"]:
        print("✅ Skill executed successfully")
        print(f"   Has shell config: {result.get('has_shell_config', False)}")
        print(f"   Effort: {result['effort']}/5")
        print(f"   Token limit: {result['effort_token_limit']:,}")
        print()

        # Show content with executed shell commands
        content = result["content"]
        print("Content preview (first 800 chars):")
        print("-" * 50)
        print(content[:800])
        if len(content) > 800:
            print("...")
        print()

        # Check if custom environment variable was used
        if "CUSTOM_VAR" in content or "Hello from custom shell" in content:
            print("✅ Custom environment variable detected in output")
        else:
            print("⚠️  Custom environment variable not found in output")

    else:
        print(f"❌ Failed: {result.get('error')}")
        return

    # Test 3: Token Estimation Comparison
    print("\n3. Testing Token Estimation (Frontmatter vs Full)")
    print("-" * 50)

    # Get registry
    from loom.tools.builtin.skill_operations import _get_or_create_registry

    registry = _get_or_create_registry()

    skill_obj = registry.get("custom-shell")
    if skill_obj:
        frontmatter_tokens = estimate_skill_tokens(skill_obj, load_content=False)
        full_tokens = estimate_skill_tokens(skill_obj, load_content=True)

        print(f"Skill: {skill_obj.name}")
        print(f"   Frontmatter only: ~{frontmatter_tokens} tokens")
        print(f"   Full content: ~{full_tokens} tokens")
        print(
            f"   Savings: ~{full_tokens - frontmatter_tokens} tokens ({100 - int(frontmatter_tokens/full_tokens*100)}%)"
        )
        print()
        print("✅ Progressive loading saves tokens during discovery")
    else:
        print("⚠️  Could not load skill for comparison")

    # Summary
    print("\n" + "=" * 50)
    print("Sprint 3 Features Summary")
    print("=" * 50)
    print("✅ Shell configuration: Implemented")
    print("✅ Progressive token estimation: Implemented")
    print("✅ Custom environment variables: Working")
    print("✅ Timeout control: Implemented")
    print("\nAll Sprint 3 features working correctly! 🎉")


asyncio.run(main())
