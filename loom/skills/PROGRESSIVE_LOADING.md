# Progressive Skill Loading

## Architecture

Three-layer progressive disclosure pattern:

### Layer 1: Discovery (Metadata Only)
- Load only `name` + `description`
- Minimal memory footprint
- Fast catalog browsing

### Layer 2: Activation (Full Instructions)
- Load complete `instructions` on-demand
- Triggered by `registry.activate(name)`
- Lazy resource loading

### Layer 3: Resources (Lazy Assets)
- Load scripts/references/assets only when accessed
- Future enhancement

## Usage

```python
from loom.skills import SkillRegistry, load_dir

# Layer 1: Load metadata only (fast)
registry = SkillRegistry()
skills = load_dir("./skills", metadata_only=True)
for skill in skills:
    registry.register(skill)

# Discovery prompt (lightweight)
prompt = registry.get_discovery_prompt()
# <available_skills>
#   <skill><name>debug</name><description>...</description></skill>
# </available_skills>

# Layer 2: Activate specific skill (lazy load instructions)
skill = registry.activate("debug")
if skill:
    print(skill.instructions)  # Now loaded

# Check active skills
active = registry.get_active()
```

## API Compatibility

```python
from loom.skills.loader import (
    query_skill_metadata,  # Layer 1
    list_skill_metadata,   # Layer 1 as dicts
    load_skill,            # Layer 2 (full load)
)

# For routes.py compatibility
metadata = list_skill_metadata("./skills")
skill = load_skill("debug", "./skills")
```

## Benefits

- **Fast startup**: Only parse frontmatter
- **Low memory**: Instructions loaded on-demand
- **Scalable**: Handle 100+ skills efficiently
- **Compatible**: Existing code works unchanged
