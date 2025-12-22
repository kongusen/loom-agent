"""
Loom Builtin Tools - "The Hands"
================================

This module provides the primitive for creating tools.

## 🛠️ Tool System

### 1. The `@tool` Decorator
The primary way to create tools. It inspects the function signature and docstring to generate the schema.

```python
@tool
async def calculator(expression: str) -> float:
    \"\"\"
    Evaluates a math expression.
    
    Args:
        expression: The expression to evaluate
    \"\"\"
    return eval(expression)
```

### 2. Best Practices
- **Type Hints**: MANDATORY. Used for schema generation.
- **Docstrings**: CRITICAL. The LLM reads this to know HOW to use the tool.
"""

from loom.builtin.tools.builder import tool, ToolBuilder

__all__ = [
    "tool",
    "ToolBuilder",
]
