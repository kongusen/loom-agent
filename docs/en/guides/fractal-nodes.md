# Fractal Nodes - Quick Start Guide

## Overview

Fractal Nodes enable **self-organizing agent structures** that dynamically adapt to task complexity. The system provides three usage modes:

1. **Automatic Mode**: Auto-decompose complex tasks (triggered by System 2)
2. **Manual Mode**: Build custom pipelines with full control
1.  **Automatic Mode**: Auto-decompose complex tasks (triggered by System 2)
2.  **Manual Mode**: Build custom pipelines with full control
3.  **Hybrid Mode**: Combine manual structure with auto-growth

---

## Installation

No additional installation needed - fractal nodes are natively integrated into the `AgentNode`.

```python
from loom.node import AgentNode
from loom.config.fractal import FractalConfig

# Standard agents have fractal capabilities built-in
agent = AgentNode(...)
agent.enable_fractal_mode()
```

---

## Quick Start

### 1. Automatic Fractal Mode (Simplest)

Let the agent automatically decompose complex tasks:

```python
import asyncio
from loom.llm.openai import OpenAIProvider
from loom.node import create_fractal_agent
from loom.config.fractal import GrowthTrigger

async def main():
    llm = OpenAIProvider(model="gpt-4")

    # Create auto-fractal agent
    agent = await create_fractal_agent(
        node_id="auto_agent",
        llm=llm,
        enable_fractal=True,
        fractal_trigger=GrowthTrigger.SYSTEM2,  # Trigger on System 2
        max_depth=3,
        max_children=5
    )

    # Simple task - direct execution
    result1 = await agent.execute("What is 2+2?")

    # Complex task - auto-decomposition
    result2 = await agent.execute("""
        Research quantum computing, analyze impact on cryptography,
        ML, and drug discovery, then create a comprehensive report
    """)

    # View generated structure
    if result2.get('structure'):
        print(agent.visualize_structure())

asyncio.run(main())
```

### 2. Manual Pipeline Building

Build custom agent pipelines:

```python
from loom.node import build_pipeline

async def main():
    llm = OpenAIProvider(model="gpt-4")

    # Build a research pipeline
    pipeline = (
        build_pipeline("research", llm)
        .coordinator("orchestrator")
        .parallel([
            ("ai_research", "specialist"),
            ("market_research", "specialist"),
            ("tech_research", "specialist")
        ])
        .aggregator("synthesizer")
        .build()
    )

    # Execute with manual task assignment
    results = await pipeline.execute_pipeline([
        "Research AI trends",
        "Analyze market data",
        "Identify tech opportunities"
    ], mode="parallel")

asyncio.run(main())
```

### 3. Using Templates

Quick pipeline creation with templates:

```python
from loom.node import PipelineTemplate

# Sequential processing
pipeline = PipelineTemplate.sequential_pipeline(
    name="analysis",
    llm=llm,
    steps=["collect", "analyze", "report"]
)

# Parallel research
pipeline = PipelineTemplate.research_pipeline(
    name="research",
    llm=llm,
    domains=["healthcare", "finance", "education"]
)

# Iterative refinement
pipeline = PipelineTemplate.iterative_refinement(
    name="refine",
    llm=llm,
    iterations=3
)
```

---

## Configuration Options

### FractalConfig

```python
from loom.config.fractal import FractalConfig, GrowthTrigger

config = FractalConfig(
    # Enable/disable fractal mode
    enabled=True,

    # When to trigger auto-growth
    growth_trigger=GrowthTrigger.SYSTEM2,  # SYSTEM2 | ALWAYS | MANUAL | NEVER

    # Structure limits
    max_depth=3,              # Maximum tree depth
    max_children=5,           # Max children per node
    max_total_nodes=20,       # Max total nodes

    # Growth thresholds
    complexity_threshold=0.7, # Task complexity (0-1) to trigger growth
    confidence_threshold=0.6, # Min confidence to NOT grow

    # Auto-pruning
    enable_auto_pruning=True,
    pruning_threshold=0.3,    # Min fitness to keep node

    # Tracking
    track_metrics=True,
    enable_visualization=True
)
```

### Growth Triggers

- **SYSTEM2**: Trigger when System 2 is activated (recommended)
- **ALWAYS**: Always evaluate for growth
- **MANUAL**: Only when explicitly requested
- **NEVER**: Disable auto-growth

### YAML Configuration

You can configure fractal settings directly in your `agent.yaml`:

```yaml
agents:
  - name: "deep-researcher"
    role: "Researcher"
    fractal:
      enabled: true
      growth_trigger: "system2"
      max_depth: 3
      max_children: 5
      complexity_threshold: 0.7
```

---

## Advanced Usage

### Hybrid Approach (Manual + Auto)

```python
# Create manual base structure
pipeline = (
    build_pipeline("hybrid", llm)
    .coordinator("main")
    .executor("researcher")
    .executor("analyzer")
    .build()
)

# Enable auto-growth on specific nodes
auto_config = FractalConfig(
    enabled=True,
    growth_trigger=GrowthTrigger.ALWAYS,
    max_depth=4
)

pipeline.children[0].fractal_config = auto_config  # Auto-grow researcher
```

