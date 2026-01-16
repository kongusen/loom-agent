"""
Loom Kernel Module - Core execution and control systems

Organized by 4-layer capability system:
- Layer 1: Core execution engine
- Layer 2: Control capabilities (Interceptors)
- Layer 3: Fractal decomposition
- Layer 4: Structure optimization
"""

# Layer 1: Core
# Layer 2: Control Capabilities
from loom.kernel.control import (
    AdaptiveLLMInterceptor,
    AuthInterceptor,
    BudgetInterceptor,
    DepthInterceptor,
    HITLInterceptor,
    Interceptor,
    TimeoutInterceptor,
    TracingInterceptor,
)
from loom.kernel.core import (
    CognitiveState,
    Dispatcher,
    ProjectionOperator,
    State,
    Thought,
    ThoughtState,
    ToolExecutor,
    UniversalEventBus,
)

# Layer 3: Fractal Decomposition
from loom.kernel.fractal import (
    FractalOrchestrator,
    OrchestratorConfig,
    ResultSynthesizer,
    StructureTemplate,
    SynthesisConfig,
    TemplateManager,
)

# Layer 4: Structure Optimization
from loom.kernel.optimization import (
    CompositePruningStrategy,
    EvolutionConfig,
    FitnessLandscapeOptimizer,
    FitnessPruningStrategy,
    GeneticOperators,
    GenomeConverter,
    HealthDiagnostic,
    HealthIssue,
    HealthReport,
    HealthStatus,
    PruningCriterion,
    PruningDecision,
    PruningStrategy,
    RedundancyPruningStrategy,
    ResourcePruningStrategy,
    SmartPruner,
    StructureController,
    StructureEvent,
    StructureEventType,
    StructureEvolver,
    StructureGenome,
    StructureHealthAssessor,
    StructurePattern,
    StructureSnapshot,
    StructureStats,
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
