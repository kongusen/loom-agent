# Skills System Quick Reference

## Basic Setup

```python
import loom
from loom.builtin.llms import OpenAILLM

agent = loom.agent(
    name="assistant",
    llm=OpenAILLM(api_key="..."),
    enable_skills=True,        # Enable skills (default)
    skills_dir="./skills"      # Skills directory (default)
)
```

## Common Operations

### List Skills
```python
# All enabled skills
skills = agent.list_skills()

# By category
analysis_skills = agent.list_skills(category="analysis")
```

### Get Skill Details
```python
skill = agent.get_skill("pdf_analyzer")
print(skill.metadata.description)
doc = skill.load_detailed_doc()
```

### Enable/Disable Skills
```python
agent.enable_skill("web_research")
agent.disable_skill("pdf_analyzer")
```

### Create New Skill
```python
skill = agent.create_skill(
    name="my_skill",
    description="What it does",
    category="tools",
    quick_guide="Brief usage hint",
    tags=["tag1", "tag2"]
)
```

### Reload Skills
```python
agent.reload_skills()  # After manual edits
```

## Skill Structure

```
skills/
  my_skill/
    skill.yaml         # Metadata + quick guide
    SKILL.md          # Detailed docs (Layer 2)
    resources/        # Files (Layer 3)
      examples.json
```

## skill.yaml Template

```yaml
metadata:
  name: my_skill
  description: Brief description (1-2 sentences)
  category: tools  # tools|analysis|communication|general
  version: 1.0.0
  author: Your Name
  tags:
    - tag1
    - tag2
  dependencies: []
  enabled: true

quick_guide: "One-line usage hint"
```

## SKILL.md Template

```markdown
# Skill Name

Brief overview.

## Overview

- Capability 1
- Capability 2

## Usage

### Basic Usage
```python
# Code example
```

## Dependencies

- package1: `pip install package1`

## Notes

- Important consideration 1
- Important consideration 2
```

## Progressive Disclosure Pattern

1. **Layer 1** (~50 tokens): System prompt shows skill index
   - Agent sees: name, description, quick guide
   - Knows: when to use this skill

2. **Layer 2** (~500-2K tokens): SKILL.md
   - Agent reads: `cat skills/my_skill/SKILL.md`
   - Gets: detailed usage, examples, API

3. **Layer 3** (unlimited): resources/
   - Agent accesses: `cat skills/my_skill/resources/file.json`
   - Uses: templates, data, examples

## Statistics

```python
stats = agent.get_stats()["skills"]
print(f"Total: {stats['total_skills']}")
print(f"Enabled: {stats['enabled_skills']}")
print(f"Categories: {stats['categories']}")
```

## Manual Skill Creation

```bash
# 1. Create structure
mkdir -p skills/my_skill/resources

# 2. Create skill.yaml
cat > skills/my_skill/skill.yaml << 'EOF'
metadata:
  name: my_skill
  description: What it does
  category: tools
  version: 1.0.0
  enabled: true
quick_guide: "Usage hint"
EOF

# 3. Create SKILL.md
cat > skills/my_skill/SKILL.md << 'EOF'
# My Skill
Documentation here...
EOF

# 4. Add resources
touch skills/my_skill/resources/examples.json
```

## Built-in Example Skills

### pdf_analyzer
```python
# Analyze PDF documents
# Category: analysis
# Uses: PyPDF2, pdfplumber
```

### web_research
```python
# Web search and scraping
# Category: tools
# Uses: requests, beautifulsoup4, selenium
```

### data_processor
```python
# Data transformation and analysis
# Category: tools
# Uses: pandas, openpyxl
```

## Best Practices

1. **Keep Layer 1 minimal** - Only essential info in quick_guide
2. **Use descriptive names** - `pdf_analyzer` not `pdf_tool`
3. **Document dependencies** - List all required packages
4. **Add examples** - In SKILL.md and resources/
5. **Tag appropriately** - For discoverability
6. **Version your skills** - Update version when changing

## Troubleshooting

```python
# Skills not loading?
print(agent.skill_manager)
agent.reload_skills()

# Skill not in system prompt?
agent.enable_skill("skill_name")
print(agent.system_prompt)

# Check skill status
skill = agent.get_skill("skill_name")
print(f"Enabled: {skill.metadata.enabled}")
```

## Common Patterns

### Dynamic Skill Management
```python
def configure_for_task(agent, task_type):
    if task_type == "research":
        agent.enable_skill("web_research")
        agent.enable_skill("pdf_analyzer")
    elif task_type == "analysis":
        agent.enable_skill("data_processor")
```

### Specialized Agents
```python
# Research agent - only research skills
researcher = loom.agent(
    name="researcher",
    llm=llm,
    skills_dir="./skills/research"
)

# Analyst - only analysis skills
analyst = loom.agent(
    name="analyst",
    llm=llm,
    skills_dir="./skills/analysis"
)
```

## API Quick Reference

| Method | Description |
|--------|-------------|
| `list_skills(category=None)` | List available skills |
| `get_skill(name)` | Get specific skill |
| `enable_skill(name)` | Enable a skill |
| `disable_skill(name)` | Disable a skill |
| `create_skill(name, description, ...)` | Create new skill |
| `reload_skills()` | Reload from disk |

---

For detailed documentation, see `docs/guides/skills_system.md`
