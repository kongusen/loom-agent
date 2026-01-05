"""
Unit Tests for Phase 1 Infrastructure Components

Tests for:
- QueryFeatureExtractor (loom/cognition/features.py)
- TokenCounter (loom/memory/tokenizer.py)
- CognitiveSystemConfig (loom/config/cognitive.py)
"""

import pytest
from loom.cognition.features import (
    QueryFeatureExtractor,
    QueryFeatures,
    ResponseFeatures,
)
from loom.memory.tokenizer import TokenCounter, get_token_counter
from loom.config.cognitive import CognitiveSystemConfig


class TestQueryFeatureExtractor:
    """Tests for QueryFeatureExtractor"""

    @pytest.fixture
    def extractor(self):
        """Create a QueryFeatureExtractor instance"""
        return QueryFeatureExtractor()

    def test_extract_query_features_short_query(self, extractor):
        """Test feature extraction for short queries"""
        query = "Hi"
        features = extractor.extract_query_features(query)

        assert isinstance(features, QueryFeatures)
        assert features.length == -0.3  # Short query
        assert "short_query" in features.detected_features

    def test_extract_query_features_long_query(self, extractor):
        """Test feature extraction for long queries"""
        query = " ".join(["word"] * 30)
        features = extractor.extract_query_features(query)

        assert features.length == 0.4  # Long query
        assert "long_query" in features.detected_features

    def test_extract_query_features_code_detection(self, extractor):
        """Test code detection in queries"""
        query = "def hello(): pass"
        features = extractor.extract_query_features(query)

        assert features.code_detected is True
        assert "code_detected" in features.detected_features

    def test_extract_query_features_multi_step(self, extractor):
        """Test multi-step task detection"""
        query = "First do this and then do that"
        features = extractor.extract_query_features(query)

        assert features.multi_step is True
        assert "multi_step" in features.detected_features

    def test_extract_query_features_math_detection(self, extractor):
        """Test math detection in queries"""
        query = "What is 5+3?"
        features = extractor.extract_query_features(query)

        assert features.math_detected is True
        assert "math_detected" in features.detected_features

    def test_extract_query_features_uncertainty(self, extractor):
        """Test uncertainty marker detection"""
        query = "Maybe I should do this, perhaps?"
        features = extractor.extract_query_features(query)

        assert features.uncertainty_markers > 0
        assert features.clarity < 1.0

    def test_extract_response_features_short_response(self, extractor):
        """Test feature extraction for short responses"""
        query = "What is 2+2?"
        response = "4"
        features = extractor.extract_response_features(query, response)

        assert isinstance(features, ResponseFeatures)
        assert features.length > 0  # Short = positive

    def test_extract_response_features_long_response(self, extractor):
        """Test feature extraction for long responses"""
        query = "What is Python?"
        response = " ".join(["word"] * 60)
        features = extractor.extract_response_features(query, response)

        assert features.length < 0  # Long = negative

    def test_extract_response_features_uncertainty_markers(self, extractor):
        """Test uncertainty marker detection in responses"""
        query = "Is this correct?"
        response = "Maybe, perhaps, I think it might be."
        features = extractor.extract_response_features(query, response)

        assert features.uncertainty_markers > 0
        assert features.uncertainty_score < 0

    def test_extract_response_features_direct_answer(self, extractor):
        """Test directness detection"""
        query = "Is this true?"
        response = "Yes, absolutely."
        features = extractor.extract_response_features(query, response)

        assert features.directness > 0

    def test_extract_response_features_clarification_request(self, extractor):
        """Test clarification request detection"""
        query = "What should I do?"
        response = "Could you clarify what you mean by that?"
        features = extractor.extract_response_features(query, response)

        assert features.clarification_requested is True

    def test_extract_response_features_good_alignment(self, extractor):
        """Test query-response alignment"""
        query = "What is the capital of France"
        response = "The capital of France is Paris"
        features = extractor.extract_response_features(query, response)

        assert features.alignment_with_query > 0

    def test_query_and_response_feature_combination(self, extractor):
        """Test comprehensive feature extraction for query and response"""
        query = "Implement a function to sort an array"
        query_features = extractor.extract_query_features(query)

        response = "Here is the implementation with explanation"
        response_features = extractor.extract_response_features(query, response)

        # Query should detect as multi-step or complex
        assert len(query_features.detected_features) > 0

        # Response should be analyzed
        assert isinstance(response_features.alignment_with_query, float)


