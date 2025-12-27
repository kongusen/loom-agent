# Tutorial 3: Building Agent Teams

> **Learning Goal**: Understand the concept of Crew, learn to create and use Agent teams

## What is a Crew?

Crew is the collaboration unit of multiple Agents, it can:

- **Organize multiple Agents**: Combine multiple Agents into a team
- **Define collaboration patterns**: Control how Agents interact
- **Decompose complex tasks**: Assign complex tasks to different Agents

## Creating a Simple Crew

### Example: Sequential Execution Team

```python
from loom.weave import create_agent, create_crew, run

# Create two Agents
writer = create_agent("writer", role="content writer - responsible for writing articles")
reviewer = create_agent("reviewer", role="reviewer - responsible for reviewing and improving articles")

# Create Team
team = create_crew("writing-team", [writer, reviewer])

# Run Task
result = run(team, "Write a short article about AI")
print(result)
```

### Understand the Code

1. **Create Agent**: Create writer and reviewer Agents respectively
2. **create_crew()**: Combine Agent list into a team
3. **Sequential Execution**: Writer's output becomes Reviewer's input

### Execution Flow

```
Task → Writer Agent → Draft Article → Reviewer Agent → Improved Article
```

## Collaboration Patterns

Crew supports different collaboration patterns:

### Sequential Mode

Agents execute in order, the output of each Agent serves as input for the next Agent.

```python
# Default is sequential mode
team = create_crew("team", [agent1, agent2, agent3], pattern="sequential")
```

**Use Cases**:
- Writing → Review → Publish
- Research → Analysis → Report
- Design → Development → Testing

## Using Pre-built Crews

loom-agent provides some pre-built team patterns:

### Example: Debate Team

```python
from loom.weave import run
from loom.stdlib.crews import DebateCrew

# Create Debate Team
debate_team = DebateCrew("debate", topic="Will AI replace human jobs?")

# Run Debate
result = run(debate_team, "Start debate, each side presents 3 arguments")
print(result)
```

**How it works**:
- Automatically creates Pro and Con Agents
- Pro speaks first, Con responds
- Suitable for exploring multiple angles of an issue

## Combining Agents and Skills

Agents in a team can have different skills:

```python
from loom.weave import create_agent, create_crew, run
from loom.stdlib.skills import CalculatorSkill, FileSystemSkill

# Create Agents with different skills
analyst = create_agent("analyst", role="Data Analyst")
calc_skill = CalculatorSkill()
calc_skill.register(analyst)

writer = create_agent("writer", role="Report Writer")
fs_skill = FileSystemSkill(base_dir="./reports")
fs_skill.register(writer)

# Create Team
team = create_crew("analysis-team", [analyst, writer])

# Run Task
result = run(team, "Analyze mean of data [100, 200, 300], and write to report")
print(result)
```

## Next Steps

→ [Tutorial 4: Using YAML Configuration](yaml-configuration.md)
