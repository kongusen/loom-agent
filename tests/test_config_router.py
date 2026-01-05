"""
Tests for Router Configuration
"""

import pytest
import re

from loom.config.router import RouterRule, RouterConfig


class TestRouterRule:
    """Test RouterRule class."""

    def test_create_rule_with_defaults(self):
        """Test creating a rule with default values."""
        rule = RouterRule(name="test_rule")

        assert rule.name == "test_rule"
        assert rule.keywords == []
        assert rule.regex_patterns == []
        assert rule.target_system == "SYSTEM_2"
        assert rule._compiled_patterns == []

    def test_create_rule_with_keywords(self):
        """Test creating a rule with keywords."""
        rule = RouterRule(
            name="test_rule",
            keywords=["test", "example", "sample"],
            target_system="SYSTEM_1"
        )

        assert rule.keywords == ["test", "example", "sample"]
        assert rule.target_system == "SYSTEM_1"

    def test_create_rule_with_regex_patterns(self):
        """Test creating a rule with regex patterns."""
        rule = RouterRule(
            name="test_rule",
            regex_patterns=[r"^test", r"example\d+"],
            target_system="SYSTEM_1"
        )

        assert rule.regex_patterns == [r"^test", r"example\d+"]
        assert len(rule._compiled_patterns) == 2
        # Check that patterns are compiled
        assert isinstance(rule._compiled_patterns[0], re.Pattern)
        assert isinstance(rule._compiled_patterns[1], re.Pattern)

    def test_compiled_patterns_ignore_case(self):
        """Test that compiled patterns ignore case."""
        rule = RouterRule(
            name="test_rule",
            regex_patterns=[r"hello"]
        )

        # Pattern should match both upper and lower case
        assert rule._compiled_patterns[0].match("HELLO")
        assert rule._compiled_patterns[0].match("hello")
        assert rule._compiled_patterns[0].match("HeLLo")

    def test_compiled_patterns_are_case_insensitive(self):
        """Test that regex patterns are compiled with IGNORECASE."""
        rule = RouterRule(
            name="test_rule",
            regex_patterns=[r"TEST"]
        )

        pattern = rule._compiled_patterns[0]
        # Should be case-insensitive
        assert pattern.flags & re.IGNORECASE


