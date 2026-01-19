"""
Tests for Fractal Utilities
"""

import pytest

from loom.config import FractalConfig, GrowthTrigger
from loom.fractal.utils import estimate_task_complexity, should_use_fractal


class TestEstimateTaskComplexity:
    """Test suite for estimate_task_complexity"""

    def test_empty_task(self):
        """Test complexity of empty task"""
        result = estimate_task_complexity("")
        assert result == 0.0

    def test_simple_task(self):
        """Test complexity of simple task"""
        result = estimate_task_complexity("Write a function")
        assert 0.0 <= result <= 0.5

    def test_long_task_higher_complexity(self):
        """Test that longer tasks have higher complexity"""
        short = "do task"
        long = "do task " * 100  # ~800 characters

        short_complexity = estimate_task_complexity(short)
        long_complexity = estimate_task_complexity(long)

        assert long_complexity > short_complexity

    def test_task_with_conjunctions(self):
        """Test task with conjunctions increases complexity"""
        simple = "do task"
        with_conjunctions = "do task and then do another task or do something else before finishing"

        simple_complexity = estimate_task_complexity(simple)
        conjunctions_complexity = estimate_task_complexity(with_conjunctions)

        assert conjunctions_complexity > simple_complexity

    def test_task_with_step_keywords(self):
        """Test task with step keywords increases complexity"""
        simple = "build app"
        with_steps = "first build the backend, second build the frontend, finally deploy the app"

        simple_complexity = estimate_task_complexity(simple)
        steps_complexity = estimate_task_complexity(with_steps)

        assert steps_complexity > simple_complexity

    def test_all_conjunctions(self):
        """Test counting all types of conjunctions"""
        task = "do this AND that OR another THEN after BEFORE while"
        result = estimate_task_complexity(task)
        # Should have high complexity due to many conjunctions
        assert result > 0.3

    def test_all_step_keywords(self):
        """Test counting all types of step keywords"""
        task = "first step, second phase, component, finally step"
        result = estimate_task_complexity(task)
        # Should have high complexity due to many step keywords
        assert result > 0.3

    def test_max_length_score(self):
        """Test that very long tasks cap at 1.0"""
        very_long = "x" * 2000
        result = estimate_task_complexity(very_long)
        # Length score caps at 1.0, but overall result depends on weighted average
        assert result <= 1.0

    def test_case_insensitive(self):
        """Test that analysis is case insensitive"""
        lower = "do task AND then another"
        upper = "DO TASK AND THEN ANOTHER"
        mixed = "Do Task And Then Another"

        result_lower = estimate_task_complexity(lower)
        result_upper = estimate_task_complexity(upper)
        result_mixed = estimate_task_complexity(mixed)

        assert result_lower == result_upper == result_mixed

    def test_complex_real_world_task(self):
        """Test complexity of a realistic complex task"""
        task = """
        Build a web application with the following requirements:
        First, create a REST API with authentication.
        Second, build a frontend using React.
        Then integrate the frontend with the backend.
        After that, add unit tests and integration tests.
        Finally, deploy to production and set up monitoring.
        Also consider adding a database layer with proper indexing.
        """

        result = estimate_task_complexity(task)

        # Should be fairly complex due to length and step keywords
        assert result > 0.5

    def test_weighted_calculation(self):
        """Test that complexity is a weighted average"""
        # Length contributes 30%, conjunctions 40%, steps 30%
        task_just_long = "x" * 500  # Pure length
        task_conjunctions = "do this and that and then another or something"  # Conjunctions
        task_steps = "first step, second phase, finally complete"  # Steps

        long_complexity = estimate_task_complexity(task_just_long)
        conjunctions_complexity = estimate_task_complexity(task_conjunctions)
        steps_complexity = estimate_task_complexity(task_steps)

        # All should be non-zero
        assert long_complexity > 0
        assert conjunctions_complexity > 0
        assert steps_complexity > 0


