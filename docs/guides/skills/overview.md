# Agent Skills System Guide

## Overview

The Loom Skills system provides a modular way to extend agent capabilities through filesystem-based skills. Skills are specialized knowledge modules that agents can discover and use on-demand, following a three-layer progressive disclosure pattern for optimal context management.

### Key Features

- **Progressive Disclosure**: Three-layer architecture (50 tokens → 500-2K tokens → unlimited)
- **Zero Intrusion**: Skills integrate through filesystem and system prompts, no code modifications needed
- **Auto-Discovery**: Skills are automatically loaded from the `skills/` directory
- **Context Efficient**: Only load detailed information when needed
- **Easy Management**: Create, enable, disable, and edit skills programmatically or manually

## Quick Start

### Using Skills with SimpleAgent

```python
import loom
from loom.builtin.llms import OpenAILLM

# Create agent with skills enabled (default behavior)
agent = loom.agent(
    name="assistant",
    llm=OpenAILLM(api_key="..."),
    enable_skills=True,
    skills_dir="./skills"  # Optional, defaults to "./skills"
)

# Skills are automatically loaded and included in system prompt
print(agent.get_stats()["skills"])
# Output: {'total_skills': 3, 'enabled_skills': 3, 'disabled_skills': 0, 'categories': 2}
```

### How Skills Work

When you create a `SimpleAgent` with skills enabled:

1. **Layer 1 (System Prompt)**: Agent sees a compact index of all skills (~50 tokens each)
   ```
   Available Skills:

   - **pdf_analyzer**: Analyze and extract information from PDF documents
     💡 Quick: Use PyPDF2 or pdfplumber to extract text, tables, and metadata
     📄 Details: `cat skills/pdf_analyzer/SKILL.md`
     📦 Resources: `ls skills/pdf_analyzer/resources/`
   ```

2. **Layer 2 (On-Demand)**: When needed, agent reads detailed documentation
   ```python
   # Agent naturally uses bash to read details:
   # cat skills/pdf_analyzer/SKILL.md
   ```

3. **Layer 3 (Deep Dive)**: Agent accesses specific resource files
   ```python
   # Agent reads specific resources:
   # cat skills/pdf_analyzer/resources/examples.json
   ```

## Skill Structure

Each skill follows this directory structure:

```
skills/
  skill_name/
    skill.yaml         # Metadata + quick guide
    SKILL.md          # Detailed documentation (Layer 2)
    resources/        # Additional files (Layer 3)
      examples.json
      templates/
      data/
```

### skill.yaml Format

```yaml
metadata:
  name: skill_name
  description: Brief description (1-2 sentences)
  category: tools|analysis|communication|general
  version: 1.0.0
  author: Your Name
  tags:
    - tag1
    - tag2
  dependencies: []  # Other skills this depends on
  enabled: true

quick_guide: "Brief usage hint (1-2 sentences) that appears in Layer 1"
```

### SKILL.md Format

```markdown
# Skill Name

Brief overview paragraph.

## Overview

Detailed overview with bullet points of capabilities.

## Usage

### Section 1: Basic Usage

Code examples and explanations.

### Section 2: Advanced Usage

More complex examples.

## Examples

Link to resources or inline examples.

## Dependencies

List required packages.

## Notes

Important considerations, best practices, gotchas.
```

## Using Skills

### Listing Available Skills

```python
# List all enabled skills
skills = agent.list_skills()
for skill in skills:
    print(f"- {skill.metadata.name}: {skill.metadata.description}")

# List skills by category
analysis_skills = agent.list_skills(category="analysis")
tool_skills = agent.list_skills(category="tools")
```

### Getting Skill Details

```python
# Get specific skill
skill = agent.get_skill("pdf_analyzer")

# Access metadata
print(skill.metadata.name)
print(skill.metadata.description)
print(skill.metadata.tags)

# Load detailed documentation (Layer 2)
detailed_doc = skill.load_detailed_doc()
print(detailed_doc)

# Access resources (Layer 3)
examples_path = skill.get_resource_path("examples.json")
if examples_path:
    with open(examples_path) as f:
        examples = json.load(f)
```

### Managing Skills

```python
# Enable a skill
agent.enable_skill("web_research")

# Disable a skill
agent.disable_skill("pdf_analyzer")

# Reload all skills (after manual edits)
agent.reload_skills()

# Get skills statistics
stats = agent.get_stats()["skills"]
print(f"Total: {stats['total_skills']}, Enabled: {stats['enabled_skills']}")
```

## Creating Skills

### Method 1: Programmatic Creation

```python
# Create a new skill
skill = agent.create_skill(
    name="database_query",
    description="Query and analyze SQL databases",
    category="tools",
    quick_guide="Use SQLAlchemy for connection and pandas for results",
    detailed_content="""# Database Query

Query and analyze SQL databases.

## Usage

```python
from sqlalchemy import create_engine
import pandas as pd