class TestTokenCounter:
    """Tests for TokenCounter singleton"""

    def test_singleton_pattern(self):
        """Test that TokenCounter follows singleton pattern"""
        counter1 = TokenCounter()
        counter2 = TokenCounter()

        assert counter1 is counter2

    def test_count_string(self):
        """Test string token counting"""
        counter = TokenCounter()
        text = "This is a test string with multiple words."

        count = counter.count_string(text)

        assert isinstance(count, int)
        assert count > 0

    def test_count_string_empty(self):
        """Test token counting for empty string"""
        counter = TokenCounter()

        count = counter.count_string("")

        assert count == 0

    def test_count_message(self):
        """Test message token counting"""
        counter = TokenCounter()
        message = {"role": "user", "content": "Hello, how are you?"}

        count = counter.count_message(message)

        assert isinstance(count, int)
        assert count > 0

    def test_count_message_includes_role_overhead(self):
        """Test that message counting includes role overhead"""
        counter = TokenCounter()
        content_only = "Hello world"
        message = {"role": "user", "content": content_only}

        content_count = counter.count_string(content_only)
        message_count = counter.count_message(message)

        # Message count should be higher due to role overhead
        assert message_count > content_count

    def test_count_messages_list(self):
        """Test counting multiple messages"""
        counter = TokenCounter()
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": "How are you?"},
        ]

        total_count = counter.count_messages(messages)

        assert isinstance(total_count, int)
        assert total_count > 0

    def test_cache_info(self):
        """Test cache information retrieval"""
        counter = TokenCounter()

        # Clear cache
        counter.clear_cache()

        # Get initial cache info
        info_before = counter.get_cache_info()
        assert info_before["hits"] == 0
        assert info_before["misses"] == 0

        # Count some text
        counter.count_string("test")
        info_after = counter.get_cache_info()

        assert info_after["misses"] > 0

    def test_cache_hit(self):
        """Test that cache hits work correctly"""
        counter = TokenCounter()
        counter.clear_cache()

        text = "Same text"

        # First call - miss
        counter.count_string(text)
        info_1 = counter.get_cache_info()

        # Second call - hit
        counter.count_string(text)
        info_2 = counter.get_cache_info()

        assert info_2["hits"] > info_1["hits"]

    def test_get_token_counter_singleton(self):
        """Test get_token_counter convenience function"""
        counter1 = get_token_counter()
        counter2 = get_token_counter()

        assert counter1 is counter2


class TestCognitiveSystemConfig:
    """Tests for CognitiveSystemConfig"""

    def test_default_config(self):
        """Test creating default configuration"""
        config = CognitiveSystemConfig.default()

        assert isinstance(config, CognitiveSystemConfig)
        assert len(config.router_rules) > 0

    def test_get_router_config(self):
        """Test building router config"""
        config = CognitiveSystemConfig.default()
        router_config = config.get_router_config()

        assert router_config.default_system == config.router_default_system
        assert router_config.s1_confidence_threshold == config.router_s1_confidence_threshold
        assert len(router_config.rules) > 0

    def test_get_curation_config(self):
        """Test building curation config"""
        config = CognitiveSystemConfig.default()
        curation_config = config.get_curation_config()

        assert curation_config.max_tokens == config.curation_max_tokens
        assert curation_config.use_snippets == config.curation_use_snippets

    def test_get_context_config(self):
        """Test building context config"""
        config = CognitiveSystemConfig.default()
        context_config = config.get_context_config()

        assert context_config.model_name == config.context_model_name
        assert context_config.tokenizer_encoding == config.context_tokenizer_encoding

    def test_for_performance_config(self):
        """Test performance-optimized configuration"""
        config = CognitiveSystemConfig.for_performance()

        # Should have smaller token budgets
        assert config.curation_max_tokens < CognitiveSystemConfig.default().curation_max_tokens
        # Should disable expensive features
        assert config.context_enable_prompt_caching is False

    def test_for_accuracy_config(self):
        """Test accuracy-optimized configuration"""
        config = CognitiveSystemConfig.for_accuracy()

        # Should have larger token budgets
        assert config.curation_max_tokens > CognitiveSystemConfig.default().curation_max_tokens
        # Should enable optimizations
        assert config.context_enable_prompt_caching is True

    def test_for_testing_config(self):
        """Test testing configuration"""
        config = CognitiveSystemConfig.for_testing()

        # Should have minimal settings
        assert config.curation_max_tokens < 1000
        assert config.context_max_tokens < 2000
        # Should use mock providers
        assert config.memory_embedding_provider == "mock"

    def test_validate_success(self):
        """Test configuration validation succeeds for valid config"""
        config = CognitiveSystemConfig.default()

        # Should not raise
        assert config.validate() is True

    def test_validate_budget_sum(self):
        """Test validation of token budget sum"""
        config = CognitiveSystemConfig()

        # Set invalid budget (doesn't sum to 1.0)
        config.context_tokens_budget_l1 = 0.5
        config.context_tokens_budget_l2 = 0.5
        config.context_tokens_budget_l3 = 0.5
        config.context_tokens_budget_l4 = 0.5

        with pytest.raises(ValueError, match="must sum to 1.0"):
            config.validate()

    def test_validate_confidence_threshold(self):
        """Test validation of confidence threshold"""
        config = CognitiveSystemConfig()

        # Set invalid threshold
        config.router_s1_confidence_threshold = 1.5

        with pytest.raises(ValueError, match="must be between 0.0 and 1.0"):
            config.validate()

    def test_validate_positive_tokens(self):
        """Test validation of positive token counts"""
        config = CognitiveSystemConfig()

        # Set invalid token count
        config.curation_max_tokens = -100

        with pytest.raises(ValueError, match="must be positive"):
            config.validate()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
