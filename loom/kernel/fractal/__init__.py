"""
Kernel Fractal - Layer 3: Fractal Decomposition

Provides task decomposition and result synthesis capabilities:
- Fractal Orchestrator: Manages delegation lifecycle
- Result Synthesizer: Synthesizes sub-task results
- Template Manager: Learns and manages structure templates
- Fractal Utils: Shared utility functions
"""

from .fractal_orchestrator import (
    FractalOrchestrator,
    OrchestratorConfig,
)
from .synthesizer import (
    ResultSynthesizer,
    SynthesisConfig,
)
from .template_manager import (
    TemplateManager,
    StructureTemplate,
)
from .fractal_utils import (
    estimate_task_complexity,
    should_use_fractal,
)

__all__ = [
    "FractalOrchestrator",
    "OrchestratorConfig",
    "ResultSynthesizer",
    "SynthesisConfig",
    "TemplateManager",
    "StructureTemplate",
    "estimate_task_complexity",
    "should_use_fractal",
]