class TestRouterConfig:
    """Test RouterConfig class."""

    def test_create_config_with_defaults(self):
        """Test creating config with default values."""
        config = RouterConfig()

        assert config.default_system == "SYSTEM_2"
        assert config.s1_confidence_threshold == 0.8
        assert config.rules == []
        assert config.enable_heuristics is True
        assert config.max_s1_length == 100

    def test_create_config_with_custom_values(self):
        """Test creating config with custom values."""
        config = RouterConfig(
            default_system="SYSTEM_1",
            s1_confidence_threshold=0.7,
            enable_heuristics=False,
            max_s1_length=50
        )

        assert config.default_system == "SYSTEM_1"
        assert config.s1_confidence_threshold == 0.7
        assert config.enable_heuristics is False
        assert config.max_s1_length == 50

    def test_add_rule(self):
        """Test adding a rule to config."""
        config = RouterConfig()
        rule = RouterRule(
            name="test_rule",
            keywords=["test"],
            target_system="SYSTEM_1"
        )

        config.add_rule(rule)

        assert len(config.rules) == 1
        assert config.rules[0] == rule

    def test_add_multiple_rules(self):
        """Test adding multiple rules."""
        config = RouterConfig()

        config.add_rule(RouterRule(name="rule1", keywords=["a"]))
        config.add_rule(RouterRule(name="rule2", keywords=["b"]))

        assert len(config.rules) == 2
        assert config.rules[0].name == "rule1"
        assert config.rules[1].name == "rule2"

    def test_default_config_has_rules(self):
        """Test that default config comes with predefined rules."""
        config = RouterConfig.default()

        assert len(config.rules) > 0
        assert config.enable_heuristics is True

    def test_default_config_greeting_rule(self):
        """Test that default config has greeting rule."""
        config = RouterConfig.default()

        greeting_rule = next((r for r in config.rules if r.name == "greeting"), None)
        assert greeting_rule is not None
        assert "hello" in greeting_rule.keywords
        assert greeting_rule.target_system == "SYSTEM_1"

    def test_default_config_factual_questions_rule(self):
        """Test that default config has factual questions rule."""
        config = RouterConfig.default()

        factual_rule = next((r for r in config.rules if r.name == "factual_questions"), None)
        assert factual_rule is not None
        assert len(factual_rule.regex_patterns) > 0
        assert factual_rule.target_system == "SYSTEM_1"

    def test_default_config_simple_math_rule(self):
        """Test that default config has simple math rule."""
        config = RouterConfig.default()

        math_rule = next((r for r in config.rules if r.name == "simple_math"), None)
        assert math_rule is not None
        assert len(math_rule.regex_patterns) > 0
        assert math_rule.target_system == "SYSTEM_1"

    def test_default_config_complex_reasoning_rule(self):
        """Test that default config has complex reasoning rule."""
        config = RouterConfig.default()

        complex_rule = next((r for r in config.rules if r.name == "complex_reasoning"), None)
        assert complex_rule is not None
        assert "plan" in complex_rule.keywords
        assert complex_rule.target_system == "SYSTEM_2"

    def test_default_config_greeting_regex(self):
        """Test greeting rule regex patterns work correctly."""
        config = RouterConfig.default()
        greeting_rule = next((r for r in config.rules if r.name == "greeting"), None)

        # Check that the rule has keywords (no regex in greeting rule)
        assert "hi" in greeting_rule.keywords
        assert "hello" in greeting_rule.keywords

    def test_default_config_factual_regex_patterns(self):
        """Test factual questions rule regex patterns."""
        config = RouterConfig.default()
        factual_rule = next((r for r in config.rules if r.name == "factual_questions"), None)

        # Should have compiled patterns
        assert len(factual_rule._compiled_patterns) > 0

        # Test pattern matching
        text = "what is the capital of France?"
        matches = any(p.search(text) for p in factual_rule._compiled_patterns)
        assert matches

    def test_default_config_simple_math_pattern(self):
        """Test simple math rule regex pattern."""
        config = RouterConfig.default()
        math_rule = next((r for r in config.rules if r.name == "simple_math"), None)

        # Test pattern matching for math expression
        text = "2 + 3 = ?"
        matches = any(p.search(text) for p in math_rule._compiled_patterns)
        assert matches

    def test_default_config_complex_reasoning_keywords(self):
        """Test complex reasoning rule has appropriate keywords."""
        config = RouterConfig.default()
        complex_rule = next((r for r in config.rules if r.name == "complex_reasoning"), None)

        # Should have keywords for complex tasks
        assert "plan" in complex_rule.keywords
        assert "strategy" in complex_rule.keywords
        assert "analyze" in complex_rule.keywords
        assert complex_rule.target_system == "SYSTEM_2"

    def test_rules_list_mutable(self):
        """Test that rules list is mutable."""
        config = RouterConfig()

        config.add_rule(RouterRule(name="rule1", keywords=["a"]))
        config.rules.append(RouterRule(name="rule2", keywords=["b"]))

        assert len(config.rules) == 2

    def test_config_with_s1_target(self):
        """Test config with SYSTEM_1 as target."""
        rule = RouterRule(
            name="s1_rule",
            keywords=["simple"],
            target_system="SYSTEM_1"
        )

        assert rule.target_system == "SYSTEM_1"

    def test_config_with_s2_target(self):
        """Test config with SYSTEM_2 as target."""
        rule = RouterRule(
            name="s2_rule",
            keywords=["complex"],
            target_system="SYSTEM_2"
        )

        assert rule.target_system == "SYSTEM_2"

    def test_rule_with_both_keywords_and_regex(self):
        """Test rule with both keywords and regex patterns."""
        rule = RouterRule(
            name="hybrid_rule",
            keywords=["test"],
            regex_patterns=[r"^test"],
            target_system="SYSTEM_1"
        )

        assert len(rule.keywords) == 1
        assert len(rule.regex_patterns) == 1
        assert len(rule._compiled_patterns) == 1
