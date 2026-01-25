"""
Phase 3: Smart Allocation Tests

Tests for TaskAnalyzer and SmartAllocationStrategy.
"""

import pytest

from loom.fractal.allocation import TaskAnalyzer, TaskFeatures
from loom.protocol import Task


class TestTaskAnalyzer:
    """Test TaskAnalyzer class"""

    @pytest.fixture
    def analyzer(self) -> TaskAnalyzer:
        """Create a TaskAnalyzer instance for testing"""
        return TaskAnalyzer()

    def test_analyzer_creation(self, analyzer: TaskAnalyzer) -> None:
        """Test creating a task analyzer"""
        assert analyzer is not None

    def test_analyze_simple_task(self, analyzer: TaskAnalyzer) -> None:
        """Test analyzing a simple task"""
        task = Task(task_id="test-1", action="read_file")

        features = analyzer.analyze(task)

        assert isinstance(features, TaskFeatures)
        assert isinstance(features.keywords, set)
        assert isinstance(features.action_type, str)
        assert 0 <= features.complexity <= 1
        assert isinstance(features.required_context, set)
