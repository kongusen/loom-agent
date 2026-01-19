"""
Tests for Sandbox
"""

import pytest

from loom.tools.sandbox import Sandbox, SandboxViolation


class TestSandboxInit:
    """Test suite for Sandbox initialization"""

    def test_init_with_existing_dir(self, tmp_path):
        """Test initialization with existing directory"""
        sandbox = Sandbox(tmp_path)

        assert sandbox.root_dir == tmp_path.resolve()

    def test_init_with_string_path(self, tmp_path):
        """Test initialization with string path"""
        sandbox = Sandbox(str(tmp_path))

        assert sandbox.root_dir == tmp_path.resolve()

    def test_init_auto_creates_directory(self, tmp_path):
        """Test that auto_create=True creates directory"""
        new_dir = tmp_path / "new_sandbox"
        assert not new_dir.exists()

        sandbox = Sandbox(new_dir, auto_create=True)

        assert new_dir.exists()
        assert sandbox.root_dir == new_dir.resolve()

    def test_init_no_auto_create_fails(self, tmp_path):
        """Test that auto_create=False raises error for non-existent dir"""
        new_dir = tmp_path / "nonexistent"

        with pytest.raises(ValueError, match="does not exist"):
            Sandbox(new_dir, auto_create=False)

    def test_init_with_file_raises_error(self, tmp_path):
        """Test that initializing with a file path raises error"""
        file_path = tmp_path / "test_file"
        file_path.write_text("test")

        with pytest.raises(ValueError, match="must be a directory"):
            Sandbox(file_path)


class TestSandboxValidatePath:
    """Test suite for Sandbox.validate_path"""

    @pytest.fixture
    def sandbox(self, tmp_path):
        """Create a sandbox instance"""
        return Sandbox(tmp_path)

    def test_validate_relative_path(self, sandbox, tmp_path):
        """Test validating relative path"""
        result = sandbox.validate_path("test.txt")

        assert result == (tmp_path / "test.txt").resolve()

    def test_validate_nested_path(self, sandbox, tmp_path):
        """Test validating nested relative path"""
        result = sandbox.validate_path("subdir/test.txt")

        assert result == (tmp_path / "subdir" / "test.txt").resolve()

    def test_validate_absolute_path_inside_sandbox(self, sandbox, tmp_path):
        """Test validating absolute path inside sandbox"""
        file_path = tmp_path / "test.txt"
        result = sandbox.validate_path(file_path)

        assert result == file_path.resolve()

    def test_validate_absolute_path_outside_sandbox(self, sandbox, tmp_path):
        """Test validating absolute path outside sandbox raises error"""
        outside_path = tmp_path.parent / "outside.txt"

        with pytest.raises(SandboxViolation, match="outside sandbox"):
            sandbox.validate_path(outside_path)

    def test_validate_path_with_parent_reference(self, sandbox, tmp_path):
        """Test validating path with .. reference"""
        (tmp_path / "subdir").mkdir()

        # Path with .. should still resolve to inside sandbox
        result = sandbox.validate_path("subdir/../test.txt")

        assert result == (tmp_path / "test.txt").resolve()

    def test_validate_path_with_parent_reference_escaping(self, sandbox, tmp_path):
        """Test that path with .. escaping sandbox raises error"""
        (tmp_path / "subdir").mkdir()

        # Try to escape using ../..
        with pytest.raises(SandboxViolation, match="outside sandbox"):
            sandbox.validate_path("subdir/../../etc/passwd")

    def test_validate_dot_path(self, sandbox, tmp_path):
        """Test validating . path"""
        result = sandbox.validate_path(".")

        assert result == tmp_path.resolve()

    def test_validate_empty_path(self, sandbox, tmp_path):
        """Test validating empty string path"""
        result = sandbox.validate_path("")

        # Empty path resolves to root
        assert result == tmp_path.resolve()

    def test_validate_symlink_inside_sandbox(self, sandbox, tmp_path):
        """Test validating symlink inside sandbox"""
        # Create a file and a symlink
        (tmp_path / "target.txt").write_text("content")
        (tmp_path / "link.txt").symlink_to("target.txt")

        result = sandbox.validate_path("link.txt")

        assert result.exists()

    def test_validate_symlink_outside_sandbox(self, sandbox, tmp_path):
        """Test that symlink outside sandbox raises error"""
        # Create file outside sandbox
        outside_file = tmp_path.parent / "outside.txt"
        outside_file.write_text("content")

        # Create symlink inside sandbox pointing outside
        (tmp_path / "link.txt").symlink_to(outside_file)

        with pytest.raises(SandboxViolation, match="outside sandbox"):
            sandbox.validate_path("link.txt")


