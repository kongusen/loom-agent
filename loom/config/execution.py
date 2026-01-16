"""
Execution Configuration
"""

from pydantic import BaseModel, Field


class NormalizationConfig(BaseModel):
    """Configuration for data normalization."""

    max_depth: int = Field(3, description="Maximum recursion depth for object normalization")
    max_bytes: int = Field(100_000, description="Maximum byte size for tool outputs")
    truncate_strings: int = Field(20_000, description="Maximum string length before truncation")
    enable_circular_check: bool = Field(True, description="Detect and handle circular references")


class ErrorHandlingConfig(BaseModel):
    """Configuration for error formatting."""

    enable_hints: bool = Field(True, description="Provide actionable suggestions for errors")
    include_traceback: bool = Field(False, description="Include full stack trace in output")
    rich_formatting: bool = Field(True, description="Use Markdown formatting for errors")


class ExecutionConfig(BaseModel):
    """
    Configuration for Agent Execution Environment.
    Controls how tools are executed and results are processed.
    """

    timeout: int = Field(60, description="Tool execution timeout in seconds")
    max_retries: int = Field(0, description="Automatic retries for system errors")
    parallel_execution: bool = Field(
        False, description="Enable parallel execution for read-only tools"
    )
    concurrency_limit: int = Field(5, description="Maximum concurrent tool executions")

    # Sub-configs
    normalization: NormalizationConfig = Field(default_factory=NormalizationConfig)
    error_handling: ErrorHandlingConfig = Field(default_factory=ErrorHandlingConfig)

    @staticmethod
    def default() -> "ExecutionConfig":
        return ExecutionConfig()
