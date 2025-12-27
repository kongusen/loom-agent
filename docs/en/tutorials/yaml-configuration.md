# Tutorial 4: Using YAML Configuration

> **Learning Goal**: Learn to use YAML files to configure Agents and Crews, implementing declarative management

## Why use YAML Configuration?

YAML configuration provides a declarative way to manage Agent systems:

- **Strong Readability**: Clear structure, easy to understand and maintain
- **Version Control**: Configuration files can be managed by Git
- **Environment Separation**: Use different configurations for development, testing, and production
- **Team Collaboration**: Non-programmers can also modify configuration

## Basic Configuration Structure

Create a `loom.yaml` file:

```yaml
version: "1.0"

# Control Configuration (Optional)
control:
  budget: 5000      # Token budget
  depth: 10         # Max depth

# Define Agents
agents:
  - name: my-agent
    role: "General Assistant"

# Define Crews (Optional)
crews:
  - name: my-team
    agents:
      - my-agent
```

## Loading Configuration File

Use `LoomApp.from_config()` to load configuration:

```python
from loom.api.main import LoomApp

# Load configuration file
app, agents, crews = LoomApp.from_config("loom.yaml")

# Get Agent
my_agent = agents["my-agent"]

# Run Task
result = await app.run(my_agent, "Hello")
print(result)
```

## Using Pre-built Agents

Configuration file supports using pre-built Agent types:

```yaml
agents:
  # Use CoderAgent
  - name: coder
    type: CoderAgent
    config:
      base_dir: ./src

  # Use AnalystAgent
  - name: analyst
    type: AnalystAgent
```

**Available Pre-built Types**:
- `CoderAgent`: Coding Agent with file operation capabilities
- `AnalystAgent`: Analyst Agent with calculation capabilities

## Using Custom Agents (with Skills)

You can also configure custom Agents via `role` and `skills`:

```yaml
agents:
  # Custom Calculation Assistant
  - name: calculator-agent
    role: "Calculation Assistant"
    skills:
      - calculator

  # Custom File Assistant
  - name: file-agent
    role: "File Assistant"
    skills:
      - filesystem
    config:
      base_dir: ./data
```

**Available Skills**:
- `calculator`: Math calculation capability
- `filesystem`: File read/write capability

## Configuring Crew

Define team in configuration file:

```yaml
agents:
  - name: writer
    role: "Content Creator"

  - name: reviewer
    role: "Reviewer"

crews:
  - name: writing-team
    agents:
      - writer
      - reviewer
```

Using configured Crew:

```python
from loom.api.main import LoomApp

app, agents, crews = LoomApp.from_config("loom.yaml")

# Get Crew
team = crews["writing-team"]

# Run Task
result = await app.run(team, "Write an article about Python")
print(result)
```

## Complete Example

Here is a complete configuration file example:

```yaml
version: "1.0"

control:
  budget: 5000
  depth: 10

agents:
  # Pre-built Agent
  - name: coder
    type: CoderAgent
    config:
      base_dir: ./src

  - name: analyst
    type: AnalystAgent

  # Custom Agent
  - name: calculator-agent
    role: "Calculation Assistant"
    skills:
      - calculator

crews:
  - name: dev-team
    agents:
      - coder
      - analyst
```

Using this configuration:

```python
from loom.api.main import LoomApp

# Load configuration
app, agents, crews = LoomApp.from_config("loom.yaml")

# Use single Agent
coder = agents["coder"]
result = await app.run(coder, "Create a hello.py file")

# Use Crew
team = crews["dev-team"]
result = await app.run(team, "Analyze and optimize code")
```

## Next Steps

🎉 Congratulations! You have completed all core tutorials.

**Continue Learning:**
- 📖 [How-to Guides](../guides/) - Solve specific problems
- 💡 [Concepts](../concepts/) - Deep dive into principles
- 📚 [Reference](../reference/) - Consult complete API
