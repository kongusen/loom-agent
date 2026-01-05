"""
Tests for Protocol Patch (JSON Patch implementation)

Tests the StatePatch class and apply_patch function.
"""

import pytest
from loom.protocol.patch import StatePatch, PatchOperation, apply_patch


class TestPatchOperation:
    """Test PatchOperation enum."""

    def test_add_value(self):
        """Test ADD operation value."""
        assert PatchOperation.ADD.value == "add"

    def test_remove_value(self):
        """Test REMOVE operation value."""
        assert PatchOperation.REMOVE.value == "remove"

    def test_replace_value(self):
        """Test REPLACE operation value."""
        assert PatchOperation.REPLACE.value == "replace"

    def test_move_value(self):
        """Test MOVE operation value."""
        assert PatchOperation.MOVE.value == "move"

    def test_copy_value(self):
        """Test COPY operation value."""
        assert PatchOperation.COPY.value == "copy"

    def test_test_value(self):
        """Test TEST operation value."""
        assert PatchOperation.TEST.value == "test"


class TestStatePatch:
    """Test StatePatch model."""

    def test_create_add_patch(self):
        """Test creating an ADD patch."""
        patch = StatePatch(
            op=PatchOperation.ADD,
            path="/test/key",
            value="value"
        )
        assert patch.op == PatchOperation.ADD
        assert patch.path == "/test/key"
        assert patch.value == "value"

    def test_create_replace_patch(self):
        """Test creating a REPLACE patch."""
        patch = StatePatch(
            op=PatchOperation.REPLACE,
            path="/test/key",
            value=42
        )
        assert patch.op == PatchOperation.REPLACE
        assert patch.value == 42

    def test_create_remove_patch(self):
        """Test creating a REMOVE patch."""
        patch = StatePatch(
            op=PatchOperation.REMOVE,
            path="/test/key"
        )
        assert patch.op == PatchOperation.REMOVE
        assert patch.value is None

    def test_patch_with_from_alias(self):
        """Test patch with 'from' alias."""
        patch = StatePatch(
            op=PatchOperation.COPY,
            path="/target",
            from_path="/source"
        )
        assert patch.from_path == "/source"

    def test_patch_model_dump(self):
        """Test that StatePatch can be serialized."""
        patch = StatePatch(
            op=PatchOperation.ADD,
            path="/test",
            value="data"
        )
        data = patch.model_dump()

        assert data["op"] == "add"
        assert data["path"] == "/test"
        assert data["value"] == "data"

    def test_all_operations_valid(self):
        """Test all patch operations can be created."""
        for op in PatchOperation:
            patch = StatePatch(op=op, path="/test", value="data")
            assert patch.op == op


