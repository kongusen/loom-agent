"""
Interceptor Configuration

Provides configuration for Layer 2 control capabilities.
"""

from pydantic import BaseModel, Field


class InterceptorConfig(BaseModel):
    """
    Configuration for Interceptors (Layer 2 - Control Capabilities)

    Interceptors provide AOP-style cross-cutting concerns:
    - Budget control (cost management)
    - Depth limiting (recursion protection)
    - Timeout control (execution time limits)
    - HITL (human-in-the-loop approval)
    - Tracing (distributed tracing)
    - Auth (authorization)
    """

    # Budget Control
    enable_budget: bool = Field(default=False, description="Enable token budget control")
    max_tokens: int | None = Field(default=None, description="Maximum tokens allowed")

    # Depth Limiting
    enable_depth_limit: bool = Field(default=False, description="Enable recursion depth limiting")
    max_depth: int | None = Field(default=5, description="Maximum recursion depth")

    # Timeout Control
    enable_timeout: bool = Field(default=False, description="Enable timeout control")
    timeout_seconds: float | None = Field(default=30.0, description="Timeout in seconds")

    # Human-in-the-Loop
    enable_hitl: bool = Field(
        default=False, description="Enable human approval for sensitive operations"
    )
    hitl_patterns: list[str] = Field(
        default_factory=list, description="Patterns requiring approval"
    )

    # Tracing
    enable_tracing: bool = Field(default=False, description="Enable distributed tracing")

    # Auth
    enable_auth: bool = Field(default=False, description="Enable authorization")
    allowed_sources: list[str] = Field(default_factory=list, description="Allowed event sources")

    class Config:
        """Pydantic config"""

        arbitrary_types_allowed = True

    @classmethod
    def default(cls) -> "InterceptorConfig":
        """Create default configuration (all disabled)"""
        return cls()

    @classmethod
    def safe_mode(cls) -> "InterceptorConfig":
        """Create safe mode configuration (basic protections enabled)"""
        return cls(
            enable_budget=True,
            max_tokens=100000,
            enable_depth_limit=True,
            max_depth=5,
            enable_timeout=True,
            timeout_seconds=60.0,
        )

    @classmethod
    def production_mode(cls) -> "InterceptorConfig":
        """Create production mode configuration (all protections enabled)"""
        return cls(
            enable_budget=True,
            max_tokens=50000,
            enable_depth_limit=True,
            max_depth=3,
            enable_timeout=True,
            timeout_seconds=30.0,
            enable_tracing=True,
            enable_auth=True,
        )
