# Skills

Skills are markdown files with YAML frontmatter that provide progressive disclosure of tools and capabilities.

## Available Skills

### code-reviewer
Reviews Python code for quality, style, and best practices.

**When to use:** review, code review, check code, improve code, refactor

**Allowed tools:** Read, Grep

### debug-assistant
Helps debug Python errors and exceptions.

**When to use:** debug, error, traceback, exception, bug, fix

**Allowed tools:** Read, Bash, Grep

## Creating Your Own Skills

Create a markdown file with YAML frontmatter:

```markdown
---
name: my-skill
description: What this skill does
whenToUse: keyword1, keyword2, keyword3
allowedTools: [Read, Write, Bash]
userInvocable: true
---

# My Skill

Instructions for the AI agent when this skill is invoked...
```

Place the file in:
- `skills/my-skill.md` (root level)
- `skills/my-skill/SKILL.md` (subdirectory)
- `~/.loom/skills/` (user-level)

## Using Skills

```python
from loom.tools.builtin.skill_operations import skill_discover, skill_invoke

# Discover all skills
result = await skill_discover()
print(f"Found {result['count']} skills")

# Invoke a skill
result = await skill_invoke("code-reviewer")
if result["success"]:
    print(result["content"])
```

See [08_skill_system.py](../08_skill_system.py) for a complete example.
