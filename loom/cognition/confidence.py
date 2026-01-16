"""
Confidence Estimation for System 1 Responses
Determines if a System 1 response is reliable or needs fallback to System 2.

Now uses unified QueryFeatureExtractor for consistent feature extraction.
"""
from dataclasses import dataclass
from typing import Any

from loom.cognition.features import QueryFeatureExtractor


@dataclass
class ConfidenceScore:
    """Result of confidence estimation"""
    score: float  # 0.0 to 1.0
    reasoning: str
    features: dict[str, float]  # Individual feature scores


class ConfidenceEstimator:
    """
    Estimates confidence in System 1 responses.

    Now uses unified QueryFeatureExtractor for consistent feature extraction.
    Previously had duplicate feature extraction logic that is now consolidated.

    Uses multiple heuristics to determine if the response is reliable:
    - Response length (too long = uncertain)
    - Uncertainty markers (maybe, perhaps, etc.)
    - Directness (starts with Yes/No = confident)
    - Requests for clarification
    - Hedging language
    """

    def __init__(
        self,
        base_confidence: float = 0.7,
        length_penalty_threshold: int = 50,
        uncertainty_penalty: float = 0.3
    ):
        self.base_confidence = base_confidence
        self.length_penalty_threshold = length_penalty_threshold
        self.uncertainty_penalty = uncertainty_penalty
        self.feature_extractor = QueryFeatureExtractor()

    def estimate(
        self,
        query: str,
        response: str,
        context: dict[str, Any] | None = None
    ) -> ConfidenceScore:
        """
        Estimate confidence in a System 1 response.

        Args:
            query: Original user query
            response: System 1 response
            context: Optional context information

        Returns:
            ConfidenceScore with score and reasoning
        """
        # Extract features using unified extractor
        response_features = self.feature_extractor.extract_response_features(query, response)

        # Map extracted features to confidence adjustments
        features = {}
        confidence = self.base_confidence

        # Feature 1: Response Length
        features["length"] = response_features.length
        confidence += response_features.length

        # Feature 2: Uncertainty Markers
        features["uncertainty"] = response_features.uncertainty_score
        confidence += response_features.uncertainty_score

        # Feature 3: Directness
        features["directness"] = response_features.directness
        confidence += response_features.directness

        # Feature 4: Clarification Requests
        features["clarification"] = -0.3 if response_features.clarification_requested else 0.0
        confidence += features["clarification"]

        # Feature 5: Query-Response Alignment
        features["alignment"] = response_features.alignment_with_query
        confidence += response_features.alignment_with_query

        # Clamp to [0, 1]
        confidence = max(0.0, min(1.0, confidence))

        # Generate reasoning
        reasoning = self._generate_reasoning(features, confidence)

        return ConfidenceScore(
            score=confidence,
            reasoning=reasoning,
            features=features
        )

    @staticmethod
    def _generate_reasoning(features: dict[str, float], confidence: float) -> str:
        """Generate human-readable reasoning."""
        reasons = []

        if features["length"] < 0:
            reasons.append("response too long")
        elif features["length"] > 0:
            reasons.append("concise response")

        if features["uncertainty"] < 0:
            reasons.append("uncertainty markers detected")

        if features["directness"] > 0:
            reasons.append("direct answer")

        if features["clarification"] < 0:
            reasons.append("requests clarification")

        if features["alignment"] > 0:
            reasons.append("good query alignment")
        elif features["alignment"] < 0:
            reasons.append("poor query alignment")

        if not reasons:
            return f"Confidence: {confidence:.2f} (neutral)"

        return f"Confidence: {confidence:.2f} ({', '.join(reasons)})"
