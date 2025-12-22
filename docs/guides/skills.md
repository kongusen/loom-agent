# Skill System Guide

Skills are higher-level bundles of capabilities than Tools. While a Tool is a single function, a Skill can contain multiple tools, domain-specific prompts, and documentation.

## 1. Concept

- **Tool**: "Hammer". A specific function (`calculator`).
- **Skill**: "Carpenter". A bundle of tools (`hammer`, `saw`) + knowledge ("How to build a table").

## 2. Using Skills

Skills are typically loaded via the `SkillManager`, but can be manually defined.

```python
from loom.skills import Skill, SkillManager

# 1. Define a Skill manually
coding_skill = Skill(
    name="PythonCoding",
    description="Ability to write and execute Python code",
    tools=[run_python_code],
    prompts={"system": "You are a Python expert..."}
)

# 2. Inject into Agent
agent = Agent(
    name="Coder",
    llm=llm,
    skills=[coding_skill]
)
```

## 3. The Skill Manager

For larger agents, you don't want to load every tool at once. The `SkillManager` allows dynamic discovery.

```python
manager = SkillManager(skill_dir="./my_skills")

# Find relevant skills for a task
relevant_skills = await manager.retrieve("analyze data")
agent.add_skills(relevant_skills)
```

## 4. Skill Directory Structure

A standard skill on disk looks like this:

```
my_skills/
  data_analysis/
    skill.yaml       # Metadata
    tools.py         # @tool definitions
    prompts.yaml     # System prompts
    docs/            # RAG documents
```
