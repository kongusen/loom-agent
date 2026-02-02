"""
Unit tests for ScriptCompiler
"""

import pytest

from loom.skills.script_compiler import ScriptCompiler


class TestScriptCompiler:
    """Tests for ScriptCompiler"""

    def test_compile_simple_script(self):
        """Test compiling a simple script with main function"""
        compiler = ScriptCompiler()

        script = """
def main():
    return "Hello, World!"
"""

        func = compiler.compile_script(script, "test.py")
        assert callable(func)
        assert func() == "Hello, World!"

    def test_compile_script_with_execute(self):
        """Test compiling a script with execute function"""
        compiler = ScriptCompiler()

        script = """
def execute():
    return 42
"""

        func = compiler.compile_script(script, "test.py")
        assert callable(func)
        assert func() == 42

    def test_compile_script_with_parameters(self):
        """Test compiling a script with parameters"""
        compiler = ScriptCompiler()

        script = """
def main(x, y):
    return x + y
"""

        func = compiler.compile_script(script, "test.py")
        assert callable(func)
        assert func(2, 3) == 5

    def test_compile_empty_script_raises_error(self):
        """Test that empty script raises ValueError"""
        compiler = ScriptCompiler()

        with pytest.raises(ValueError, match="empty"):
            compiler.compile_script("", "test.py")

    def test_compile_script_without_main_raises_error(self):
        """Test that script without main/execute raises ValueError"""
        compiler = ScriptCompiler()

        script = """
def other_function():
    return "test"
"""

        with pytest.raises(ValueError, match="must define"):
            compiler.compile_script(script, "test.py")

    def test_compile_script_with_syntax_error(self):
        """Test that script with syntax error raises SyntaxError"""
        compiler = ScriptCompiler()

        script = """
def main(:
    return "test"
"""

        with pytest.raises(SyntaxError):
            compiler.compile_script(script, "test.py")
