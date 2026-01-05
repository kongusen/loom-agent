"""
Structure Optimization Configuration

Provides configuration for Layer 4 optimization capabilities.
"""

from typing import Optional
from pydantic import BaseModel, Field


class OptimizationConfig(BaseModel):
    """
    Configuration for Structure Optimization (Layer 4 - Optimization Capabilities)

    Provides dynamic structure optimization:
    - Structure evolution (adaptive growth)
    - Health monitoring (performance tracking)
    - Landscape optimization (resource allocation)
    - Pruning strategies (structure simplification)
    """

    # Enable/Disable
    enabled: bool = Field(default=False, description="Enable structure optimization")

    # Evolution Strategy
    evolution_strategy: str = Field(
        default="adaptive",
        description="Evolution strategy: adaptive, aggressive, conservative"
    )

    # Health Monitoring
    enable_health_check: bool = Field(default=True, description="Enable health monitoring")
    health_check_interval: int = Field(default=10, description="Health check interval (iterations)")

    # Landscape Optimization
    enable_landscape_optimization: bool = Field(
        default=False,
        description="Enable landscape optimization"
    )

    # Pruning
    enable_pruning: bool = Field(default=False, description="Enable structure pruning")
    pruning_threshold: float = Field(default=0.3, description="Pruning threshold (0-1)")

    # Performance Thresholds
    min_success_rate: float = Field(default=0.7, description="Minimum success rate")
    max_avg_time: float = Field(default=10.0, description="Maximum average time (seconds)")

    class Config:
        """Pydantic config"""
        arbitrary_types_allowed = True

    @classmethod
    def default(cls) -> 'OptimizationConfig':
        """Create default configuration (disabled)"""
        return cls(enabled=False)

    @classmethod
    def basic(cls) -> 'OptimizationConfig':
        """Create basic optimization configuration"""
        return cls(
            enabled=True,
            evolution_strategy="adaptive",
            enable_health_check=True,
            health_check_interval=10
        )

    @classmethod
    def advanced(cls) -> 'OptimizationConfig':
        """Create advanced optimization configuration"""
        return cls(
            enabled=True,
            evolution_strategy="aggressive",
            enable_health_check=True,
            health_check_interval=5,
            enable_landscape_optimization=True,
            enable_pruning=True,
            pruning_threshold=0.3
        )