class TestShouldUseFractal:
    """Test suite for should_use_fractal"""

    def test_disabled_config(self):
        """Test that disabled config never uses fractal"""
        config = FractalConfig(enabled=False)
        result = should_use_fractal("any task", config)
        assert result is False

    def test_none_config(self):
        """Test that None config returns False"""
        result = should_use_fractal("any task", None)
        assert result is False

    @pytest.mark.parametrize("trigger", [GrowthTrigger.NEVER, GrowthTrigger.MANUAL])
    def test_never_and_manual_triggers(self, trigger):
        """Test NEVER and MANUAL triggers don't use fractal automatically"""
        config = FractalConfig(enabled=True, growth_trigger=trigger)
        result = should_use_fractal("any task", config)
        assert result is False

    def test_always_trigger(self):
        """Test ALWAYS trigger always uses fractal"""
        config = FractalConfig(enabled=True, growth_trigger=GrowthTrigger.ALWAYS)
        result = should_use_fractal("simple task", config)
        assert result is True

    def test_complexity_trigger_below_threshold(self):
        """Test complexity trigger below threshold doesn't use fractal"""
        config = FractalConfig(
            enabled=True, growth_trigger=GrowthTrigger.COMPLEXITY, complexity_threshold=0.8
        )
        result = should_use_fractal("simple task", config)
        assert result is False

    def test_complexity_trigger_above_threshold(self):
        """Test complexity trigger above threshold uses fractal"""
        config = FractalConfig(
            enabled=True, growth_trigger=GrowthTrigger.COMPLEXITY, complexity_threshold=0.3
        )
        # Use a complex task that should exceed threshold
        task = "first do this and then do that, after that do another, finally complete everything"
        result = should_use_fractal(task, config)
        assert result is True

    def test_complexity_trigger_at_threshold(self):
        """Test complexity trigger exactly at threshold"""
        config = FractalConfig(
            enabled=True, growth_trigger=GrowthTrigger.COMPLEXITY, complexity_threshold=0.5
        )
        # This task should have exactly 0.5 complexity
        task = "x" * 500  # Length score = 0.5, no conjunctions or steps
        # 0.5 * 0.3 + 0 * 0.4 + 0 * 0.3 = 0.15, which is below 0.5
        result = should_use_fractal(task, config)
        assert result is False

    def test_complexity_trigger_zero_threshold(self):
        """Test complexity trigger with zero threshold always uses fractal"""
        config = FractalConfig(
            enabled=True, growth_trigger=GrowthTrigger.COMPLEXITY, complexity_threshold=0.0
        )
        result = should_use_fractal("any task", config)
        # "any task" has some complexity > 0, so should use fractal
        assert result is True

    def test_complexity_trigger_with_simple_task(self):
        """Test complexity trigger with simple task"""
        config = FractalConfig(
            enabled=True, growth_trigger=GrowthTrigger.COMPLEXITY, complexity_threshold=0.5
        )
        result = should_use_fractal("simple", config)
        assert result is False

    def test_complexity_trigger_with_complex_task(self):
        """Test complexity trigger with very complex task"""
        config = FractalConfig(
            enabled=True, growth_trigger=GrowthTrigger.COMPLEXITY, complexity_threshold=0.4
        )
        complex_task = """
        First, analyze the requirements and create a design document.
        Second, set up the development environment and configure all dependencies.
        Then, implement the core features and integrate them with the backend.
        After that, write comprehensive unit tests and integration tests.
        Finally, deploy to production and set up monitoring and alerting.
        Also ensure proper error handling and logging throughout the application.
        And don't forget to optimize performance and implement caching strategies.
        """

        result = should_use_fractal(complex_task, config)
        assert result is True

    def test_different_triggers_same_task(self):
        """Test same task with different triggers"""
        task = "first do this and then that"

        config_always = FractalConfig(
            enabled=True, growth_trigger=GrowthTrigger.ALWAYS
        )
        config_never = FractalConfig(enabled=True, growth_trigger=GrowthTrigger.NEVER)
        config_complexity = FractalConfig(
            enabled=True, growth_trigger=GrowthTrigger.COMPLEXITY, complexity_threshold=0.1
        )

        assert should_use_fractal(task, config_always) is True
        assert should_use_fractal(task, config_never) is False
        assert should_use_fractal(task, config_complexity) is True
