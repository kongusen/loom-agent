"""
System Router - Metacognition Layer
Decides whether to use System 1 (Fast/Reflex) or System 2 (Slow/Reasoning).
"""
from enum import Enum
from typing import Optional, Dict, Any
from dataclasses import dataclass

from loom.config.router import RouterConfig, RouterRule
from loom.cognition.features import QueryFeatureExtractor

class SystemType(Enum):
    """Cognitive System Type"""
    SYSTEM_1 = "system_1"  # Fast, Intuitive, Reflexive
    SYSTEM_2 = "system_2"  # Slow, Analytical, Reflective
    ADAPTIVE = "adaptive"  # Try S1 first, fallback to S2


@dataclass
class RoutingDecision:
    """Result of a routing decision"""
    system: SystemType
    confidence: float  # 0.0 to 1.0
    reasoning: str
    fallback_allowed: bool = True


class QueryClassifier:
    """
    Classifies user queries to determine the optimal cognitive system using configurable rules.

    Now uses unified QueryFeatureExtractor for consistent feature extraction.
    """

    def __init__(self, config: Optional[RouterConfig] = None):
        self.config = config or RouterConfig.default()
        self.feature_extractor = QueryFeatureExtractor()
        self.stats = {
            "total": 0,
            "system_1": 0,
            "system_2": 0,
            "switches": 0
        }

    def classify(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> RoutingDecision:
        """Classify a query into System 1 or System 2."""
        self.stats["total"] += 1

        # 1. Rule-Based (Priority)
        rule_decision = self._rule_based_classify(query, context)
        if rule_decision:
             self._update_stats(rule_decision.system)
             return rule_decision

        # 2. Heuristic (if enabled) - now using QueryFeatureExtractor
        if self.config.enable_heuristics:
            heuristic_decision = self._heuristic_classify(query, context)
            if heuristic_decision:
                self._update_stats(heuristic_decision.system)
                return heuristic_decision

        # 3. Default / Adaptive
        adaptive_decision = RoutingDecision(
            system=SystemType.ADAPTIVE,
            confidence=0.5,
            reasoning="Uncertain route - defaulting to adaptive (S1 -> S2)",
            fallback_allowed=True
        )
        self._update_stats(SystemType.SYSTEM_1)
        return adaptive_decision

    def _rule_based_classify(
        self,
        query: str,
        context: Optional[Dict] = None
    ) -> Optional[RoutingDecision]:
        """Check against configured rules."""
        query_lower = query.lower()

        # Special Case: Context requirement overrides text rules
        if context and context.get("requires_tools"):
            return RoutingDecision(
                system=SystemType.SYSTEM_2,
                confidence=0.95,
                reasoning="Context indicates tool requirement"
            )

        for rule in self.config.rules:
            # Check keywords
            for kw in rule.keywords:
                if kw in query_lower:
                    return RoutingDecision(
                        system=SystemType(rule.target_system.lower()),
                        confidence=0.9,
                        reasoning=f"Rule '{rule.name}' matched keyword: '{kw}'"
                    )

            # Check Regex
            for pattern in rule._compiled_patterns:
                if pattern.search(query):
                    return RoutingDecision(
                        system=SystemType(rule.target_system.lower()),
                        confidence=0.95,
                        reasoning=f"Rule '{rule.name}' matched regex"
                    )

        return None

    def _heuristic_classify(
        self,
        query: str,
        context: Optional[Dict] = None
    ) -> Optional[RoutingDecision]:
        """
        Heuristic scoring based on query features.

        Now uses QueryFeatureExtractor for consistent feature extraction.
        """
        # Extract features using unified extractor
        features = self.feature_extractor.extract_query_features(query, context)

        score = 0.0
        detected = []

        # Feature 1: Length
        score += features.length
        if features.length < 0:
            detected.append("short_query")
        elif features.length > 0:
            detected.append("long_query")

        # Feature 2: Code / Technical indicators
        if features.code_detected:
            score += 0.5
            detected.append("code_detected")

        # Feature 3: Multi-step indicators
        if features.multi_step:
            score += 0.3
            detected.append("multi_step")

        # Feature 4: Math
        if features.math_detected:
            score += 0.2
            detected.append("math_detected")

        # Thresholding
        if score > 0.3:
            return RoutingDecision(
                system=SystemType.SYSTEM_2,
                confidence=min(0.7 + score * 0.1, 0.95),
                reasoning=f"Heuristics ({', '.join(detected)}) favored reasoning"
            )
        elif score < -0.2:
             # Check max length constraint for S1
             word_count = len(query.split())
             if word_count < self.config.max_s1_length:
                return RoutingDecision(
                    system=SystemType.SYSTEM_1,
                    confidence=min(0.7 + abs(score) * 0.1, 0.95),
                    reasoning=f"Heuristics ({', '.join(detected)}) favored reflex"
                )

        return None

    def _update_stats(self, system: SystemType):
        if system == SystemType.SYSTEM_1:
            self.stats["system_1"] += 1
        elif system == SystemType.SYSTEM_2:
            self.stats["system_2"] += 1

    def record_switch(self):
        """Record a fallback from S1 to S2."""
        self.stats["switches"] += 1


class AdaptiveRouter:
    """
    Manages the execution flow based on classification and fallback logic.
    """

    def __init__(
        self,
        classifier: QueryClassifier,
        config: Optional[RouterConfig] = None
    ):
        self.classifier = classifier
        self.config = config or classifier.config

    def route(self, query: str, context: Optional[Dict] = None) -> RoutingDecision:
        """Delegates to classifier."""
        return self.classifier.classify(query, context)

    def should_fallback(self, s1_confidence: float) -> bool:
        """
        Determine if we should fallback to System 2.
        """
        return s1_confidence < self.config.s1_confidence_threshold




