"""
Error Formatting Utilities
Inspired by Claude Code's ErrorFormatter.
"""


class ErrorFormatter:
    """
    Formats errors into actionable, rich markdown messages.
    """

    @staticmethod
    def format_tool_error(error: Exception, tool_name: str, context: dict | None = None) -> str:
        """
        Format an exception from a tool execution into a rich string.
        """
        error_type = type(error).__name__
        message = str(error)

        # Standard Header
        output = [f"## ❌ Tool Execution Failed: `{tool_name}`"]
        output.append(f"**Error Type**: `{error_type}`")
        output.append(f"**Message**: {message}")

        # Actionable Hints Logic
        hints = ErrorFormatter._get_hints(error, tool_name, message)
        if hints:
            output.append("\n### 💡 Suggestions")
            for hint in hints:
                output.append(f"- {hint}")

        # Technical Details (Stack Trace or raw output if available)
        if hasattr(error, "stdout") and error.stdout:
            output.append(f"\n**stdout**:\n```\n{error.stdout}\n```")
        if hasattr(error, "stderr") and error.stderr:
            output.append(f"\n**stderr**:\n```\n{error.stderr}\n```")

        return "\n".join(output)

    @staticmethod
    def _get_hints(error: Exception, tool_name: str, message: str) -> list[str]:
        hints = []
        msg_lower = message.lower()

        # Permission Errors
        if "permission denied" in msg_lower or "eacces" in msg_lower:
            hints.append("Check if you have the necessary permissions to access the file/directory.")
            hints.append("This might require elevated privileges or checking file mode bits.")

        # File Not Found
        if "not found" in msg_lower or "enoent" in msg_lower or "no such file" in msg_lower:
            hints.append("Double check the file path. It might be misspelled or does not exist.")
            hints.append("Try using `ls` or `find` to verify the path first.")

        # Shell Errors (Generic 127/1)
        if hasattr(error, "returncode"):
             if error.returncode == 127:
                 hints.append("Command not found. Is it installed and in your PATH?")
             if error.returncode != 0:
                 hints.append("Review the stderr output above for specific error details from the command.")

        # Python Syntax/Execution
        if "syntaxerror" in msg_lower:
            hints.append("The code provided to the tool has a syntax error. Please verify the code string.")

        # JSON/Parsing
        if "jsondecodeerror" in msg_lower:
             hints.append(" The tool output was not valid JSON. This might happen if the tool printed extra logs.")

        if not hints:
            hints.append("Review the arguments provided to the tool.")

        return hints
