# Loom Skills Directory

This directory contains modular skills that can be used by Loom agents. Skills provide specialized capabilities and knowledge that agents can discover and use on-demand.

## Available Skills

### pdf_analyzer (analysis)
Analyze and extract information from PDF documents including text, tables, and metadata.

**Quick Guide**: Use PyPDF2 or pdfplumber to extract text, tables, and metadata from PDF files. Check resources/examples.json for common patterns.

**When to Use**: Document processing, invoice extraction, resume parsing, contract analysis

---

### web_research (tools)
Conduct web research and gather information from online sources using search APIs and web scraping.

**Quick Guide**: Use search APIs (Google, Bing) for queries, requests/beautifulsoup4 for scraping, and selenium for dynamic content. See resources/search_templates.json for query patterns.

**When to Use**: Market research, competitive analysis, fact-checking, trend analysis

---

### data_processor (tools)
Process and transform structured data from CSV, JSON, and Excel formats.

**Quick Guide**: Use pandas for tabular data, json module for JSON, and openpyxl for Excel. Check resources/transformation_patterns.json for common operations.

**When to Use**: Data cleaning, ETL pipelines, data aggregation, format conversion

---

## How Skills Work

Skills follow a **three-layer progressive disclosure** pattern:

### Layer 1: Index (~50 tokens)
- Appears in agent's system prompt
- Includes: name, description, quick guide
- Agent knows: when to use each skill

### Layer 2: Detailed Docs (~500-2K tokens)
- Stored in `SKILL.md`
- Agent reads via: `cat skills/<skill_name>/SKILL.md`
- Includes: usage examples, API reference, notes

### Layer 3: Resources (unlimited)
- Stored in `resources/` directory
- Agent accesses via: `cat skills/<skill_name>/resources/<file>`
- Includes: templates, examples, reference data

## Skill Structure

Each skill follows this directory structure:

```
skills/
  skill_name/
    skill.yaml         # Metadata + quick guide (Layer 1)
    SKILL.md          # Detailed documentation (Layer 2)
    resources/        # Additional files (Layer 3)
      examples.json
      templates/
      data/
```

## Creating New Skills

### Option 1: Programmatically

```python
import loom

agent = loom.agent(name="assistant", llm=llm)

skill = agent.create_skill(
    name="my_skill",
    description="What this skill does",
    category="tools",
    quick_guide="Brief usage hint",
    tags=["tag1", "tag2"]
)
```

### Option 2: Manually

1. Create directory structure:
```bash
mkdir -p skills/my_skill/resources
```

2. Create `skill.yaml`:
```yaml
metadata:
  name: my_skill
  description: Brief description
  category: tools
  version: 1.0.0
  enabled: true
quick_guide: "Usage hint"
```

3. Create `SKILL.md` with detailed documentation

4. Add resources as needed

5. Reload in agent:
```python
agent.reload_skills()
```

## Using Skills

Skills are automatically loaded when you create a `SimpleAgent`:

```python
import loom

agent = loom.agent(
    name="assistant",
    llm=llm,
    enable_skills=True,        # Default
    skills_dir="./skills"      # Default
)

# List available skills
skills = agent.list_skills()

# Get specific skill
skill = agent.get_skill("pdf_analyzer")

# Enable/disable skills
agent.enable_skill("web_research")
agent.disable_skill("data_processor")
```

## Documentation

- **Full Guide**: `docs/guides/skills_system.md`
- **Quick Reference**: `docs/guides/skills_quick_reference.md`

## Categories

Standard skill categories:
- **tools**: General-purpose tools and utilities
- **analysis**: Analysis and processing capabilities
- **communication**: Communication and integration skills
- **general**: Miscellaneous skills

## Best Practices

1. **Keep Layer 1 minimal** - System prompt should be concise
2. **Document thoroughly** - Clear examples in SKILL.md
3. **Organize resources** - Group related files in subdirectories
4. **Tag appropriately** - Use descriptive tags for discoverability
5. **Version skills** - Update version when making changes
6. **Test thoroughly** - Verify skills work as documented

## Contributing Skills

When creating new skills:

1. Follow the three-layer structure
2. Use clear, descriptive names (snake_case)
3. Write comprehensive SKILL.md documentation
4. Include practical code examples
5. Document dependencies and installation
6. Add relevant resources (examples, templates, data)
7. Test with actual agents before committing

## License

All skills in this directory follow the same license as the Loom framework.
