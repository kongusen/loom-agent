"""
Loom Skills - "The Knowledge"
=============================

This module provides the "Skill System", a way to dynamically inject capabilities and knowledge into Agents.

## 📚 Core Concepts

### 1. Skill (`Skill`)
A bundle of knowledge and capabilities. Unlike simple Tools, a Skill can contain:
- **Tools**: Executable functions.
- **Prompts**: Domain-specific instructions.
- **Resources**: Documentation or Data.

### 2. SkillManager (`SkillManager`)
The librarian that retrieves relevant skills for the Agent.
- **Discovery**: Finds skills based on query.
- **Injection**: Injects selected skills into the Agent's context.

## 🚀 Usage Pattern
```python
from loom.skills import Skill, SkillManager

# 1. Define or Load Skills
# (Usually loaded from a directory)

# 2. Equip Agent
agent = Agent(
    ...,
    skills=[math_skill, coding_skill]
)
```
"""

from loom.skills.skill import Skill, SkillMetadata
from loom.skills.manager import SkillManager

__all__ = [
    "Skill",
    "SkillMetadata",
    "SkillManager",
]
