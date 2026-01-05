"""
Unified Query Feature Extraction

Consolidates feature extraction logic from router.py and confidence.py
to eliminate duplication and provide a single source of truth for
query and response feature analysis.
"""

from typing import Dict, Optional, List, Set
from dataclasses import dataclass, field
from functools import lru_cache
import re


@dataclass
class QueryFeatures:
    """Container for extracted query features"""
    length: float = 0.0
    code_detected: bool = False
    multi_step: bool = False
    math_detected: bool = False
    uncertainty_markers: int = 0
    clarity: float = 0.0  # 0-1, higher = more clear
    reasoning: str = ""
    detected_features: List[str] = field(default_factory=list)


@dataclass
class ResponseFeatures:
    """Container for extracted response features"""
    length: float = 0.0  # -0.3 to 0.1 range
    uncertainty_markers: int = 0
    uncertainty_score: float = 0.0  # -0.3 to 0.0
    directness: float = 0.0  # 0.0 to 0.15
    clarification_requested: bool = False
    alignment_with_query: float = 0.0  # -0.1 to 0.1
    detected_features: List[str] = field(default_factory=list)


class QueryFeatureExtractor:
    """
    Unified feature extraction for queries and responses.

    Replaces:
    - router.py::QueryClassifier._heuristic_classify (feature extraction)
    - confidence.py::ConfidenceEstimator.extract_features (all methods)

    Benefits:
    - Single source of truth for feature definitions
    - Caching for repeated feature calculations
    - Consistent feature semantics across cognition layer
    - Easier to maintain and extend
    """

    # Uncertainty markers used in both router and confidence
    UNCERTAINTY_WORDS = {
        "maybe", "perhaps", "possibly", "might", "could be",
        "unclear", "uncertain", "not sure", "depends", "it depends",
        "hard to say", "difficult to", "i think", "i believe",
        "probably", "likely", "seems like"
    }

    # Confidence boosters for response directness
    CONFIDENCE_STARTERS = {
        "yes", "no", "the answer is", "definitely", "certainly",
        "absolutely", "exactly", "precisely"
    }

    # Stop words for alignment calculation
    STOP_WORDS = {
        "the", "a", "an", "is", "are", "was", "were", "in", "on", "at",
        "and", "or", "but", "if", "then", "for", "to", "with"
    }

    # Clarification request patterns
    CLARIFICATION_PATTERNS = [
        r"could you clarify",
        r"can you provide more",
        r"need more information",
        r"what do you mean by",
        r"please specify",
        r"which .+ are you referring to"
    ]

    def __init__(self):
        """Initialize feature extractor with cached methods."""
        self._compile_patterns()

    def _compile_patterns(self):
        """Pre-compile regex patterns for efficiency."""
        self.compiled_clarification_patterns = [
            re.compile(p, re.IGNORECASE)
            for p in self.CLARIFICATION_PATTERNS
        ]

    def extract_query_features(
        self,
        query: str,
        context: Optional[Dict] = None
    ) -> QueryFeatures:
        """
        Extract features from a query.

        Combines features from:
        - router.py::_heuristic_classify (length, code, multi-step, math)
        - confidence.py logic adapted for queries

        Args:
            query: The query to analyze
            context: Optional context information

        Returns:
            QueryFeatures with extracted feature values
        """
        features = QueryFeatures()
        detected = []

        # Feature 1: Length (from router.py line 120)
        word_count = len(query.split())
        features.length = self._extract_length_score(word_count)
        if word_count < 8:
            detected.append("short_query")
        elif word_count > 25:
            detected.append("long_query")

        # Feature 2: Code/Technical indicators (from router.py line 131)
        if self._detect_code(query):
            features.code_detected = True
            detected.append("code_detected")

        # Feature 3: Multi-step indicators (from router.py line 136)
        if self._detect_multi_step(query):
            features.multi_step = True
            detected.append("multi_step")

        # Feature 4: Math indicators (from router.py line 141)
        if re.search(r'\d+[\+\-\*/^]\d+', query):
            features.math_detected = True
            detected.append("math_detected")

        # Feature 5: Uncertainty markers (adapted from confidence.py)
        uncertainty_count = self._count_uncertainty_markers(query)
        features.uncertainty_markers = uncertainty_count
        if uncertainty_count > 0:
            detected.append(f"uncertainty_markers_{uncertainty_count}")

        # Calculate clarity (inverse of uncertainty)
        features.clarity = 1.0 - (uncertainty_count * 0.1)
        features.clarity = max(0.0, min(1.0, features.clarity))

        features.detected_features = detected
        features.reasoning = self._generate_query_reasoning(features)

        return features

    def extract_response_features(
        self,
        query: str,
        response: str
    ) -> ResponseFeatures:
        """
        Extract features from a response.

        Replaces confidence.py::ConfidenceEstimator all feature extraction

        Args:
            query: Original user query
            response: System response

        Returns:
            ResponseFeatures with extracted feature values
        """
        features = ResponseFeatures()
        detected = []

        # Feature 1: Length (from confidence.py line 121)
        response_words = len(response.split())
        features.length = self._analyze_response_length(response_words)
        if features.length < 0:
            detected.append("response_too_long")
        elif features.length > 0:
            detected.append("concise_response")

        # Feature 2: Uncertainty Markers (from confidence.py line 135)
        uncertainty_count = self._count_uncertainty_markers(response)
        features.uncertainty_markers = uncertainty_count
        features.uncertainty_score = self._calculate_uncertainty_score(uncertainty_count)
        if features.uncertainty_score < 0:
            detected.append("uncertainty_markers_detected")

        # Feature 3: Directness (from confidence.py line 150)
        features.directness = self._analyze_directness(response)
        if features.directness > 0:
            detected.append("direct_answer")

        # Feature 4: Clarification Requests (from confidence.py line 163)
        features.clarification_requested = self._detect_clarification_request(response)
        if features.clarification_requested:
            detected.append("requests_clarification")

        # Feature 5: Query-Response Alignment (from confidence.py line 173)
        features.alignment_with_query = self._analyze_alignment(query, response)
        if features.alignment_with_query > 0:
            detected.append("good_query_alignment")
        elif features.alignment_with_query < 0:
            detected.append("poor_query_alignment")

        features.detected_features = detected

        return features

    # ============================================================================
    # Helper Methods for Query Features
    # ============================================================================

    @staticmethod
    @lru_cache(maxsize=1024)
    def _extract_length_score(word_count: int) -> float:
        """Extract length feature as normalized score."""
        if word_count < 8:
            return -0.3  # Favors S1
        elif word_count > 25:
            return 0.4   # Favors S2
        else:
            return 0.0

    @staticmethod
    def _detect_code(query: str) -> bool:
        """Detect code/technical indicators."""
        return "```" in query or any(
            x in query for x in ["def ", "class ", "import ", "{", "}"]
        )

    @staticmethod
    def _detect_multi_step(query: str) -> bool:
        """Detect multi-step task indicators."""
        return any(
            x in query.lower()
            for x in [" and ", " then ", " after ", " step "]
        )

    def _count_uncertainty_markers(self, text: str) -> int:
        """Count uncertainty markers in text."""
        text_lower = text.lower()
        return sum(1 for word in self.UNCERTAINTY_WORDS if word in text_lower)

    @staticmethod
    def _generate_query_reasoning(features: QueryFeatures) -> str:
        """Generate human-readable reasoning for query features."""
        reasons = []

        if features.code_detected:
            reasons.append("code_detected")
        if features.multi_step:
            reasons.append("multi_step_task")
        if features.math_detected:
            reasons.append("math_detected")
        if features.uncertainty_markers > 0:
            reasons.append(f"uncertainty_{features.uncertainty_markers}")

        if not reasons:
            return "No special features detected"

        return f"Features: {', '.join(reasons)}"

    # ============================================================================
    # Helper Methods for Response Features
    # ============================================================================

    @staticmethod
    @lru_cache(maxsize=256)
    def _analyze_response_length(word_count: int) -> float:
        """Analyze response length impact on confidence."""
        length_penalty_threshold = 50

        if word_count < 20:
            return 0.1  # Short and direct = confident
        elif word_count < length_penalty_threshold:
            return 0.0  # Normal length
        else:
            # Penalty for excessive length
            excess = word_count - length_penalty_threshold
            penalty = min(0.3, excess * 0.01)
            return -penalty

    @staticmethod
    @lru_cache(maxsize=256)
    def _calculate_uncertainty_score(uncertainty_count: int) -> float:
        """Convert uncertainty marker count to score."""
        uncertainty_penalty = 0.3

        if uncertainty_count == 0:
            return 0.0
        elif uncertainty_count == 1:
            return -0.1
        else:
            return -uncertainty_penalty

    def _analyze_directness(self, response: str) -> float:
        """Check if response starts with confident language."""
        response_lower = response.lower().strip()

        # Check first few words
        first_words = " ".join(response_lower.split()[:3])

        for starter in self.CONFIDENCE_STARTERS:
            if first_words.startswith(starter):
                return 0.15  # Boost for direct answers

        return 0.0

    def _detect_clarification_request(self, response: str) -> bool:
        """Check if response requests clarification."""
        response_lower = response.lower()

        for pattern in self.compiled_clarification_patterns:
            if pattern.search(response_lower):
                return True

        return False

    def _analyze_alignment(self, query: str, response: str) -> float:
        """Check query-response alignment."""
        query_words: Set[str] = set(query.lower().split())
        response_words: Set[str] = set(response.lower().split())

        # Remove common stop words
        query_words -= self.STOP_WORDS
        response_words -= self.STOP_WORDS

        if not query_words:
            return 0.0

        # Calculate overlap
        overlap = len(query_words & response_words)
        coverage = overlap / len(query_words)

        # Good coverage = confident
        if coverage > 0.5:
            return 0.1
        elif coverage < 0.2:
            return -0.1

        return 0.0