### Runtime Enhancement

Add fractal capabilities to existing agents:

```python
from loom.node import add_fractal_to_agent

# Create standard agent
agent = AgentNode(...)

# Add fractal capabilities
add_fractal_to_agent(
    agent,
    enable=True,
    growth_trigger=GrowthTrigger.SYSTEM2,
    max_depth=3
)

# Now agent has fractal methods
agent.should_use_fractal(task)
agent.get_fractal_config()
```

### Custom Node Roles

```python
from loom.config.fractal import NodeRole

# Available roles
NodeRole.COORDINATOR  # Task decomposer
NodeRole.SPECIALIST   # Domain expert
NodeRole.EXECUTOR     # Task executor
NodeRole.AGGREGATOR   # Result synthesizer
```

---

## Monitoring & Debugging

### Structure Visualization

```python
# Tree view
print(agent.visualize_structure(format="tree"))

# Compact view
print(agent.visualize_structure(format="compact"))

# Get structure data
tree = agent.get_structure_tree()
```

### Performance Metrics

```python
# Node metrics
metrics = agent.metrics.to_dict()
print(f"Tasks: {metrics['task_count']}")
print(f"Success rate: {metrics['success_rate']}")
print(f"Fitness: {metrics['fitness_score']}")

# System 2 integration stats (if using FractalSystem2Node)
stats = agent.get_activation_stats()
print(f"System 2 activations: {stats['system2_activations']}")
print(f"Fractal activations: {stats['fractal_activations']}")
```

---

## Best Practices

### 1. Choose the Right Trigger

- **System 2**: Best for general use (auto-adapt to complexity)
- **Always**: For experimentation and learning optimal structures
- **Manual**: For production pipelines with known structure
- **Never**: For simple, single-task agents

### 2. Set Appropriate Limits

```python
# Conservative (production)
FractalConfig(max_depth=2, max_children=3, max_total_nodes=10)

# Moderate (default)
FractalConfig(max_depth=3, max_children=5, max_total_nodes=20)

# Aggressive (research)
FractalConfig(max_depth=5, max_children=7, max_total_nodes=50)
```

### 3. Monitor Performance

```python
# Track fitness scores
if agent.metrics.fitness_score() < 0.5:
    print("⚠️ Low fitness - consider adjusting structure")

# Enable visualization during development
config.enable_visualization = True  # See structure changes

# Disable in production for performance
config.enable_visualization = False
```

### 4. Start Simple

```python
# Start with manual pipeline
pipeline = build_pipeline(...).coordinator(...).executor(...).build()

# Add auto-growth gradually
pipeline.fractal_config.enabled = True
pipeline.fractal_config.growth_trigger = GrowthTrigger.SYSTEM2
```

---

## Examples

See `examples/fractal_demo.py` for comprehensive examples including:
- Automatic fractal mode
- Manual pipeline building
- Template usage
- Hybrid approach
- Runtime enhancement

---

## Troubleshooting

### Issue: Agent always/never grows

**Check trigger setting:**
```python
print(agent.fractal_config.growth_trigger)
# Should match your intent
```

**Check thresholds:**
```python
complexity = agent._estimate_task_complexity(task)
print(f"Task complexity: {complexity}")
print(f"Threshold: {agent.fractal_config.complexity_threshold}")
```

### Issue: Too many nodes created

**Reduce limits:**
```python
config.max_depth = 2
config.max_children = 3
config.max_total_nodes = 10
```

### Issue: Poor performance

**Enable auto-pruning:**
```python
config.enable_auto_pruning = True
config.pruning_threshold = 0.4  # Prune nodes with fitness < 0.4
```

**Check metrics:**
```python
print(agent.metrics.to_dict())
# Look for low success_rate or high avg_tokens
```

---

## API Reference

### Core Classes

- `FractalAgentNode`: Base fractal node with auto-decomposition
- `FractalSystem2Node`: System 2 integration
- `PipelineBuilder`: Fluent API for manual pipelines
- `PipelineTemplate`: Pre-built templates

### Factory Functions

- `create_fractal_agent()`: Create fractal agent
- `build_pipeline()`: Start pipeline builder
- `add_fractal_to_agent()`: Runtime enhancement

### Configuration

- `FractalConfig`: Fractal behavior configuration
- `NodeRole`: Node role enum
- `GrowthTrigger`: When to trigger growth
- `GrowthStrategy`: How to decompose

---

## Next Steps

- Read the full documentation at `docs/concepts/node_architecture.md`
- Run examples: `python examples/fractal_demo.py`
- Run tests: `pytest tests/test_fractal_nodes.py`
- Explore Phase 2: Structure Controllers (coming soon)

---

## Support

For issues or questions:
- GitHub Issues: [loom-agent/issues](https://github.com/your-org/loom-agent/issues)
- Documentation: `docs/`
- Examples: `examples/`