engine = create_engine('postgresql://user:pass@localhost/db')
df = pd.read_sql("SELECT * FROM users", engine)
```

## Notes

- Always use parameterized queries to prevent SQL injection
- Close connections after use
- Consider connection pooling for multiple queries
""",
    tags=["database", "sql", "query"],
    author="Your Name"
)

print(f"Created skill: {skill.metadata.name}")
```

### Method 2: Manual Creation

1. Create the directory structure:
```bash
mkdir -p skills/my_skill/resources
```

2. Create `skill.yaml`:
```yaml
metadata:
  name: my_skill
  description: What this skill does
  category: tools
  version: 1.0.0
  author: Your Name
  tags:
    - tag1
  dependencies: []
  enabled: true

quick_guide: "One-line usage hint"
```

3. Create `SKILL.md`:
```markdown
# My Skill

Detailed documentation here...
```

4. Add resources (optional):
```bash
# Add example files, templates, data
touch skills/my_skill/resources/examples.json
```

5. Reload skills:
```python
agent.reload_skills()
```

## Best Practices

### 1. Progressive Disclosure

Design skills to follow the three-layer pattern:

- **Layer 1**: Minimal info (~50 tokens) in system prompt
  - Name, description, quick guide
  - Just enough to know when to use the skill

- **Layer 2**: Detailed docs (~500-2K tokens) in SKILL.md
  - Usage examples, API reference
  - Load only when agent needs details

- **Layer 3**: Resources (unlimited) in resources/
  - Templates, data files, examples
  - Access specific files as needed

### 2. Naming Conventions

- Use `snake_case` for skill names
- Choose descriptive, action-oriented names
- Examples: `pdf_analyzer`, `web_research`, `data_processor`

### 3. Documentation Quality

- Write clear, concise descriptions
- Include practical code examples
- Document dependencies explicitly
- Add notes about edge cases and limitations

### 4. Categories

Standard categories:
- `tools`: General-purpose tools
- `analysis`: Analysis and processing skills
- `communication`: Communication and integration skills
- `general`: Miscellaneous skills

### 5. Resource Organization

```
resources/
  examples/        # Example inputs/outputs
  templates/       # Reusable templates
  data/           # Reference data
  configs/        # Configuration files
```

### 6. Dependencies

- List skill dependencies in metadata
- Document external package requirements
- Include installation instructions

## Advanced Usage

### Conditional Skill Loading

```python
# Load skills only for specific agents
research_agent = loom.agent(
    name="researcher",
    llm=llm,
    enable_skills=True,
    skills_dir="./skills/research"  # Separate skill set
)

coding_agent = loom.agent(
    name="coder",
    llm=llm,
    enable_skills=True,
    skills_dir="./skills/coding"  # Different skill set
)
```

### Dynamic Skill Management

```python
# Enable skills based on task
def prepare_agent_for_task(agent, task_type):
    if task_type == "research":
        agent.enable_skill("web_research")
        agent.enable_skill("pdf_analyzer")
        agent.disable_skill("data_processor")
    elif task_type == "analysis":
        agent.enable_skill("data_processor")
        agent.disable_skill("web_research")

    return agent
```

### Skill Metadata Editing

```python
from loom.skills import SkillManager

skill_mgr = SkillManager("./skills")
skill_mgr.load_all()

# Edit skill metadata
skill_mgr.edit_skill_metadata(
    "pdf_analyzer",
    description="Updated description",
    tags=["pdf", "document", "analysis", "extraction", "new-tag"]
)
```

## Examples

### Example 1: Using PDF Analyzer

```python
import loom
from loom.builtin.llms import OpenAILLM
from loom.core.message import Message

agent = loom.agent(
    name="doc_assistant",
    llm=OpenAILLM(api_key="..."),
    enable_skills=True
)

# Agent has pdf_analyzer skill in Layer 1 (system prompt)
# When user asks to analyze a PDF, agent:
# 1. Sees pdf_analyzer in available skills
# 2. Reads SKILL.md for detailed instructions
# 3. Accesses resources/examples.json for patterns
# 4. Executes the appropriate code

message = Message(
    role="user",
    content="Extract all tables from invoice.pdf and summarize totals"
)

response = await agent.run(message)
print(response.content)
```

### Example 2: Creating a Custom Skill

```python
# Create a skill for API integration
api_skill = agent.create_skill(
    name="rest_api_client",
    description="Make HTTP requests to REST APIs with authentication",
    category="tools",
    quick_guide="Use requests library with proper headers and error handling",
    detailed_content="""# REST API Client

Make authenticated HTTP requests to REST APIs.

## Usage

```python
import requests

def api_call(url, method='GET', headers=None, data=None):
    response = requests.request(
        method=method,
        url=url,
        headers=headers or {},
        json=data,
        timeout=30
    )
    response.raise_for_status()
    return response.json()
