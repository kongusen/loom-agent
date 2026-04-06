# Self-Improvement

Loom agents can improve themselves over time through four evolution strategies.

## How It Works

After each session, the `EvolutionEngine` applies registered strategies to the agent's feedback history:

```python
from loom.evolution import (
    EvolutionEngine,
    ToolLearningStrategy,
    PolicyOptimizationStrategy,
    ConstraintHardeningStrategy,
    AmoebaSplitStrategy,
)

engine = EvolutionEngine()
engine.register_strategy(ToolLearningStrategy())
engine.register_strategy(PolicyOptimizationStrategy())
engine.register_strategy(ConstraintHardeningStrategy())
engine.register_strategy(AmoebaSplitStrategy())

engine.evolve(agent)
```

See [Strategies](strategies.md) for details on each.

**Code:** `loom/evolution/`
