"""
Kernel Optimization - Layer 4: Structure Optimization

Provides dynamic structure optimization and health monitoring:
- Structure Controller: Manages structure optimization lifecycle
- Structure Evolution: Evolves structure through genetic algorithms
- Structure Health: Monitors structure health and performance
- Landscape Optimizer: Optimizes resource allocation
- Pruning Strategies: Simplifies structure through intelligent pruning
"""

from .landscape_optimizer import (
    FitnessLandscapeOptimizer,
    StructurePattern,
    StructureSnapshot,
)
from .pruning_strategies import (
    CompositePruningStrategy,
    FitnessPruningStrategy,
    PruningCriterion,
    PruningDecision,
    PruningStrategy,
    RedundancyPruningStrategy,
    ResourcePruningStrategy,
    SmartPruner,
)
from .structure_controller import (
    StructureController,
    StructureEvent,
    StructureEventType,
    StructureStats,
)
from .structure_evolution import (
    EvolutionConfig,
    GeneticOperators,
    GenomeConverter,
    MutationType,
    StructureEvolver,
    StructureGenome,
)
from .structure_health import (
    HealthDiagnostic,
    HealthIssue,
    HealthReport,
    HealthStatus,
    StructureHealthAssessor,
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