```

## Authentication

- Bearer tokens: `headers={'Authorization': 'Bearer TOKEN'}`
- API keys: `headers={'X-API-Key': 'KEY'}` or `params={'api_key': 'KEY'}`
- Basic auth: `auth=('username', 'password')`

## Notes

- Always set timeouts
- Handle rate limiting (429 status)
- Validate response status codes
- Log requests for debugging
""",
    tags=["api", "http", "rest", "integration"]
)

# Add example configurations
import json
with open(agent.skill_manager.skills_dir / "rest_api_client" / "resources" / "api_configs.json", "w") as f:
    json.dump({
        "github": {
            "base_url": "https://api.github.com",
            "auth_type": "bearer",
            "rate_limit": 5000
        },
        "openai": {
            "base_url": "https://api.openai.com/v1",
            "auth_type": "bearer",
            "rate_limit": 10000
        }
    }, f, indent=2)

agent.reload_skills()
```

### Example 3: Skills in Multi-Agent System

```python
from loom.patterns import Crew
from loom.patterns.crew_role import CrewRole

# Create specialized agents with different skills
researcher = loom.agent(
    name="researcher",
    llm=llm,
    skills_dir="./skills"
)
researcher.disable_skill("data_processor")  # Only research skills

analyst = loom.agent(
    name="analyst",
    llm=llm,
    skills_dir="./skills"
)
analyst.disable_skill("web_research")  # Only analysis skills

# Create crew with specialized agents
crew = Crew(
    agents={
        "researcher": researcher,
        "analyst": analyst
    },
    llm=llm
)

# Researcher uses web_research and pdf_analyzer skills
# Analyst uses data_processor skill
result = await crew.execute(
    "Research AI trends and analyze the data"
)
```

## Troubleshooting

### Skills Not Loading

```python
# Check if skills directory exists
import os
print(os.path.exists("./skills"))

# Check skill manager status
print(agent.skill_manager)
print(agent.get_stats()["skills"])

# Try reloading
agent.reload_skills()
```

### Skill Not Appearing in System Prompt

```python
# Check if skill is enabled
skill = agent.get_skill("skill_name")
print(f"Enabled: {skill.metadata.enabled}")

# Enable it
agent.enable_skill("skill_name")

# Check system prompt
print(agent.system_prompt)
```

### Invalid skill.yaml

```python
# Validate YAML syntax
import yaml
with open("skills/skill_name/skill.yaml") as f:
    try:
        data = yaml.safe_load(f)
        print("Valid YAML:", data)
    except yaml.YAMLError as e:
        print("Invalid YAML:", e)
```

## API Reference

### SimpleAgent Methods

#### `list_skills(category: Optional[str] = None) -> List[Skill]`
List available skills, optionally filtered by category.

#### `get_skill(name: str) -> Optional[Skill]`
Get a specific skill by name.

#### `reload_skills() -> None`
Reload all skills from disk.

#### `enable_skill(name: str) -> bool`
Enable a skill. Returns True if successful.

#### `disable_skill(name: str) -> bool`
Disable a skill. Returns True if successful.

#### `create_skill(name: str, description: str, category: str = "general", **kwargs) -> Skill`
Create a new skill programmatically.

### SkillManager

#### `load_all() -> None`
Load all skills from the skills directory.

#### `get_system_prompt_section(enabled_only: bool = True, include_quick_guide: bool = True) -> str`
Generate the skills section for system prompt (Layer 1).

#### `create_skill(name: str, description: str, category: str = "general", **kwargs) -> Skill`
Create a new skill with directory structure.

#### `delete_skill(name: str) -> bool`
Delete a skill and its directory.

#### `edit_skill_metadata(name: str, **updates) -> bool`
Edit skill metadata fields.

### Skill

#### `load_detailed_doc() -> str`
Load the detailed documentation (SKILL.md) for Layer 2.

#### `get_resource_path(resource_name: str) -> Optional[Path]`
Get the path to a resource file in Layer 3.

#### `to_system_prompt_entry() -> str`
Generate the Layer 1 system prompt entry for this skill.

### SkillMetadata

Data class containing:
- `name: str` - Unique skill identifier
- `description: str` - Brief description
- `category: str` - Skill category
- `version: str` - Version string
- `author: Optional[str]` - Author name
- `tags: List[str]` - Searchable tags
- `dependencies: List[str]` - Required skills
- `enabled: bool` - Whether skill is active

## Conclusion

The Skills system provides a powerful, flexible way to extend agent capabilities while maintaining efficient context usage. By following the three-layer progressive disclosure pattern, agents can discover and use skills intelligently without context bloat.

Key takeaways:
- Skills are filesystem-based and zero-intrusion
- Progressive disclosure keeps context efficient
- Easy to create, manage, and customize
- Works seamlessly with single agents and multi-agent crews
- Supports both programmatic and manual management

For more examples, see the built-in skills in `skills/` directory:
- `pdf_analyzer` - PDF document analysis
- `web_research` - Web search and scraping
- `data_processor` - Data transformation and analysis