class TestApplyPatch:
    """Test apply_patch function."""

    def test_apply_add_to_dict(self):
        """Test applying ADD patch to dict."""
        state = {}
        patch = StatePatch(
            op=PatchOperation.ADD,
            path="/key",
            value="value"
        )
        apply_patch(state, patch)

        assert state == {"key": "value"}

    def test_apply_add_to_nested_dict(self):
        """Test applying ADD patch to nested dict."""
        state = {"outer": {}}
        patch = StatePatch(
            op=PatchOperation.ADD,
            path="/outer/inner",
            value="value"
        )
        apply_patch(state, patch)

        assert state == {"outer": {"inner": "value"}}

    def test_apply_add_to_list_by_index(self):
        """Test applying ADD patch to list at specific index."""
        state = [1, 2, 4]
        patch = StatePatch(
            op=PatchOperation.ADD,
            path="/2",
            value=3
        )
        apply_patch(state, patch)

        assert state == [1, 2, 3, 4]

    def test_apply_add_to_list_at_end(self):
        """Test applying ADD patch to list at end."""
        state = [1, 2]
        patch = StatePatch(
            op=PatchOperation.ADD,
            path="/-",
            value=3
        )
        apply_patch(state, patch)

        assert state == [1, 2, 3]

    def test_apply_replace_in_dict(self):
        """Test applying REPLACE patch in dict."""
        state = {"key": "old"}
        patch = StatePatch(
            op=PatchOperation.REPLACE,
            path="/key",
            value="new"
        )
        apply_patch(state, patch)

        assert state == {"key": "new"}

    def test_apply_replace_in_list(self):
        """Test applying REPLACE patch in list."""
        state = [1, 2, 3]
        patch = StatePatch(
            op=PatchOperation.REPLACE,
            path="/1",
            value=20
        )
        apply_patch(state, patch)

        assert state == [1, 20, 3]

    def test_apply_remove_from_dict(self):
        """Test applying REMOVE patch from dict."""
        state = {"key": "value", "other": "keep"}
        patch = StatePatch(
            op=PatchOperation.REMOVE,
            path="/key"
        )
        apply_patch(state, patch)

        assert state == {"other": "keep"}
        assert "key" not in state

    def test_apply_remove_from_list(self):
        """Test applying REMOVE patch from list."""
        state = [1, 2, 3]
        patch = StatePatch(
            op=PatchOperation.REMOVE,
            path="/1"
        )
        apply_patch(state, patch)

        assert state == [1, 3]

    def test_apply_patch_to_root(self):
        """Test applying patch to root (no-op)."""
        state = {"key": "value"}
        patch = StatePatch(
            op=PatchOperation.ADD,
            path="/",
            value="test"
        )
        apply_patch(state, patch)

        # Root modification should not directly modify
        assert state == {"key": "value"}

    def test_apply_add_creates_nested_path(self):
        """Test that ADD creates nested path if not exists."""
        state = {}
        patch = StatePatch(
            op=PatchOperation.ADD,
            path="/a/b/c",
            value="value"
        )
        apply_patch(state, patch)

        assert state["a"]["b"]["c"] == "value"

    def test_apply_add_overwrites_value(self):
        """Test that ADD overwrites existing value."""
        state = {"key": "old"}
        patch = StatePatch(
            op=PatchOperation.ADD,
            path="/key",
            value="new"
        )
        apply_patch(state, patch)

        assert state["key"] == "new"

    def test_apply_replace_creates_if_not_exists(self):
        """Test that REPLACE creates if not exists (setdefault behavior)."""
        state = {}
        patch = StatePatch(
            op=PatchOperation.REPLACE,
            path="/new_key",
            value="new"
        )
        apply_patch(state, patch)

        assert state == {"new_key": "new"}

    def test_apply_invalid_list_index(self):
        """Test applying patch with invalid list index."""
        state = [1, 2, 3]
        patch = StatePatch(
            op=PatchOperation.ADD,
            path="/invalid",
            value="test"
        )

        with pytest.raises(ValueError):
            apply_patch(state, patch)

    def test_apply_remove_nonexistent_key(self):
        """Test removing non-existent key (should not error)."""
        state = {"key": "value"}
        patch = StatePatch(
            op=PatchOperation.REMOVE,
            path="/nonexistent"
        )
        apply_patch(state, patch)

        assert state == {"key": "value"}

    def test_apply_patch_various_values(self):
        """Test applying patches with various value types."""
        state = {}
        values = [
            ("str_val", "string"),
            ("int_val", 42),
            ("float_val", 3.14),
            ("bool_val", True),
            ("null_val", None),
            ("list_val", [1, 2, 3]),
            ("dict_val", {"nested": "data"})
        ]

        for key, value in values:
            patch = StatePatch(
                op=PatchOperation.ADD,
                path=f"/{key}",
                value=value
            )
            apply_patch(state, patch)

        assert state["str_val"] == "string"
        assert state["int_val"] == 42
        assert state["float_val"] == 3.14
        assert state["bool_val"] is True
        assert state["null_val"] is None
        assert state["list_val"] == [1, 2, 3]
        assert state["dict_val"] == {"nested": "data"}

    def test_apply_patch_special_characters_in_path(self):
        """Test path with special characters."""
        state = {}
        patch = StatePatch(
            op=PatchOperation.ADD,
            path="/key-with_special.chars",
            value="value"
        )
        apply_patch(state, patch)

        assert "key-with_special.chars" in state