class TestSandboxViolation:
    """Test suite for SandboxViolation exception"""

    def test_sandbox_violation_is_exception(self):
        """Test SandboxViolation is an Exception"""
        assert issubclass(SandboxViolation, Exception)

    def test_sandbox_violation_can_be_raised(self):
        """Test SandboxViolation can be raised"""
        with pytest.raises(SandboxViolation):
            raise SandboxViolation("Test violation")

    def test_sandbox_violation_message(self):
        """Test SandboxViolation message"""
        error = SandboxViolation("Path violation detected")
        assert str(error) == "Path violation detected"

    def test_sandbox_violation_with_cause(self):
        """Test SandboxViolation with cause"""
        inner_error = ValueError("Inner error")
        error = SandboxViolation("Outer error", inner_error)

        assert "Outer error" in str(error)


class TestSandboxSafeMethods:
    """Test suite for Sandbox safe_* methods"""

    @pytest.fixture
    def sandbox(self, tmp_path):
        """Create a sandbox instance"""
        return Sandbox(tmp_path)

    def test_safe_read_existing_file(self, sandbox, tmp_path):
        """Test reading existing file"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")

        content = sandbox.safe_read("test.txt")

        assert content == "Hello, World!"

    def test_safe_read_nonexistent_file(self, sandbox):
        """Test reading nonexistent file raises FileNotFoundError"""
        with pytest.raises(FileNotFoundError, match="File not found"):
            sandbox.safe_read("nonexistent.txt")

    def test_safe_read_directory_raises_error(self, sandbox, tmp_path):
        """Test reading directory raises ValueError (触发line 115)"""
        subdir = tmp_path / "subdir"
        subdir.mkdir()

        with pytest.raises(ValueError, match="Not a file"):
            sandbox.safe_read("subdir")

    def test_safe_write_new_file(self, sandbox, tmp_path):
        """Test writing new file"""
        sandbox.safe_write("new.txt", "content")

        content = (tmp_path / "new.txt").read_text()
        assert content == "content"

    def test_safe_write_with_subdirectories(self, sandbox, tmp_path):
        """Test writing file with automatic subdirectory creation (触发line 135)"""
        sandbox.safe_write("subdir/nested/file.txt", "content")

        assert (tmp_path / "subdir" / "nested" / "file.txt").exists()
        assert (tmp_path / "subdir" / "nested" / "file.txt").read_text() == "content"

    def test_safe_write_without_create_dirs(self, sandbox, tmp_path):
        """Test writing file without creating subdirectories"""
        subdir = tmp_path / "subdir"
        subdir.mkdir()

        sandbox.safe_write("subdir/file.txt", "content", create_dirs=False)

        assert (tmp_path / "subdir" / "file.txt").exists()

    def test_safe_write_without_create_dirs_fails(self, sandbox, tmp_path):
        """Test writing file without subdirectory creation fails"""
        with pytest.raises(FileNotFoundError):
            sandbox.safe_write("nonexistent/file.txt", "content", create_dirs=False)

    def test_safe_exists_true(self, sandbox, tmp_path):
        """Test safe_exists returns True for existing file"""
        (tmp_path / "test.txt").write_text("content")

        assert sandbox.safe_exists("test.txt") is True

    def test_safe_exists_false(self, sandbox):
        """Test safe_exists returns False for nonexistent file"""
        assert sandbox.safe_exists("nonexistent.txt") is False

    def test_safe_list_dir(self, sandbox, tmp_path):
        """Test listing directory contents (触发line 167)"""
        (tmp_path / "file1.txt").write_text("content1")
        (tmp_path / "file2.txt").write_text("content2")
        (tmp_path / "subdir").mkdir()

        result = sandbox.safe_list_dir(".")

        # Should return list of strings
        assert len(result) == 3
        assert "file1.txt" in result
        assert "file2.txt" in result
        assert "subdir" in result

    def test_safe_list_dir_nonexistent_directory(self, sandbox):
        """Test listing nonexistent directory (触发line 191)"""
        with pytest.raises(FileNotFoundError, match="not found"):
            sandbox.safe_list_dir("nonexistent")

    def test_safe_list_dir_file_not_directory(self, sandbox, tmp_path):
        """Test listing file path (not directory) raises NotADirectoryError (触发line 206)"""
        (tmp_path / "file.txt").write_text("content")

        # NotADirectoryError can be either from os or pathlib module
        import os

        with pytest.raises(NotADirectoryError):
            sandbox.safe_list_dir("file.txt")
