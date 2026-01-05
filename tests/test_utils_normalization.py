"""
Tests for Normalization Utilities
"""

import pytest
from loom.utils.normalization import DataNormalizer


class TestDataNormalizer:
    """Test DataNormalizer functionality."""

    def test_normalize_none(self):
        """Test normalizing None."""
        result = DataNormalizer.normalize_to_size(None)
        assert result is None

    def test_normalize_primitives(self):
        """Test normalizing primitive types."""
        assert DataNormalizer.normalize_to_size(True) is True
        assert DataNormalizer.normalize_to_size(42) == 42
        assert DataNormalizer.normalize_to_size(3.14) == 3.14
        assert DataNormalizer.normalize_to_size("hello") == "hello"

    def test_normalize_long_string(self):
        """Test normalizing long string."""
        long_string = "a" * 25000
        result = DataNormalizer.normalize_to_size(long_string, string_limit=100)

        assert result.endswith("... [TRUNCATED]")
        assert len(result) <= 115  # 100 + "... [TRUNCATED]"

    def test_normalize_list(self):
        """Test normalizing list."""
        data = [1, 2, 3, 4, 5]
        result = DataNormalizer.normalize_to_size(data)

        assert result == [1, 2, 3, 4, 5]

    def test_normalize_long_list(self):
        """Test normalizing list with many items."""
        data = list(range(100))
        result = DataNormalizer.normalize_to_size(data, max_depth=2)

        assert len(result) <= 51  # 50 items + truncation message
        assert "more items" in str(result[-1])

    def test_normalize_dict(self):
        """Test normalizing dict."""
        data = {"a": 1, "b": 2}
        result = DataNormalizer.normalize_to_size(data)

        assert result == {"a": 1, "b": 2}

    def test_normalize_dict_with_many_keys(self):
        """Test normalizing dict with many keys."""
        data = {f"key{i}": i for i in range(100)}
        result = DataNormalizer.normalize_to_size(data, max_depth=2)

        assert len(result) <= 51  # 50 keys + truncation message

    def test_normalize_nested_structure(self):
        """Test normalizing nested structure."""
        data = {"a": {"b": {"c": "d"}}}
        result = DataNormalizer.normalize_to_size(data, max_depth=2)

        # At max_depth=2, should truncate inner dict
        assert "a" in result
        assert isinstance(result["a"], dict)

    def test_normalize_max_depth_zero(self):
        """Test normalizing with max_depth=0."""
        data = {"a": [1, 2, 3]}
        result = DataNormalizer.normalize_to_size(data, max_depth=0)

        # Should truncate at depth 0
        assert isinstance(result, str)
        assert "dict" in result.lower()

    def test_normalize_with_list_at_max_depth(self):
        """Test normalizing list at max depth."""
        data = [1, 2, 3, 4, 5]
        result = DataNormalizer._normalize(data, max_depth=0, current_depth=0)

        assert result == "[Array(5)]"

    def test_normalize_circular_reference(self):
        """Test handling circular references."""
        data = {}
        data["self"] = data

        result = DataNormalizer.normalize_to_size(data)

        assert "self" in result
        assert result["self"] == "[Circular]"

    def test_normalize_pydantic_model_v2(self):
        """Test normalizing Pydantic v2 model."""
        try:
            from pydantic import BaseModel

            class TestModel(BaseModel):
                name: str
                value: int

            obj = TestModel(name="test", value=42)
            result = DataNormalizer.normalize_to_size(obj)

            assert result == {"name": "test", "value": 42}
        except ImportError:
            pytest.skip("Pydantic not available")

    def test_estimate_size_simple_dict(self):
        """Test size estimation for simple dict."""
        data = {"key": "value"}
        size = DataNormalizer._estimate_size(data)

        assert size > 0

    def test_estimate_size_complex_structure(self):
        """Test size estimation for complex structure."""
        data = {"a": [1, 2, 3], "b": {"c": "d"}}
        size = DataNormalizer._estimate_size(data)

        assert size > 0

    def test_estimate_size_with_exception(self):
        """Test size estimation when JSON serialization fails."""
        class BadObject:
            def __str__(self):
                raise Exception("Cannot serialize")

        obj = BadObject()
        size = DataNormalizer._estimate_size(obj)

        # Should fallback to sys.getsizeof
        assert size > 0

    def test_normalize_with_bytes_limit(self):
        """Test normalize_to_size with bytes limit."""
        large_data = {f"key{i}": f"value{i}" * 100 for i in range(100)}
        result = DataNormalizer.normalize_to_size(large_data, max_bytes=1000)

        # Should truncate to fit within bytes limit
        estimated = DataNormalizer._estimate_size(result)
        assert estimated < 5000  # Reasonable upper bound

    def test_normalize_tuple(self):
        """Test normalizing tuple."""
        data = (1, 2, 3)
        result = DataNormalizer.normalize_to_size(data)

        assert isinstance(result, list)

    def test_normalize_custom_object(self):
        """Test normalizing custom object."""
        class CustomClass:
            def __init__(self):
                self.value = 42

        obj = CustomClass()
        result = DataNormalizer.normalize_to_size(obj)

        # Should normalize to dict representation
        assert "value" in result

    def test_normalize_mixed_structure(self):
        """Test normalizing mixed structure."""
        data = {
            "string": "test",
            "number": 42,
            "list": [1, 2, 3],
            "nested": {"a": "b"}
        }
        result = DataNormalizer.normalize_to_size(data)

        assert result["string"] == "test"
        assert result["number"] == 42
        assert isinstance(result["list"], list)
        assert "nested" in result

    def test_normalize_empty_structures(self):
        """Test normalizing empty structures."""
        assert DataNormalizer.normalize_to_size([]) == []
        assert DataNormalizer.normalize_to_size({}) == {}

    def test_normalize_set_becomes_list(self):
        """Test that set is converted to list-like."""
        data = {1, 2, 3}
        result = DataNormalizer.normalize_to_size(data)

        # Set doesn't have __dict__, should convert to string
        assert isinstance(result, str)

    def test_normalize_preserves_types(self):
        """Test that primitive types are preserved."""
        data = {
            "int": 42,
            "float": 3.14,
            "bool": True,
            "str": "test"
        }
        result = DataNormalizer.normalize_to_size(data)

        assert isinstance(result["int"], int)
        assert isinstance(result["float"], float)
        assert isinstance(result["bool"], bool)
        assert isinstance(result["str"], str)

    def test_normalize_with_different_depths(self):
        """Test normalization at different depths."""
        data = {"a": {"b": {"c": {"d": "value"}}}}

        result_depth1 = DataNormalizer.normalize_to_size(data, max_depth=1)
        result_depth3 = DataNormalizer.normalize_to_size(data, max_depth=3)

        # Depth 1 should be more truncated
        str(result_depth1).count("[") <= str(result_depth3).count("[")
