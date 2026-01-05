"""
Loom Kernel Module - Core execution and control systems

Organized by 4-layer capability system:
- Layer 1: Core execution engine
- Layer 2: Control capabilities (Interceptors)
- Layer 3: Fractal decomposition
- Layer 4: Structure optimization
"""

# Layer 1: Core
from loom.kernel.core import (
    UniversalEventBus,
    Dispatcher,
    ToolExecutor,
    State,
    CognitiveState,
    ProjectionOperator,
    Thought,
    ThoughtState,
)

# Layer 2: Control Capabilities
from loom.kernel.control import (
    Interceptor,
    TracingInterceptor,
    AuthInterceptor,
    BudgetInterceptor,
    DepthInterceptor,
    TimeoutInterceptor,
    HITLInterceptor,
    AdaptiveLLMInterceptor,
)

# Layer 3: Fractal Decomposition
from loom.kernel.fractal import (
    FractalOrchestrator,
    OrchestratorConfig,
    ResultSynthesizer,
    SynthesisConfig,
    TemplateManager,
    StructureTemplate,
)

# Layer 4: Structure Optimization
from loom.kernel.optimization import (
    StructureController,
    StructureEvent,
    StructureEventType,
    StructureStats,
    PruningStrategy,
    PruningDecision,
    PruningCriterion,
    FitnessPruningStrategy,
    RedundancyPruningStrategy,
    ResourcePruningStrategy,
    CompositePruningStrategy,
    SmartPruner,
    StructureHealthAssessor,
    HealthReport,
    HealthStatus,
    HealthIssue,
    HealthDiagnostic,
    FitnessLandscapeOptimizer,
    StructureSnapshot,
    StructurePattern,
    StructureEvolver,
    StructureGenome,
    GenomeConverter,
    EvolutionConfig,
    GeneticOperators,
)

__all__ = [
    # Layer 1: Core
    "UniversalEventBus",
    "Dispatcher",
    "ToolExecutor",
    "State",
    "CognitiveState",
    "ProjectionOperator",
    "Thought",
    "ThoughtState",

    # Layer 2: Control
    "Interceptor",
    "TracingInterceptor",
    "AuthInterceptor",
    "BudgetInterceptor",
    "DepthInterceptor",
    "TimeoutInterceptor",
    "HITLInterceptor",
    "AdaptiveLLMInterceptor",

    # Layer 3: Fractal Decomposition
    "FractalOrchestrator",
    "OrchestratorConfig",
    "ResultSynthesizer",
    "SynthesisConfig",
    "TemplateManager",
    "StructureTemplate",

    # Layer 4: Structure Optimization
    # Structure Controller
    "StructureController",
    "StructureEvent",
    "StructureEventType",
    "StructureStats",

    # Pruning
    "PruningStrategy",
    "PruningDecision",
    "PruningCriterion",
    "FitnessPruningStrategy",
    "RedundancyPruningStrategy",
    "ResourcePruningStrategy",
    "CompositePruningStrategy",
    "SmartPruner",

    # Health
    "StructureHealthAssessor",
    "HealthReport",
    "HealthStatus",
    "HealthIssue",
    "HealthDiagnostic",

    # Landscape Optimization
    "FitnessLandscapeOptimizer",
    "StructureSnapshot",
    "StructurePattern",

    # Evolution
    "StructureEvolver",
    "StructureGenome",
    "GenomeConverter",
    "EvolutionConfig",
    "GeneticOperators",
]
