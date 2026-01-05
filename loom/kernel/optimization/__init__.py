"""
Kernel Optimization - Layer 4: Structure Optimization

Provides dynamic structure optimization and health monitoring:
- Structure Controller: Manages structure optimization lifecycle
- Structure Evolution: Evolves structure through genetic algorithms
- Structure Health: Monitors structure health and performance
- Landscape Optimizer: Optimizes resource allocation
- Pruning Strategies: Simplifies structure through intelligent pruning
"""

from .structure_controller import (
    StructureController,
    StructureEvent,
    StructureEventType,
    StructureStats,
)
from .structure_evolution import (
    StructureEvolver,
    StructureGenome,
    GenomeConverter,
    EvolutionConfig,
    GeneticOperators,
    MutationType,
)
from .structure_health import (
    StructureHealthAssessor,
    HealthReport,
    HealthStatus,
    HealthIssue,
    HealthDiagnostic,
)
from .landscape_optimizer import (
    FitnessLandscapeOptimizer,
    StructureSnapshot,
    StructurePattern,
)
from .pruning_strategies import (
    PruningStrategy,
    PruningDecision,
    PruningCriterion,
    FitnessPruningStrategy,
    RedundancyPruningStrategy,
    ResourcePruningStrategy,
    CompositePruningStrategy,
    SmartPruner,
)

__all__ = [
    # Structure Controller
    "StructureController",
    "StructureEvent",
    "StructureEventType",
    "StructureStats",

    # Structure Evolution
    "StructureEvolver",
    "StructureGenome",
    "GenomeConverter",
    "EvolutionConfig",
    "GeneticOperators",
    "MutationType",

    # Structure Health
    "StructureHealthAssessor",
    "HealthReport",
    "HealthStatus",
    "HealthIssue",
    "HealthDiagnostic",

    # Landscape Optimizer
    "FitnessLandscapeOptimizer",
    "StructureSnapshot",
    "StructurePattern",

    # Pruning
    "PruningStrategy",
    "PruningDecision",
    "PruningCriterion",
    "FitnessPruningStrategy",
    "RedundancyPruningStrategy",
    "ResourcePruningStrategy",
    "CompositePruningStrategy",
    "SmartPruner",
]
