"""
Configuration for Metacognition Layer.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Pattern
import re

@dataclass
class RouterRule:
    """A rule for classifying queries."""
    name: str
    keywords: List[str] = field(default_factory=list)
    regex_patterns: List[str] = field(default_factory=list)
    target_system: str = "SYSTEM_2"  # "SYSTEM_1" or "SYSTEM_2"
    
    # Pre-compiled patterns (internal)
    _compiled_patterns: List[Pattern] = field(init=False, default_factory=list)
    
    def __post_init__(self):
        self._compiled_patterns = [re.compile(p, re.IGNORECASE) for p in self.regex_patterns]

@dataclass
class RouterConfig:
    """
    Configuration for the Cognitive Router.
    """
    # Default system if no rules match
    default_system: str = "SYSTEM_2" 
    
    # Confidence thresholds
    s1_confidence_threshold: float = 0.8
    
    # Classification rules
    rules: List[RouterRule] = field(default_factory=list)
    
    # Heuristics
    enable_heuristics: bool = True
    max_s1_length: int = 100  # Queries longer than this unlikely to be S1 (unless rule matches)
    
    def add_rule(self, rule: RouterRule):
        self.rules.append(rule)

    @staticmethod
    def default() -> "RouterConfig":
        """Create a default configuration with standard rules."""
        config = RouterConfig()
        
        # System 1 Rules (Simple/Factual)
        config.add_rule(RouterRule(
            name="greeting",
            keywords=["hi", "hello", "hey", "greeting"],
            target_system="SYSTEM_1"
        ))
        
        config.add_rule(RouterRule(
            name="factual_questions",
            regex_patterns=[r"^what is", r"^who is", r"^when did"],
            target_system="SYSTEM_1"
        ))
        
        config.add_rule(RouterRule(
            name="simple_math",
            regex_patterns=[r"\d+\s*[\+\-\*\/]\s*\d+"],
            target_system="SYSTEM_1"
        ))
        
        # System 2 Rules (Complex/Reasoning)
        config.add_rule(RouterRule(
            name="complex_reasoning",
            keywords=["plan", "strategy", "design", "analyze", "compare", "code", "implement"],
            target_system="SYSTEM_2"
        ))
        
        return config
