"""Configuration management"""

from dataclasses import dataclass


@dataclass
class LoomConfig:
    """Global Loom configuration"""
    max_tokens: int = 200000
    max_depth: int = 5
    rho_threshold: float = 1.0
    heartbeat_interval: float = 5.0
    delta_min: float = 0.1
