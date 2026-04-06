# Skills (S)

Skills are the progressive disclosure mechanism for tools. Only skills matching the current task are loaded into `C_skill` — keeping the context window lean.

## How Skills Work

```
Task description
      │
      ▼
SkillRegistry.match(task)   ← keyword matching on when_to_use
      │
      ▼
Matching skills injected into C_skill
      │
      ▼
Model calls Skill tool to execute
```

## Defining a Skill (Markdown frontmatter)

```markdown
---
name: debug-assistant
description: Helps debug Python errors
when_to_use: [debug, error, traceback, exception]
allowed_tools: [read_file, run_command]
user_invocable: true
---

# Debug Assistant

Steps to diagnose and fix Python errors...
```

## Using Skills in Code

```python
from loom.ecosystem.skill import SkillRegistry, SkillLoader

registry = SkillRegistry()
SkillLoader.load_from_directory("skills/", registry)

matches = registry.find_matching("debug this traceback")
skill = registry.get("debug-assistant")   # lazy-loaded on first access
```

**Code:** `loom/ecosystem/skill.py`
