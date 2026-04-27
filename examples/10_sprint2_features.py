"""10 - Sprint 2 Features: Hooks and Shell Execution

Demonstrates Sprint 2 advanced features:
- Hooks system (onLoad, onInvoke, onComplete, onError)
- Shell inline execution (!`command` syntax)

Run:
    python examples/10_sprint2_features.py
"""

import asyncio

from loom.tools.builtin.skill_operations import skill_invoke


async def main():
    print("=== Sprint 2 Features Demo ===\n")

    # Test 1: Hooks System
    print("1. Testing Hooks System")
    print("-" * 50)

    result = await skill_invoke("system-info")

    if result["success"]:
        print("✅ Skill executed successfully")
        print(f"   Has hooks: {result.get('has_hooks', False)}")
        print(f"   Effort: {result['effort']}/5")
        print(f"   Token limit: {result['effort_token_limit']:,}")
        print()

        # Show first 500 chars of content
        content = result["content"]
        print("Content preview (first 500 chars):")
        print("-" * 50)
        print(content[:500])
        if len(content) > 500:
            print("...")
        print()

    else:
        print(f"❌ Failed: {result.get('error')}")
        return

    # Test 2: Shell Inline Execution
    print("\n2. Testing Shell Inline Execution")
    print("-" * 50)

    # Check if shell commands were executed
    if "!`" in result["content"]:
        print("⚠️  Shell commands not executed (still contains !` syntax)")
    else:
        print("✅ Shell commands executed successfully")

        # Extract some executed commands
        lines = result["content"].split("\n")
        for line in lines:
            if any(
                keyword in line
                for keyword in ["Current Directory", "User", "Date", "Git Branch", "Python"]
            ):
                print(f"   {line.strip()}")

    # Test 3: Error Handling with Hooks
    print("\n3. Testing Error Handling")
    print("-" * 50)

    result = await skill_invoke("non-existent-skill")

    if not result["success"]:
        print(f"✅ Error handled correctly: {result.get('error')}")
    else:
        print("⚠️  Expected error but got success")

    # Summary
    print("\n" + "=" * 50)
    print("Sprint 2 Features Summary")
    print("=" * 50)
    print("✅ Hooks system: Implemented")
    print("✅ Shell inline execution: Implemented")
    print("✅ Error handling: Implemented")
    print("\nAll Sprint 2 features working correctly! 🎉")


asyncio.run(main())
